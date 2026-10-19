"""События предметной области: запись в outbox, публикация в RabbitMQ, приём worker-ом."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import OutboxEvent

log = logging.getLogger("app.events")
EXCHANGE = "logistics.final"


def add_event(session: AsyncSession, name: str, payload: dict) -> None:
    """Добавить событие в outbox текущей транзакции (публикуется после фиксации)."""
    session.add(OutboxEvent(event_id=uuid.uuid4().hex, name=name, payload=payload))


class RabbitPublisher:
    def __init__(self, url: str) -> None:
        self.url = url
        self.connection = None
        self.exchange = None

    async def connect(self) -> None:
        import aio_pika

        self.connection = await aio_pika.connect_robust(self.url)
        channel = await self.connection.channel()
        self.exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    async def publish(self, event_id: str, name: str, payload: dict) -> None:
        import aio_pika

        body = json.dumps({"id": event_id, "name": name, "payload": payload}, ensure_ascii=False).encode()
        await self.exchange.publish(
            aio_pika.Message(
                body,
                message_id=event_id,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=name,
        )

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()


class OutboxRelay:
    """Фоновая публикация неотправленных событий (at-least-once)."""

    def __init__(self, sessions, publisher, interval: float = 2.0) -> None:
        self.sessions = sessions
        self.publisher = publisher
        self.interval = interval
        self.task: asyncio.Task | None = None

    async def flush(self) -> int:
        if self.publisher is None:
            return 0
        sent = 0
        async with self.sessions() as session:
            stmt = (
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
            for event in await session.scalars(stmt):
                try:
                    await self.publisher.publish(event.event_id, event.name, event.payload)
                except Exception as error:  # noqa: BLE001 — брокер недоступен, повторим позже
                    log.warning("событие %s не опубликовано: %s", event.name, error)
                    break
                event.published_at = datetime.now(UTC)
                sent += 1
                log.info("событие опубликовано: %s %s", event.name, event.payload)
            await session.commit()
        return sent

    async def backlog(self) -> int:
        """Количество событий, ожидающих публикации (растёт, если брокер недоступен)."""
        async with self.sessions() as session:
            return await session.scalar(
                select(func.count()).select_from(OutboxEvent).where(OutboxEvent.published_at.is_(None))
            )

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            try:
                await self.flush()
            except Exception as error:  # noqa: BLE001  # pragma: no cover
                log.error("ошибка outbox: %s", error)

    def start(self) -> None:
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()


async def consume(url: str, queue_name: str, events: list[str], handler: Callable[[dict], Awaitable[None]]) -> object:
    """Подписка worker-а: durable-очередь, подтверждение после успешной обработки."""
    import aio_pika

    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    # prefetch=1: события обрабатываются по одному в порядке публикации — иначе уведомление
    # «груз доставлен» могло бы появиться раньше «груз в пути»
    await channel.set_qos(prefetch_count=1)
    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue(queue_name, durable=True)
    for name in events:
        await queue.bind(exchange, routing_key=name)

    async def on_message(message) -> None:
        async with message.process(requeue=True):
            await handler(json.loads(message.body))

    await queue.consume(on_message)
    return connection
