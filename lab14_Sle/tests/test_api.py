from tests.conftest import NEW


def test_get_list(client, user):
    body = client.get("/items", headers=user).json()
    assert body["total"] == 15 and len(body["items"]) == 10


def test_get_existing(client, user):
    response = client.get("/items/1", headers=user)
    assert response.status_code == 200 and response.json()["sku"] == "NB-001"


def test_get_missing(client, user):
    response = client.get("/items/999", headers=user)
    assert response.status_code == 404 and response.json()["error"] == "NOT_FOUND"


def test_post_valid(client, admin):
    response = client.post("/items", json=NEW, headers=admin)
    assert response.status_code == 201 and response.json()["id"] == 16


def test_post_invalid(client, admin):
    response = client.post("/items", json={**NEW, "quantity": -1, "location": "zone"}, headers=admin)
    assert response.status_code == 422
    assert {d["field"] for d in response.json()["details"]} == {"quantity", "location"}


def test_post_duplicate_conflict(client, admin):
    assert client.post("/items", json={**NEW, "sku": "NB-001"}, headers=admin).status_code == 409


def test_put(client, admin):
    response = client.put("/items/2", json={**NEW, "sku": "MS-010"}, headers=admin)
    assert response.status_code == 200 and response.json()["name"] == "Кабель HDMI 2 м"


def test_patch_changes_only_given_fields(client, admin):
    body = client.patch("/items/1", json={"quantity": 2}, headers=admin).json()
    assert body["quantity"] == 2 and body["name"] == "Ноутбук Lenovo IdeaPad" and body["below_min"]


def test_delete_and_repeat(client, admin):
    assert client.delete("/items/3", headers=admin).status_code == 204
    assert client.delete("/items/3", headers=admin).status_code == 404


def test_filtering(client, user):
    body = client.get("/items?category=мебель", headers=user).json()
    assert {i["sku"] for i in body["items"]} == {"CH-OF", "TB-120", "SH-05"}
    below = client.get("/items?below_min=true&limit=100", headers=user).json()
    assert below["total"] == 5


def test_sorting(client, user):
    body = client.get("/items?sort=price&order=desc&limit=3", headers=user).json()
    assert [i["sku"] for i in body["items"]] == ["NB-001", "MN-027", "TB-120"]


def test_pagination(client, user):
    body = client.get("/items?skip=10&limit=10", headers=user).json()
    assert len(body["items"]) == 5 and body["skip"] == 10


def test_search(client, user):
    assert {i["sku"] for i in client.get("/items/search?q=молкомб", headers=user).json()} == \
        {"MLK-32", "KF-1", "SR-RS"}


def test_statistics(client, user):
    body = client.get("/items/statistics", headers=user).json()
    assert body["total_items"] == 15 and body["below_min"] == 5
    assert body["by_category"]["продукты"] == 3


def test_validation_error_on_query(client, user):
    assert client.get("/items?sort=color", headers=user).status_code == 422
    assert client.get("/items?limit=1000", headers=user).status_code == 422


def test_cache_miss_then_hit(client, user):
    assert client.get("/items/4", headers=user).headers["X-Cache"] == "MISS"
    assert client.get("/items/4", headers=user).headers["X-Cache"] == "HIT"


def test_cache_invalidation(client, user, admin):
    client.get("/items/5", headers=user)
    client.patch("/items/5", json={"price": 450}, headers=admin)
    response = client.get("/items/5", headers=user)
    assert response.headers["X-Cache"] == "MISS" and response.json()["price"] == 450


def test_auth_required_and_roles(client, user):
    assert client.get("/items").status_code == 401
    assert client.post("/items", json=NEW, headers=user).status_code == 403
    assert client.get("/profile", headers=user).json() == {"id": 2, "username": "ivan", "role": "USER"}


def test_wrong_password(client):
    response = client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "healthy"}
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/items", "/items/{item_id}", "/items/search", "/items/statistics"} <= set(paths)
