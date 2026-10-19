"""Контейнер зависимостей: БД, Redis, брокер, фоновая публикация событий."""

from __future__ import annotations

import logging

from app.config import Settings
from app.core.cache import RedisCache
from app.core.database import create_schema, make_engine, make_sessions
from app.core.events import OutboxRelay, RabbitPublisher
from app.core.observability import Metrics

log = logging.getLogger("app")


class Container:
    def __init__(self, settings: Settings, redis_client=None, publisher=None) -> None:
        self.settings = settings
        self.engine = make_engine(settings.database_url)
        self.sessions = make_sessions(self.engine)
        if redis_client is None and settings.redis_url:
            import redis.asyncio as redis

            redis_client = redis.from_url(settings.redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
        self.cache = RedisCache(redis_client, ttl=settings.cache_ttl_seconds)
        if publisher is None and settings.broker_url:
            publisher = RabbitPublisher(settings.broker_url)
        self.publisher = publisher
        self.outbox = OutboxRelay(self.sessions, publisher, settings.outbox_interval)
        self.metrics = Metrics()
        self.broker_ok = False

    async def start(self, create: bool = False, background: bool = True) -> None:
        if create:
            await create_schema(self.engine)
        if self.publisher is not None:
            try:
                await self.publisher.connect()
                self.broker_ok = True
            except Exception as error:  # noqa: BLE001 — события подождут в outbox
                log.warning("брокер недоступен при запуске (%s); события будут отправлены позже", error)
        if background:
            self.outbox.start()
        from app.seed import seed

        await seed(self)
        log.info("приложение запущено")

    async def stop(self) -> None:
        await self.outbox.stop()
        if self.publisher is not None:
            await self.publisher.close()
        if self.cache.client is not None:
            await self.cache.client.aclose()
        await self.engine.dispose()
