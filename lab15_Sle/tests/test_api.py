"""Тесты REST API."""


def test_api_list_filters(client):
    data = client.get("/api/shipments?status=IN_TRANSIT&sort=cost&order=desc").get_json()
    assert data["total"] == 2
    costs = [s["cost"] for s in data["items"]]
    assert costs == sorted(costs, reverse=True)


def test_api_create_and_cost(client, new_shipment):
    r = client.post("/api/shipments", json=new_shipment)
    assert r.status_code == 201 and r.headers["Location"] == "/api/shipments/8"
    body = r.get_json()
    assert body["cost"] == 851.0  # 500 + 75*180*0.02*1.3
    assert body["events"][0]["status"] == "CREATED"


def test_api_validation_400(client):
    r = client.post("/api/shipments", json={"client_id": 999, "origin": "Москва",
                                            "destination": "москва", "distance_km": "x"})
    body = r.get_json()
    assert r.status_code == 400
    assert set(body["fields"]) >= {"client_id", "destination", "distance_km"}


def test_api_bad_json(client):
    r = client.post("/api/shipments", data="oops", content_type="application/json")
    assert r.status_code == 400


def test_api_conflict_409(client, new_shipment):
    new_shipment["tracking_number"] = "LG-00001"
    assert client.post("/api/shipments", json=new_shipment).status_code == 409
    r = client.post("/api/clients", json={"name": "Дубль", "email": "farm@fermer.ru", "city": "Тула"})
    assert r.status_code == 409


def test_api_status_transitions(client):
    r = client.post("/api/shipments/6/status", json={"status": "IN_TRANSIT", "location": "Чебоксары"})
    assert r.status_code == 200 and r.get_json()["status"] == "IN_TRANSIT"
    r = client.post("/api/shipments/1/status", json={"status": "CANCELLED", "location": "СПб"})
    assert r.status_code == 409


def test_api_update_only_created(client, new_shipment):
    assert client.put("/api/shipments/5", json=new_shipment).status_code == 200
    assert client.put("/api/shipments/2", json=new_shipment).status_code == 409


def test_api_delete(client):
    assert client.delete("/api/shipments/2").status_code == 409  # в пути
    assert client.delete("/api/shipments/3").status_code == 204
    assert client.get("/api/shipments/3").status_code == 404


def test_api_client_shipments_relation(client):
    data = client.get("/api/clients/1/shipments").get_json()
    assert [s["tracking_number"] for s in data["shipments"]] == ["LG-00001", "LG-00004"]


def test_api_404_json(client):
    r = client.get("/api/track/NOPE")
    assert r.status_code == 404 and r.get_json()["error"] == "NotFoundError"
