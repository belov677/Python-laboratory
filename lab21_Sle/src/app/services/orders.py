"""Заказы клиентов."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.core.events import add_event
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.entities import DeliveryStatus, Order, OrderStatus, Role, User
from app.repositories.repositories import DeliveryRepository, OrderRepository, RouteRepository
from app.schemas.dto import OrderIn

log = logging.getLogger("app.orders")
SORTS = ("created_at", "-created_at", "pickup_at", "-pickup_at", "weight", "-weight")


def utcnow() -> datetime:
    return datetime.now(UTC)


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        routes: RouteRepository,
        deliveries: DeliveryRepository,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.orders, self.routes, self.deliveries = orders, routes, deliveries
        self.session = orders.session
        self.now = now

    async def _check(self, data: OrderIn) -> None:
        # Правило 1: подача не может быть в прошлом
        if data.pickup_at <= self.now():
            raise BusinessRuleError("Время подачи должно быть в будущем", code="PICKUP_IN_PAST")
        # Правило 2: перевозка выполняется только по маршрутам компании
        route = await self.routes.find(data.origin, data.destination)
        if route is None:
            raise BusinessRuleError(
                f"Компания не обслуживает направление {data.origin} → {data.destination}", code="NO_ROUTE"
            )
        # Правило 3: срок доставки должен быть достижим (время в пути по маршруту)
        hours = (data.deadline_at - data.pickup_at).total_seconds() / 3600
        if hours < route.duration_h:
            raise BusinessRuleError(
                f"Срок нереалистичен: по маршруту {route.code} в пути {route.duration_h} ч, а отведено {hours:.1f} ч",
                code="DEADLINE_TOO_SHORT",
            )

    async def create(self, data: OrderIn, user: User) -> Order:
        await self._check(data)
        order = await self.orders.add(Order(customer_id=user.id, **data.model_dump()))
        add_event(
            self.session,
            "OrderCreated",
            {"order_id": order.id, "customer_id": user.id, "route": f"{order.origin} → {order.destination}"},
        )
        await self.session.commit()
        log.info(
            "заказ %s создан клиентом %s: %s → %s, %s кг",
            order.id,
            user.email,
            order.origin,
            order.destination,
            order.weight_kg,
        )
        return order

    async def get(self, order_id: int, user: User) -> Order:
        order = await self.orders.get(order_id)
        if order is None:
            raise NotFoundError("Заказ", order_id)
        if user.role != Role.ADMIN and order.customer_id != user.id:
            raise ForbiddenError("Это заказ другого клиента", code="NOT_OWNER")
        return order

    async def search(
        self, user: User, status: OrderStatus | None, city: str | None, sort: str, page: int, size: int
    ) -> tuple[list[Order], int]:
        customer = None if user.role == Role.ADMIN else user.id  # клиент видит только свои заказы
        return await self.orders.search(customer_id=customer, status=status, city=city, sort=sort, page=page, size=size)

    async def update(self, order_id: int, data: OrderIn, user: User) -> Order:
        order = await self.get(order_id, user)
        if order.status != OrderStatus.NEW:
            raise BusinessRuleError(
                "Изменить можно только заказ в статусе NEW (до назначения рейса)", code="ORDER_LOCKED"
            )
        await self._check(data)
        for key, value in data.model_dump().items():
            setattr(order, key, value)
        await self.session.commit()
        return order

    async def cancel(self, order_id: int, user: User) -> Order:
        order = await self.get(order_id, user)
        if order.status not in (OrderStatus.NEW, OrderStatus.SCHEDULED):
            raise BusinessRuleError(
                f"Заказ в статусе {order.status.value} отменить нельзя", code="ORDER_NOT_CANCELLABLE"
            )
        delivery = await self.deliveries.active_for_order(order.id)
        if delivery is not None:
            delivery.status = DeliveryStatus.CANCELLED  # освобождаем машину и водителя
        order.status = OrderStatus.CANCELLED
        add_event(self.session, "OrderCancelled", {"order_id": order.id, "customer_id": order.customer_id})
        await self.session.commit()
        log.info("заказ %s отменён (%s)", order.id, user.email)
        return order
