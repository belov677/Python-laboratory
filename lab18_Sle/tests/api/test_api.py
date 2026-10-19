"""Тесты HTTP API (дополнительное задание 2)."""
import pytest
from fastapi.testclient import TestClient

from src.api.app import app, get_service


@pytest.fixture
def client(real_service):
    app.dependency_overrides[get_service] = lambda: real_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_receive_and_stock(client):
    r = client.post("/stock/receive", json={"product_id": 1, "warehouse_id": 1, "quantity": 7})
    assert r.status_code == 200 and r.json() == {"balance": 7}
    body = client.get("/products/1/stock").json()
    assert body["total"] == 7 and body["product"]["sku"] == "EL-1001"


@pytest.mark.parametrize("payload, status, error", [
    ({"product_id": 1, "warehouse_id": 1, "quantity": 0}, 422, "ValidationError"),
    ({"product_id": 99, "warehouse_id": 1, "quantity": 1}, 404, "NotFoundError"),
    ({"product_id": 1, "warehouse_id": 1, "quantity": 1}, 409, "InsufficientStockError"),
])
def test_api_write_off_errors(client, payload, status, error):
    r = client.post("/stock/write-off", json=payload)
    assert r.status_code == status and r.json()["error"] == error


def test_api_create_product_and_duplicate(client):
    data = {"sku": "EL-2001", "name": "Мышь", "min_stock": 10}
    assert client.post("/products", json=data).status_code == 201
    assert client.post("/products", json=data).status_code == 409
    assert client.post("/products", json={"sku": "EL-2002"}).status_code == 422  # нет name


def test_api_transfer_and_search(client):
    client.post("/stock/receive", json={"product_id": 2, "warehouse_id": 1, "quantity": 10})
    r = client.post("/stock/transfer", json={"product_id": 2, "source_id": 1, "target_id": 2, "quantity": 4})
    assert r.json() == {"source_balance": 6, "target_balance": 4}
    assert [p["sku"] for p in client.get("/products", params={"q": "бумага"}).json()] == ["OF-5001"]
