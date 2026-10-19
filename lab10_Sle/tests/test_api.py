from tests.conftest import KEY, NEW


def test_get_list(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert len(response.get_json()) == 6


def test_get_item(client):
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.get_json()["sku"] == "NB-001"


def test_get_missing_returns_404(client):
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Item with id 999 not found", "code": "ITEM_NOT_FOUND"}


def test_create_returns_201(client):
    response = client.post("/items", json=NEW, headers=KEY)
    assert response.status_code == 201
    assert response.headers["Location"] == "/items/7"


def test_create_invalid_returns_400(client):
    response = client.post("/items", json={**NEW, "price": 0}, headers=KEY)
    assert response.status_code == 400
    assert response.get_json()["code"] == "VALIDATION_ERROR"


def test_create_duplicate_returns_409(client):
    assert client.post("/items", json={**NEW, "sku": "NB-001"}, headers=KEY).status_code == 409


def test_put_replaces_item(client):
    response = client.put("/items/2", json={**NEW, "sku": "MS-010"}, headers=KEY)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Клавиатура"


def test_patch_changes_one_field(client):
    response = client.patch("/items/1", json={"quantity": 2}, headers=KEY)
    body = response.get_json()
    assert response.status_code == 200 and body["quantity"] == 2 and body["below_min"]


def test_delete_returns_204_then_404(client):
    assert client.delete("/items/3", headers=KEY).status_code == 204
    assert client.delete("/items/3", headers=KEY).status_code == 404


def test_filter_and_sort(client):
    body = client.get("/items?category=мебель&sort=price&order=desc").get_json()
    assert [i["sku"] for i in body] == ["TB-120", "CH-OF"]


def test_filter_bad_parameter_returns_400(client):
    assert client.get("/items?min_quantity=abc").status_code == 400
    assert client.get("/items?sort=color").status_code == 400


def test_low_stock_endpoint(client):
    body = client.get("/items/low-stock").get_json()
    assert {i["sku"] for i in body} == {"MS-010", "PN-BL", "TB-120"}


def test_pagination(client):
    body = client.get("/items?page=2&limit=4").get_json()
    assert body["total"] == 6 and len(body["items"]) == 2


def test_api_key_required(client):
    assert client.post("/items", json=NEW).status_code == 401


def test_method_not_allowed(client):
    response = client.post("/items/1", headers=KEY)
    assert response.status_code == 405


def test_etag_not_modified(client):
    etag = client.get("/items/1").headers["ETag"]
    assert client.get("/items/1", headers={"If-None-Match": etag}).status_code == 304
