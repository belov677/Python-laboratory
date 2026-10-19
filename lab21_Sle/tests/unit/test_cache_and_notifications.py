"""Unit: кэш Redis (hit/miss/bypass, Circuit Breaker) и тексты уведомлений."""

from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from app.core.cache import RedisCache
from app.services.notifications import render


async def test_cache_miss_then_hit_and_invalidate():
    cache = RedisCache(fakeredis.aioredis.FakeRedis(), ttl=60)
    loader = AsyncMock(return_value=[{"id": 1}])
    assert await cache.get_or_load("routes:list:*", loader) == ([{"id": 1}], "MISS")
    assert await cache.get_or_load("routes:list:*", loader) == ([{"id": 1}], "HIT")
    loader.assert_awaited_once()  # второй раз БД не запрашивается
    await cache.invalidate("routes:*")
    assert (await cache.get_or_load("routes:list:*", loader))[1] == "MISS"
    assert cache.stats == {"hit": 1, "miss": 2, "bypass": 0}


async def test_cache_bypass_and_circuit_breaker_when_redis_is_down():
    now = {"t": 0.0}
    broken = MagicMock()
    broken.get = AsyncMock(side_effect=ConnectionError("redis down"))
    cache = RedisCache(broken, failure_threshold=2, recovery_timeout=10, clock=lambda: now["t"])
    loader = AsyncMock(return_value="из БД")
    for _ in range(3):
        assert await cache.get_or_load("k", loader) == ("из БД", "BYPASS")
    assert broken.get.await_count == 2  # после 2 сбоев Redis больше не опрашивается
    now["t"] = 11  # прошёл recovery_timeout — пробный запрос
    broken.get = AsyncMock(return_value=None)
    broken.set = AsyncMock()
    assert (await cache.get_or_load("k", loader))[1] == "MISS"
    assert cache.available


@pytest.mark.parametrize(
    "name, payload, fragment",
    [
        ("OrderCreated", {"order_id": 7, "route": "Москва → Казань", "customer_id": 1}, "принят"),
        (
            "DeliveryScheduled",
            {
                "order_id": 7,
                "vehicle": "КАМАЗ Е303ЕЕ78",
                "driver": "Смирнов",
                "start": "2026-11-02T09:00:00+00:00",
                "cost": 33450,
                "customer_id": 1,
            },
            "02.11.2026 09:00",
        ),
        ("DeliveryStatusChanged", {"order_id": 7, "status": "DELIVERED", "customer_id": 1}, "груз доставлен"),
        ("OrderCancelled", {"order_id": 7, "customer_id": 1}, "отменён"),
    ],
)
def test_notification_texts(name, payload, fragment):
    assert fragment in render({"id": "x", "name": name, "payload": payload})


def test_unknown_event_is_ignored():
    assert render({"id": "x", "name": "Something", "payload": {}}) is None
