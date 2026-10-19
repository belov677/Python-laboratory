"""Redis-кэш: cache-aside, TTL, инвалидирование, счётчики популярности."""
from __future__ import annotations

import json
import logging

import redis

log = logging.getLogger("cache")


class RedisCache:
    def __init__(self, url: str, ttl: int) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=1)
        self.ttl = ttl

    def get(self, key: str):
        try:
            value = self.client.get(key)
        except redis.RedisError as error:          # Redis недоступен — работаем без кэша
            log.warning("Redis unavailable: %s", error)
            return None
        return json.loads(value) if value is not None else None

    def set(self, key: str, value, ttl: int | None = None) -> None:
        try:
            self.client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl or self.ttl)
        except redis.RedisError as error:
            log.warning("Redis unavailable: %s", error)

    def delete(self, *keys: str) -> None:
        try:
            self.client.delete(*keys)
        except redis.RedisError as error:
            log.warning("Redis unavailable: %s", error)

    def hit(self, item_id: int) -> None:
        """Учёт частых запросов: счётчик + рейтинг в sorted set."""
        try:
            self.client.incr("stats:item_requests")
            self.client.zincrby("items:popular", 1, item_id)
        except redis.RedisError:
            pass

    def popular(self, count: int = 5) -> list[tuple[str, float]]:
        try:
            return self.client.zrevrange("items:popular", 0, count - 1, withscores=True)
        except redis.RedisError:
            return []

    def info(self) -> dict:
        try:
            keys = sorted(self.client.scan_iter("item*"))
            return {"keys": {k: self.client.ttl(k) for k in keys},
                    "item_requests": int(self.client.get("stats:item_requests") or 0)}
        except redis.RedisError as error:
            return {"error": str(error)}
