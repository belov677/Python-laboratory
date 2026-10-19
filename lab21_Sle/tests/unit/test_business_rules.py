"""Unit: бизнес-правила сервисов заказов и доставок; репозитории заменены Mock-объектами."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.entities import (
    Delivery,
    DeliveryStatus,
    Driver,
    Order,
    OrderStatus,
    Role,
    Route,
    Vehicle,
    VehicleCategory,
    VehicleStatus,
)
from app.schemas.dto import OrderIn
from app.services.deliveries import DeliveryService, calculate_cost
from app.services.orders import OrderService

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)
ROUTE = Route(id=1, code="R-101", origin="Москва", destination="Санкт-Петербург", distance_km=710, duration_h=9.5)
USER = SimpleNamespace(id=5, role=Role.USER, email="u@test")
ADMIN = SimpleNamespace(id=1, role=Role.ADMIN, email="a@test")


def repo(**methods):
    mock = MagicMock()
    mock.session = MagicMock(commit=AsyncMock(), rollback=AsyncMock(), add=MagicMock())
    for name, value in methods.items():
        setattr(mock, name, AsyncMock(return_value=value))
    return mock


def order_in(hours=24, pickup_delta=timedelta(days=1)):
    pickup = NOW + pickup_delta
    return OrderIn(
        origin="Москва",
        destination="Санкт-Петербург",
        cargo="Мебель",
        weight_kg=1000,
        pickup_at=pickup,
        deadline_at=pickup + timedelta(hours=hours),
    )


def order_service(route=ROUTE, order=None):
    orders = repo(get=order, add=None)
    orders.add.side_effect = lambda o: (setattr(o, "id", 10), o)[1]
    return OrderService(orders, repo(find=route), repo(active_for_order=None), now=lambda: NOW), orders


async def test_create_order_writes_outbox_event():
    service, orders = order_service()
    order = await service.create(order_in(), USER)
    assert order.customer_id == 5 and order.id == 10
    event = orders.session.add.call_args.args[0]  # событие в той же транзакции
    assert (event.name, event.payload["order_id"]) == ("OrderCreated", 10)
    orders.session.commit.assert_awaited_once()


@pytest.mark.parametrize(
    "kwargs, route, code",
    [
        ({"pickup_delta": timedelta(hours=-1)}, ROUTE, "PICKUP_IN_PAST"),
        ({}, None, "NO_ROUTE"),
        ({"hours": 5}, ROUTE, "DEADLINE_TOO_SHORT"),  # 5 ч < 9,5 ч в пути
    ],
)
async def test_order_business_rules(kwargs, route, code):
    service, orders = order_service(route=route)
    with pytest.raises(BusinessRuleError) as info:
        await service.create(order_in(**kwargs), USER)
    assert info.value.code == code
    orders.add.assert_not_awaited()


async def test_user_cannot_read_foreign_order_but_admin_can():
    foreign = Order(id=3, customer_id=99, status=OrderStatus.NEW)
    service, _ = order_service(order=foreign)
    with pytest.raises(ForbiddenError):
        await service.get(3, USER)
    assert await service.get(3, ADMIN) is foreign


async def test_order_in_transit_cannot_be_cancelled():
    service, _ = order_service(order=Order(id=3, customer_id=5, status=OrderStatus.IN_TRANSIT))
    with pytest.raises(BusinessRuleError, match="отменить нельзя"):
        await service.cancel(3, USER)


def vehicle(**kw):
    return Vehicle(
        **{
            "id": 2,
            "plate": "Е303ЕЕ78",
            "model": "КАМАЗ",
            "category": VehicleCategory.C,
            "capacity_kg": 15000,
            "status": VehicleStatus.ACTIVE,
            **kw,
        }
    )


def driver(**kw):
    return Driver(**{"id": 3, "full_name": "Смирнов О.И.", "license_categories": ["B", "C"], "active": True, **kw})


def delivery_service(order, vehicle_=None, driver_=None, vehicle_busy=False, driver_busy=False):
    deliveries = repo(vehicle_busy=vehicle_busy, driver_busy=driver_busy, add=None)
    return DeliveryService(
        deliveries,
        repo(get=order),
        repo(find=ROUTE),
        repo(get=vehicle_ or vehicle()),
        repo(get=driver_ or driver()),
        now=lambda: NOW,
    ), deliveries


def new_order(weight=1200, deadline_h=48):
    return Order(
        id=10,
        customer_id=5,
        origin="Москва",
        destination="Санкт-Петербург",
        weight_kg=weight,
        pickup_at=NOW + timedelta(days=1),
        deadline_at=NOW + timedelta(days=1, hours=deadline_h),
        status=OrderStatus.NEW,
    )


async def test_create_delivery_checks_all_entities_and_schedules_order():
    order = new_order()
    service, deliveries = delivery_service(order)
    delivery = await service.create(10, 2, 3, ADMIN)
    assert delivery.cost == 1500 + 710 * 45  # категория C — 45 руб./км
    assert delivery.planned_end - delivery.planned_start == timedelta(hours=10.5)  # 9,5 ч + погрузка
    assert order.status == OrderStatus.SCHEDULED
    deliveries.vehicle_busy.assert_awaited_once_with(2, delivery.planned_start, delivery.planned_end)
    deliveries.driver_busy.assert_awaited_once_with(3, delivery.planned_start, delivery.planned_end)


@pytest.mark.parametrize(
    "setup, code",
    [
        ({"vehicle_": vehicle(capacity_kg=1000)}, "VEHICLE_CAPACITY"),
        ({"vehicle_": vehicle(status=VehicleStatus.MAINTENANCE)}, "VEHICLE_INACTIVE"),
        ({"driver_": driver(license_categories=["B"])}, "DRIVER_LICENSE"),
        ({"driver_": driver(active=False)}, "DRIVER_INACTIVE"),
        ({"vehicle_busy": True}, "VEHICLE_BUSY"),
        ({"driver_busy": True}, "DRIVER_BUSY"),
    ],
)
async def test_create_delivery_rules(setup, code):
    service, deliveries = delivery_service(new_order(), **setup)
    with pytest.raises(BusinessRuleError) as info:
        await service.create(10, 2, 3, ADMIN)
    assert info.value.code == code
    deliveries.add.assert_not_awaited()


async def test_delivery_cannot_finish_after_deadline():
    service, _ = delivery_service(new_order(deadline_h=6))
    with pytest.raises(BusinessRuleError) as info:
        await service.create(10, 2, 3, ADMIN)
    assert info.value.code == "DEADLINE_UNREACHABLE"


async def test_create_delivery_for_missing_order():
    service, _ = delivery_service(None)
    with pytest.raises(NotFoundError):
        await service.create(404, 2, 3, ADMIN)


@pytest.mark.parametrize(
    "category, expected",
    [(VehicleCategory.B, 1500 + 710 * 30), (VehicleCategory.C, 1500 + 710 * 45), (VehicleCategory.CE, 1500 + 710 * 60)],
)
def test_calculate_cost(category, expected):
    assert calculate_cost(ROUTE, vehicle(category=category)) == expected


async def test_invalid_status_transition():
    delivery = Delivery(id=1, status=DeliveryStatus.PLANNED, order=new_order(), order_id=10)
    service = DeliveryService(repo(get=delivery), repo(), repo(), repo(), repo(), now=lambda: NOW)
    with pytest.raises(BusinessRuleError, match="complete"):
        await service.change_status(1, "complete")  # нельзя завершить, не начав
    started = await service.change_status(1, "start")
    assert started.status == DeliveryStatus.IN_TRANSIT and started.order.status == OrderStatus.IN_TRANSIT
