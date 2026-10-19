"""Интеграционный: публикация в настоящий RabbitMQ и приём событий (пропускается без BROKER_URL)."""

import asyncio
import os
import uuid

import pytest

from app.core.events import RabbitPublisher, consume

pytestmark = pytest.mark.skipif(not os.getenv("BROKER_URL"), reason="нужен RabbitMQ (BROKER_URL)")


async def test_publish_and_consume_through_rabbitmq():
    received: asyncio.Queue = asyncio.Queue()
    queue = f"test-{uuid.uuid4().hex[:8]}"
    connection = await consume(os.environ["BROKER_URL"], queue, ["OrderCreated"], received.put)
    publisher = RabbitPublisher(os.environ["BROKER_URL"])
    await publisher.connect()
    await publisher.publish("evt-42", "OrderCreated", {"order_id": 42, "customer_id": 1})
    await publisher.publish("evt-43", "Other", {"order_id": 43})  # не подписаны — не придёт
    event = await asyncio.wait_for(received.get(), timeout=10)
    assert event == {"id": "evt-42", "name": "OrderCreated", "payload": {"order_id": 42, "customer_id": 1}}
    channel = await connection.channel()
    await channel.queue_delete(queue)
    await publisher.close()
    await connection.close()
