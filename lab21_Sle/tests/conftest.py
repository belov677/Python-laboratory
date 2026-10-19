"""Фикстуры: отдельная тестовая БД PostgreSQL, Redis — fakeredis, брокер — подделка в памяти."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio

from app.config import Settings
from app.container import Container
from app.core.database import create_schema
from app.main import create_app

ADMIN = {"email": "dispatcher@example.com", "password": "Dispatcher2026"}


class FakeConnection:
    is_closed = False


class FakePublisher:
    """Брокер в памяти; up=False имитирует недоступность RabbitMQ."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.up = True
        self.connection = FakeConnection()

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def publish(self, event_id: str, name: str, payload: dict) -> None:
        if not self.up:
            raise ConnectionError("broker down")
        self.events.append({"id": event_id, "name": name, "payload": payload})


def settings() -> Settings:
    return Settings(
        database_url=os.environ["TEST_DATABASE_URL"],
        jwt_secret="test-only-secret-0123456789abcdef0123456789",
        admin_email=ADMIN["email"],
        admin_password=ADMIN["password"],
        seed_demo_data=True,
    )


@pytest_asyncio.fixture
async def container():
    c = Container(settings(), redis_client=fakeredis.aioredis.FakeRedis(), publisher=FakePublisher())
    await create_schema(c.engine, drop=True)
    await c.start(background=False)
    yield c
    await c.stop()


@pytest_asyncio.fixture
async def client(container):
    app = create_app(container)
    # raise_app_exceptions=False: как в реальном сервере, клиент получает ответ 500, а не исключение
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
        yield api


async def token(api: httpx.AsyncClient, email: str, password: str) -> dict:
    response = await api.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin(client):
    return await token(client, ADMIN["email"], ADMIN["password"])


@pytest_asyncio.fixture
async def user(client):
    await client.post(
        "/auth/register", json={"email": "client@example.com", "password": "Client2026", "full_name": "ООО Клиент"}
    )
    return await token(client, "client@example.com", "Client2026")


@pytest_asyncio.fixture
async def other_user(client):
    await client.post(
        "/auth/register", json={"email": "other@example.com", "password": "Other2026", "full_name": "ИП Другой"}
    )
    return await token(client, "other@example.com", "Other2026")


def order_payload(**changes) -> dict:
    pickup = datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)
    data = {
        "origin": "Москва",
        "destination": "Санкт-Петербург",
        "cargo": "Оргтехника, 12 коробок",
        "weight_kg": 1200,
        "pickup_at": pickup.isoformat(),
        "deadline_at": (pickup + timedelta(days=1)).isoformat(),
    }
    data.update(changes)
    return data


@pytest.fixture
def make_order():
    return order_payload
