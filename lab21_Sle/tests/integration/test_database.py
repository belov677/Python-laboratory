"""Интеграционные: сервисы и репозитории с настоящей PostgreSQL (без Mock)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.entities import Delivery, Order, OutboxEvent, User
from app.repositories.repositories import OrderRepository
from app.services.notifications import handle_event


async def make_order(session, customer_id, origin="Москва", destination="Санкт-Петербург", weight=1000, days=2):
    pickup = datetime.now(UTC) + timedelta(days=days)
    order = Order(
        customer_id=customer_id,
        origin=origin,
        destination=destination,
        cargo="Груз",
        weight_kg=weight,
        pickup_at=pickup,
        deadline_at=pickup + timedelta(days=1),
    )
    session.add(order)
    await session.flush()
    return order


async def test_exclude_constraint_blocks_overlapping_trips_in_database(container):
    """Даже в обход сервиса БД не даст назначить одну машину на пересекающиеся рейсы."""
    async with container.sessions() as session:
        admin = await session.scalar(select(User))
        first, second = await make_order(session, admin.id), await make_order(session, admin.id)
        start = first.pickup_at
        for order, shift in ((first, 0), (second, 5)):  # второй рейс начинается через 5 ч
            session.add(
                Delivery(
                    order_id=order.id,
                    route_id=1,
                    vehicle_id=3,
                    driver_id=3 if shift else 2,
                    planned_start=start + timedelta(hours=shift),
                    planned_end=start + timedelta(hours=shift + 10),
                    cost=1,
                )
            )
        with pytest.raises(IntegrityError, match="ex_vehicle_busy"):
            await session.commit()


async def test_order_search_filters_sorts_and_paginates(container):
    async with container.sessions() as session:
        admin = await session.scalar(select(User))
        for weight, (o, d) in zip(
            (500, 3000, 1500), (("Москва", "Казань"), ("Казань", "Самара"), ("Москва", "Санкт-Петербург")), strict=True
        ):
            await make_order(session, admin.id, o, d, weight)
        await session.commit()
        repo = OrderRepository(session)
        items, total = await repo.search(customer_id=None, status=None, city="казань", sort="-weight", page=1, size=10)
        assert total == 2 and [o.weight_kg for o in items] == [3000, 500]
        items, total = await repo.search(customer_id=admin.id, status=None, city=None, sort="weight", page=2, size=2)
        assert total == 3 and [o.weight_kg for o in items] == [3000]


async def test_outbox_relay_survives_broker_outage(container):
    publisher = container.publisher
    async with container.sessions() as session:
        session.add(OutboxEvent(event_id="e1", name="OrderCreated", payload={"order_id": 1}))
        await session.commit()
    publisher.up = False
    assert await container.outbox.flush() == 0  # брокер недоступен — событие ждёт
    publisher.up = True
    assert await container.outbox.flush() == 1
    assert await container.outbox.flush() == 0  # повторно не отправляется
    assert publisher.events[0]["name"] == "OrderCreated"


async def test_worker_creates_notification_once(container):
    async with container.sessions() as session:
        admin = await session.scalar(select(User))
    event = {"id": "evt-1", "name": "OrderCancelled", "payload": {"order_id": 5, "customer_id": admin.id}}
    first = await handle_event(container.sessions, event)
    second = await handle_event(container.sessions, event)  # повторная доставка
    assert first.text == "Заказ №5 отменён." and second is None
