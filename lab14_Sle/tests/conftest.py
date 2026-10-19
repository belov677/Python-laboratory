import sys
from dataclasses import replace
from pathlib import Path

import pytest
import redis
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from config import settings  # noqa: E402
from main import create_app  # noqa: E402
from seed import seed  # noqa: E402

TEST_SETTINGS = replace(settings, database_url="postgresql+psycopg://lab:lab@localhost:5432/warehouse_api_test",
                        redis_url="redis://localhost:6379/13", audit_log="/tmp/claude-0/audit_test.log")
NEW = {"sku": "CB-HDMI", "name": "Кабель HDMI 2 м", "category": "электроника", "quantity": 40,
       "min_stock": 10, "price": 390, "supplier": "ООО Периферия", "location": "A-05"}


@pytest.fixture
def client():
    redis.Redis.from_url(TEST_SETTINGS.redis_url).flushdb()
    app = create_app(TEST_SETTINGS, reset_db=True)
    with TestClient(app) as test_client:
        seed(app.state.db)
        yield test_client


def token(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password}).json()["access_token"]


@pytest.fixture
def admin(client):
    return {"Authorization": f"Bearer {token(client, 'admin', 'admin12345')}"}


@pytest.fixture
def user(client):
    client.post("/auth/register", json={"username": "ivan", "password": "password123"})
    return {"Authorization": f"Bearer {token(client, 'ivan', 'password123')}"}
