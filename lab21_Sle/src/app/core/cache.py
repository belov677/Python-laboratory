"""Кэш Redis с плавной деградацией: при недоступности Redis приложение работает с БД напрямую.

Простой Circuit Breaker не даёт каждому запросу ждать тайм-аут неработающего Redis.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger("app.cache")


class RedisCache:
    def __init__(
        self,
        client,
        ttl: int = 300,
        failure_threshold: int = 3,
        recovery_timeout: float = 15.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client  # redis.asyncio.Redis или совместимый (fakeredis в тестах); None — кэш выключен
        self.ttl = ttl
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.clock = clock
        self.failures = 0
        self.opened_at: float | None = None
        self.stats = {"hit": 0, "miss": 0, "bypass": 0}

    @property
    def available(self) -> bool:
        if self.client is None:
            return False
        if self.opened_at is None:
            return True
        if self.clock() - self.opened_at >= self.recovery_timeout:  # HALF-OPEN: пробуем снова
            return True
        return False

    def _failed(self, error: Exception) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold and self.opened_at is None:
            log.warning("Redis недоступен (%s): кэш отключён на %.0f с", type(error).__name__, self.recovery_timeout)
        if self.failures >= self.failure_threshold:
            self.opened_at = self.clock()

    def _ok(self) -> None:
        if self.opened_at is not None:
            log.info("Redis снова доступен: кэш включён")
        self.failures, self.opened_at = 0, None

    async def get_or_load(self, key: str, loader: Callable[[], Awaitable[Any]]) -> tuple[Any, str]:
        """Возвращает (значение, HIT|MISS|BYPASS)."""
        if not self.available:
            self.stats["bypass"] += 1
            return await loader(), "BYPASS"
        try:
            cached = await self.client.get(key)
            self._ok()
        except Exception as error:  # noqa: BLE001 — любой сбой Redis не должен ломать запрос
            self._failed(error)
            self.stats["bypass"] += 1
            return await loader(), "BYPASS"
        if cached is not None:
            self.stats["hit"] += 1
            return json.loads(cached), "HIT"
        value = await loader()
        try:
            await self.client.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=self.ttl)
        except Exception as error:  # noqa: BLE001
            self._failed(error)
        self.stats["miss"] += 1
        return value, "MISS"

    async def invalidate(self, *patterns: str) -> None:
        if not self.available:
            return
        try:
            for pattern in patterns:
                keys = [k async for k in self.client.scan_iter(match=pattern)]
                if keys:
                    await self.client.delete(*keys)
        except Exception as error:  # noqa: BLE001
            self._failed(error)

    async def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            await self.client.ping()
            self._ok()
            return True
        except Exception as error:  # noqa: BLE001
            self._failed(error)
            return False
