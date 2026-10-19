"""Доступ к данным: только SQLAlchemy, без бизнес-правил."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Delivery,
    DeliveryStatus,
    Driver,
    Notification,
    Order,
    OrderStatus,
    Route,
    User,
    Vehicle,
    VehicleStatus,
)

T = TypeVar("T")


class Repository(Generic[T]):  # noqa: UP046 — явная форма понятнее в учебном коде
    model: type

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: int) -> T | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)

    async def list(self, stmt: Select | None = None) -> list[T]:
        return list((await self.session.scalars(stmt if stmt is not None else select(self.model))).unique())

    async def exists(self, *conditions) -> bool:
        return bool(await self.session.scalar(select(func.count()).select_from(self.model).where(*conditions)))


class UserRepository(Repository[User]):
    model = User

    async def by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))


class RouteRepository(Repository[Route]):
    model = Route

    async def search(self, origin: str | None = None) -> list[Route]:
        stmt = select(Route).order_by(Route.code)
        if origin:
            stmt = stmt.where(func.lower(Route.origin) == origin.lower())
        return await self.list(stmt)

    async def find(self, origin: str, destination: str) -> Route | None:
        return await self.session.scalar(
            select(Route).where(
                func.lower(Route.origin) == origin.strip().lower(),
                func.lower(Route.destination) == destination.strip().lower(),
            )
        )


class VehicleRepository(Repository[Vehicle]):
    model = Vehicle

    async def search(self, status: VehicleStatus | None, min_capacity: int | None, sort: str) -> list[Vehicle]:
        stmt = select(Vehicle)
        if status:
            stmt = stmt.where(Vehicle.status == status)
        if min_capacity:
            stmt = stmt.where(Vehicle.capacity_kg >= min_capacity)
        column = {"capacity": Vehicle.capacity_kg, "-capacity": Vehicle.capacity_kg.desc(), "plate": Vehicle.plate}.get(
            sort, Vehicle.id
        )
        return await self.list(stmt.order_by(column, Vehicle.id))


class DriverRepository(Repository[Driver]):
    model = Driver


class OrderRepository(Repository[Order]):
    model = Order

    async def search(
        self, *, customer_id: int | None, status: OrderStatus | None, city: str | None, sort: str, page: int, size: int
    ) -> tuple[list[Order], int]:
        conditions = []
        if customer_id is not None:
            conditions.append(Order.customer_id == customer_id)
        if status:
            conditions.append(Order.status == status)
        if city:
            pattern = f"%{city.lower()}%"
            conditions.append(or_(func.lower(Order.origin).like(pattern), func.lower(Order.destination).like(pattern)))
        where = and_(*conditions) if conditions else True
        total = await self.session.scalar(select(func.count()).select_from(Order).where(where))
        column = {
            "created_at": Order.created_at,
            "-created_at": Order.created_at.desc(),
            "pickup_at": Order.pickup_at,
            "-pickup_at": Order.pickup_at.desc(),
            "weight": Order.weight_kg,
            "-weight": Order.weight_kg.desc(),
        }[sort]
        stmt = select(Order).where(where).order_by(column, Order.id).offset((page - 1) * size).limit(size)
        return await self.list(stmt), total


class DeliveryRepository(Repository[Delivery]):
    model = Delivery

    @staticmethod
    def _overlap(start: datetime, end: datetime):
        return and_(
            Delivery.status != DeliveryStatus.CANCELLED, Delivery.planned_start < end, Delivery.planned_end > start
        )

    async def vehicle_busy(self, vehicle_id: int, start: datetime, end: datetime) -> bool:
        return await self.exists(Delivery.vehicle_id == vehicle_id, self._overlap(start, end))

    async def driver_busy(self, driver_id: int, start: datetime, end: datetime) -> bool:
        return await self.exists(Delivery.driver_id == driver_id, self._overlap(start, end))

    async def busy_ids(self, start: datetime, end: datetime) -> tuple[set[int], set[int]]:
        rows = (
            await self.session.execute(select(Delivery.vehicle_id, Delivery.driver_id).where(self._overlap(start, end)))
        ).all()
        return {r.vehicle_id for r in rows}, {r.driver_id for r in rows}

    async def active_for_order(self, order_id: int) -> Delivery | None:
        return await self.session.scalar(
            select(Delivery).where(Delivery.order_id == order_id, Delivery.status != DeliveryStatus.CANCELLED)
        )

    async def last_for_order(self, order_id: int) -> Delivery | None:
        return await self.session.scalar(
            select(Delivery).where(Delivery.order_id == order_id).order_by(Delivery.id.desc()).limit(1)
        )

    async def search(self, status: DeliveryStatus | None) -> list[Delivery]:
        stmt = select(Delivery).order_by(Delivery.planned_start)
        if status:
            stmt = stmt.where(Delivery.status == status)
        return await self.list(stmt)

    async def stats(self) -> dict:
        rows = (
            await self.session.execute(
                select(Delivery.status, func.count(), func.coalesce(func.sum(Delivery.cost), 0)).group_by(
                    Delivery.status
                )
            )
        ).all()
        return {status.value: {"count": count, "cost": float(total)} for status, count, total in rows}


class NotificationRepository(Repository[Notification]):
    model = Notification

    async def for_user(self, user_id: int) -> list[Notification]:
        return await self.list(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.id.desc())
        )
