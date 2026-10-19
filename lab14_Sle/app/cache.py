"""Redis: кэш GET /items/{id} (cache-aside, TTL), инвалидирование, Pub/Sub событий."""
from __future__ import annotations

import json
import logging

import redis

log = logging.getLogger("cache")


class ItemCache:
    CHANNEL = "items.events"

    def __init__(self, url: str, ttl: int) -> None:
        self.r = redis.Redis.from_url(url, decode_responses=True, socket_timeout=1,
                                      socket_connect_timeout=1)
        self.ttl = ttl

    @staticmethod
    def key(item_id: int) -> str:
        return f"item:{item_id}"

    def get(self, item_id: int) -> dict | None:
        try:
            raw = self.r.get(self.key(item_id))
        except redis.RedisError as error:
            log.warning("Redis недоступен: %s", error)
            return None
        return json.loads(raw) if raw else None

    def set(self, item_id: int, data: dict) -> None:
        try:
            self.r.set(self.key(item_id), json.dumps(data, ensure_ascii=False, default=str),
                       ex=self.ttl)
        except redis.RedisError as error:
            log.warning("Redis недоступен: %s", error)

    def invalidate(self, item_id: int) -> None:
        try:
            self.r.delete(self.key(item_id))
        except redis.RedisError:
            pass

    def publish(self, event: str, item_id: int) -> None:
        try:
            self.r.publish(self.CHANNEL, json.dumps({"event": event, "item_id": item_id}))
        except redis.RedisError:
            pass
