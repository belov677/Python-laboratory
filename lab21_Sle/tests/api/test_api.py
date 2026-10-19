"""Тесты REST API: коды ответов, права, валидация, сквозной сценарий."""

from app.services.notifications import handle_event


async def test_register_login_me_and_duplicate(client, user):
    me = await client.get("/auth/me", headers=user)
    assert me.status_code == 200 and me.json()["role"] == "USER"
    dup = await client.post(
        "/auth/register", json={"email": "CLIENT@example.com", "password": "Client2026", "full_name": "Дубль"}
    )
    assert dup.status_code == 409 and dup.json()["error"] == "EMAIL_TAKEN"
    bad = await client.post("/auth/login", json={"email": "client@example.com", "password": "Wrong2026"})
    assert bad.status_code == 401 and bad.json() == {
        "error": "INVALID_CREDENTIALS",
        "message": "Неверный email или пароль",
    }


async def test_unauthorized_and_forbidden(client, user):
    assert (await client.get("/orders")).status_code == 401
    assert (await client.get("/orders", headers={"Authorization": "Bearer garbage"})).json()["error"] == "INVALID_TOKEN"
    forbidden = await client.get("/vehicles", headers=user)
    assert forbidden.status_code == 403 and forbidden.json()["error"] == "ADMIN_ONLY"


async def test_validation_error_format(client, user, make_order):
    response = await client.post("/orders", headers=user, json=make_order(weight_kg=-1, cargo=""))
    body = response.json()
    assert response.status_code == 422 and body["error"] == "VALIDATION_ERROR"
    assert {d["field"] for d in body["details"]} == {"weight_kg", "cargo"}


async def test_routes_cache_hit_miss_and_invalidation(client, user, admin):
    first = await client.get("/routes", headers=user)
    second = await client.get("/routes", headers=user)
    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("MISS", "HIT")
    route = first.json()[0]
    updated = await client.put(f"/routes/{route['id']}", headers=admin, json={**route, "distance_km": 715})
    assert updated.status_code == 200
    third = await client.get("/routes", headers=user)
    assert third.headers["X-Cache"] == "MISS" and third.json()[0]["distance_km"] == 715
    assert (await client.get("/routes/999", headers=user)).json()["error"] == "МАРШРУТ_NOT_FOUND"


async def test_fleet_crud_and_conflicts(client, admin):
    body = {"plate": "Т808ТТ77", "model": "Hyundai HD78", "category": "C", "capacity_kg": 4500}
    created = await client.post("/vehicles", headers=admin, json=body)
    assert created.status_code == 201
    assert (await client.post("/vehicles", headers=admin, json=body)).json()["error"] == "PLATE_TAKEN"
    vid = created.json()["id"]
    assert (await client.put(f"/vehicles/{vid}", headers=admin, json={**body, "capacity_kg": 4800})).status_code == 200
    heavy = await client.get("/vehicles", headers=admin, params={"min_capacity": 10000, "sort": "-capacity"})
    assert [v["capacity_kg"] for v in heavy.json()] == [40000, 15000]
    assert (await client.delete(f"/vehicles/{vid}", headers=admin)).status_code == 204
    driver = {
        "full_name": "Новиков Денис",
        "license_number": "50 05 500005",
        "license_categories": ["C"],
        "phone": "+79035550005",
    }
    assert (await client.post("/drivers", headers=admin, json=driver)).status_code == 201
    assert (await client.post("/drivers", headers=admin, json=driver)).status_code == 409


async def test_order_rules_via_api(client, user, make_order):
    no_route = await client.post("/orders", headers=user, json=make_order(destination="Владивосток"))
    assert no_route.status_code == 409 and no_route.json()["error"] == "NO_ROUTE"
    order = (await client.post("/orders", headers=user, json=make_order())).json()
    changed = await client.put(f"/orders/{order['id']}", headers=user, json=make_order(weight_kg=1500))
    assert changed.json()["weight_kg"] == 1500
    assert (await client.get("/orders/99999", headers=user)).status_code == 404


async def test_users_see_only_their_orders(client, user, other_user, admin, make_order):
    mine = (await client.post("/orders", headers=user, json=make_order())).json()
    await client.post("/orders", headers=other_user, json=make_order(weight_kg=300))
    assert (await client.get(f"/orders/{mine['id']}", headers=other_user)).status_code == 403
    assert (await client.get("/orders", headers=user)).json()["total"] == 1
    assert (await client.get("/orders", headers=admin)).json()["total"] == 2


async def test_full_delivery_scenario(client, container, user, admin, make_order):
    order = (await client.post("/orders", headers=user, json=make_order(weight_kg=4200))).json()
    options = (await client.get("/deliveries/available", headers=admin, params={"order_id": order["id"]})).json()
    assert [v["plate"] for v in options["vehicles"]] == ["К404КК16", "Е303ЕЕ78", "М505ММ66"]  # от меньшей к большей
    assert {d["full_name"] for d in options["drivers"]} >= {"Смирнов Олег Игоревич"}
    wrong = await client.post(
        "/deliveries", headers=admin, json={"order_id": order["id"], "vehicle_id": 3, "driver_id": 1}
    )  # нет категории C
    assert wrong.json()["error"] == "DRIVER_LICENSE"
    created = await client.post(
        "/deliveries", headers=admin, json={"order_id": order["id"], "vehicle_id": 4, "driver_id": 2}
    )
    assert created.status_code == 201 and created.json()["cost"] == 1500 + 710 * 45
    again = await client.post(
        "/deliveries", headers=admin, json={"order_id": order["id"], "vehicle_id": 3, "driver_id": 3}
    )
    assert again.json()["error"] == "ORDER_NOT_NEW"
    delivery_id = created.json()["id"]
    for action in ("start", "complete"):
        assert (
            await client.patch(f"/deliveries/{delivery_id}/status", headers=admin, json={"action": action})
        ).status_code == 200
    tracking = (await client.get(f"/orders/{order['id']}/tracking", headers=user)).json()
    assert tracking["order"]["status"] == "DELIVERED" and tracking["delivery"]["vehicle"]["plate"] == "К404КК16"
    assert (await client.delete(f"/orders/{order['id']}", headers=user)).json()["error"] == "ORDER_NOT_CANCELLABLE"
    # события из outbox → брокер → worker → уведомления клиенту
    await container.outbox.flush()
    for event in container.publisher.events:
        await handle_event(container.sessions, event)
    texts = [n["text"] for n in (await client.get("/auth/me/notifications", headers=user)).json()]
    assert len(texts) == 4 and "груз доставлен" in texts[0] and "принят" in texts[-1]


async def test_cancel_scheduled_order_frees_vehicle(client, user, admin, make_order):
    first = (await client.post("/orders", headers=user, json=make_order())).json()
    await client.post("/deliveries", headers=admin, json={"order_id": first["id"], "vehicle_id": 1, "driver_id": 1})
    second = (await client.post("/orders", headers=user, json=make_order(weight_kg=800))).json()
    busy = await client.post(
        "/deliveries", headers=admin, json={"order_id": second["id"], "vehicle_id": 1, "driver_id": 2}
    )
    assert busy.json()["error"] == "VEHICLE_BUSY"  # то же время, та же машина
    assert (await client.delete(f"/orders/{first['id']}", headers=user)).json()["status"] == "CANCELLED"
    free = await client.post(
        "/deliveries", headers=admin, json={"order_id": second["id"], "vehicle_id": 1, "driver_id": 2}
    )
    assert free.status_code == 201


async def test_health_and_metrics_degrade_without_redis(client, container, user):
    assert (await client.get("/health")).json() == {
        "status": "healthy",
        "checks": {"database": "up", "redis": "up", "broker": "up"},
        "outbox_backlog": 0,
    }
    await client.get("/routes", headers=user)
    container.cache.client = None  # Redis «упал»
    response = await client.get("/routes", headers=user)
    assert response.status_code == 200 and response.headers["X-Cache"] == "BYPASS"
    assert (await client.get("/health")).json()["status"] == "degraded"
    metrics = (await client.get("/metrics")).json()
    assert metrics["endpoints"]["GET /routes"]["count"] == 2 and metrics["cache"]["bypass"] == 1


async def test_internal_errors_do_not_leak_traceback(client, container, user, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("секретная деталь реализации")

    monkeypatch.setattr("app.services.catalog.CatalogService.list_routes", boom)
    response = await client.get("/routes", headers=user)
    assert response.status_code == 500
    assert response.json() == {"error": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"}


async def test_route_management_rules(client, admin, user, make_order):
    body = {"code": "R-201", "origin": "Тула", "destination": "Орёл", "distance_km": 180, "duration_h": 2.5}
    created = await client.post("/routes", headers=admin, json=body)
    assert created.status_code == 201
    assert (await client.post("/routes", headers=admin, json={**body, "code": "R-202"})).json()[
        "error"
    ] == "ROUTE_EXISTS"
    assert (await client.post("/routes", headers=admin, json={**body, "origin": "Курск"})).json()[
        "error"
    ] == "ROUTE_CODE_TAKEN"
    assert (await client.post("/routes", headers=user, json=body)).status_code == 403
    assert (await client.delete(f"/routes/{created.json()['id']}", headers=admin)).status_code == 204
    order = (await client.post("/orders", headers=user, json=make_order())).json()
    await client.post("/deliveries", headers=admin, json={"order_id": order["id"], "vehicle_id": 1, "driver_id": 1})
    used = await client.delete("/routes/1", headers=admin)  # маршрут используется в рейсе
    assert used.status_code == 409 and used.json()["error"] == "ROUTE_IN_USE"


async def test_fleet_rules_with_active_delivery(client, admin, user, make_order):
    order = (await client.post("/orders", headers=user, json=make_order())).json()
    await client.post("/deliveries", headers=admin, json={"order_id": order["id"], "vehicle_id": 1, "driver_id": 1})
    vehicle = {
        "plate": "А101АА77",
        "model": "ГАЗель Next",
        "category": "B",
        "capacity_kg": 1500,
        "status": "MAINTENANCE",
    }
    repair = await client.put("/vehicles/1", headers=admin, json=vehicle)
    assert repair.json()["error"] == "VEHICLE_HAS_DELIVERIES"
    assert (await client.delete("/vehicles/1", headers=admin)).json()["error"] == "VEHICLE_IN_USE"
    assert (await client.delete("/drivers/1", headers=admin)).json()["error"] == "DRIVER_IN_USE"
    driver = {
        "full_name": "Иванов Пётр Сергеевич",
        "license_number": "77 01 100001",
        "license_categories": ["B"],
        "phone": "+79160000001",
        "active": False,
    }
    assert (await client.put("/drivers/1", headers=admin, json=driver)).json()["active"] is False
    assert (await client.delete("/drivers/4", headers=admin)).status_code == 204
    listing = await client.get("/deliveries", headers=admin, params={"status": "PLANNED"})
    assert len(listing.json()) == 1
    assert (await client.get(f"/deliveries/{listing.json()[0]['id']}", headers=admin)).status_code == 200


async def test_documentation_is_available(client):
    assert "swagger-ui" in (await client.get("/swagger")).text
    schema = (await client.get("/openapi.json")).json()
    assert "/deliveries" in schema["paths"] and "/orders/{order_id}/tracking" in schema["paths"]
    assert (await client.get("/static/swagger-ui.css")).status_code == 200
