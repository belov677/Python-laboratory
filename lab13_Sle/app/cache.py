"""RedisCache: кэш карточек (String + TTL), остатки (Hash), популярность (Sorted Set),
последние поиски (List), товары с низким остатком (Set), блокировка от cache stampede,
публикация событий (Pub/Sub)."""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager

import redis

log = logging.getLogger("cache")

STOCK = "warehouse:stock"          # Hash: sku → количество
POPULAR = "items:popular"          # Sorted Set: sku → число запросов
RECENT = "search:recent"           # List: последние поисковые запросы
LOW = "items:low"                  # Set: артикулы ниже минимального остатка
EVENTS = "warehouse.events"        # канал Pub/Sub


class RedisCache:
    def __init__(self, client: redis.Redis, ttl: int) -> None:
        self.r = client
        self.ttl = ttl
        self.available = True

    def _safe(self, func, default=None):
        try:
            result = func()
            self.available = True
            return result
        except redis.RedisError as error:
            if self.available:
                log.warning("Redis недоступен: %s — работа без кэша", error)
            self.available = False
            return default

    @staticmethod
    def item_key(sku: str) -> str:
        return f"item:{sku}"

    # --- String + TTL ---
    def get_item(self, sku: str) -> dict | None:
        raw = self._safe(lambda: self.r.get(self.item_key(sku)))
        return json.loads(raw) if raw else None

    def set_item(self, sku: str, data: dict) -> None:
        self._safe(lambda: self.r.set(self.item_key(sku), json.dumps(data, ensure_ascii=False),
                                      ex=self.ttl))

    def invalidate(self, sku: str) -> None:
        self._safe(lambda: self.r.delete(self.item_key(sku)))

    def ttl_of(self, sku: str) -> int:
        return self._safe(lambda: self.r.ttl(self.item_key(sku)), -2)

    # --- защита от cache stampede ---
    @contextmanager
    def lock(self, sku: str, timeout: float = 5.0):
        """SET NX EX: только один процесс загружает отсутствующий объект из MongoDB."""
        key, acquired = f"lock:{sku}", False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            acquired = self._safe(lambda: self.r.set(key, "1", nx=True, ex=10), True)
            if acquired:
                break
            time.sleep(0.02)
        try:
            yield acquired
        finally:
            if acquired:
                self._safe(lambda: self.r.delete(key))

    # --- Hash: остатки ---
    def set_stock(self, sku: str, quantity: int, low: bool) -> None:
        def run():
            pipe = self.r.pipeline()
            pipe.hset(STOCK, sku, quantity)
            pipe.sadd(LOW, sku) if low else pipe.srem(LOW, sku)
            pipe.execute()
        self._safe(run)

    def remove_stock(self, sku: str) -> None:
        self._safe(lambda: (self.r.hdel(STOCK, sku), self.r.srem(LOW, sku)))

    def stock(self, sku: str) -> int | None:
        value = self._safe(lambda: self.r.hget(STOCK, sku))
        return int(value) if value is not None else None

    def all_stock(self) -> dict[str, int]:
        return {k: int(v) for k, v in (self._safe(lambda: self.r.hgetall(STOCK), {}) or {}).items()}

    def low_skus(self) -> set[str]:
        return self._safe(lambda: self.r.smembers(LOW), set())

    # --- Sorted Set: популярные товары ---
    def hit(self, sku: str) -> None:
        self._safe(lambda: self.r.zincrby(POPULAR, 1, sku))

    def popular(self, n: int = 5) -> list[tuple[str, float]]:
        return self._safe(lambda: self.r.zrevrange(POPULAR, 0, n - 1, withscores=True), [])

    # --- List: последние поиски ---
    def remember_search(self, text: str) -> None:
        def run():
            self.r.lpush(RECENT, text)
            self.r.ltrim(RECENT, 0, 9)
        self._safe(run)

    def recent_searches(self) -> list[str]:
        return self._safe(lambda: self.r.lrange(RECENT, 0, -1), [])

    # --- Pub/Sub ---
    def publish(self, event: str, sku: str) -> None:
        self._safe(lambda: self.r.publish(EVENTS, json.dumps({"event": event, "sku": sku})))

    # --- обслуживание ---
    def status(self) -> dict:
        def run():
            keys = sorted(self.r.scan_iter("item:*"))
            return {"cached_items": {k: self.r.ttl(k) for k in keys},
                    "stock_hash_size": self.r.hlen(STOCK), "low": sorted(self.r.smembers(LOW)),
                    "popular": self.r.zrevrange(POPULAR, 0, 4, withscores=True),
                    "recent_searches": self.r.lrange(RECENT, 0, 4),
                    "memory": self.r.info("memory")["used_memory_human"]}
        return self._safe(run, {"error": "Redis недоступен"})

    def clear(self) -> int:
        def run():
            keys = list(self.r.scan_iter("item:*")) + [STOCK, POPULAR, RECENT, LOW]
            return self.r.delete(*keys) if keys else 0
        return self._safe(run, 0)
