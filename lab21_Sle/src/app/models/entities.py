"""ORM-модели: пользователи, маршруты, транспорт, водители, заказы, доставки, события, уведомления."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Role(enum.StrEnum):
    USER = "USER"  # клиент: свои заказы
    ADMIN = "ADMIN"  # диспетчер: справочники, доставки, все заказы


class VehicleCategory(enum.StrEnum):
    B = "B"  # до 3,5 т
    C = "C"  # грузовой
    CE = "CE"  # тягач с прицепом


class VehicleStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"


class OrderStatus(enum.StrEnum):
    NEW = "NEW"
    SCHEDULED = "SCHEDULED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class DeliveryStatus(enum.StrEnum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


def _enum(cls, name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), default=Role.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    orders: Mapped[list[Order]] = relationship(back_populates="customer", lazy="raise")


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint("origin", "destination", name="uq_route_direction"),
        CheckConstraint("distance_km > 0", name="ck_route_distance"),
        CheckConstraint("duration_h > 0", name="ck_route_duration"),
        CheckConstraint("origin <> destination", name="ck_route_points"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    origin: Mapped[str] = mapped_column(String(100), index=True)
    destination: Mapped[str] = mapped_column(String(100))
    distance_km: Mapped[int]
    duration_h: Mapped[float]
    waypoints: Mapped[list] = mapped_column(JSON, default=list)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (CheckConstraint("capacity_kg > 0", name="ck_vehicle_capacity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(15), unique=True)
    model: Mapped[str] = mapped_column(String(80))
    category: Mapped[VehicleCategory] = mapped_column(_enum(VehicleCategory, "vehicle_category"))
    capacity_kg: Mapped[int]
    status: Mapped[VehicleStatus] = mapped_column(_enum(VehicleStatus, "vehicle_status"), default=VehicleStatus.ACTIVE)


class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    license_number: Mapped[str] = mapped_column(String(20), unique=True)
    license_categories: Mapped[list] = mapped_column(JSON)  # ["B", "C"]
    phone: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(default=True)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="ck_order_weight"),
        CheckConstraint("deadline_at > pickup_at", name="ck_order_dates"),
        Index("ix_orders_status_created", "status", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    cargo: Mapped[str] = mapped_column(String(200))
    weight_kg: Mapped[int]
    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"), default=OrderStatus.NEW)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    customer: Mapped[User] = relationship(back_populates="orders", lazy="joined")
    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="order", order_by="Delivery.id", lazy="raise"
    )  # только явные запросы через репозиторий


ACTIVE_DELIVERY = text("status <> 'CANCELLED'")


class Delivery(Base):
    """Рейс: заказ + маршрут + машина + водитель в интервале времени."""

    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint("planned_end > planned_start", name="ck_delivery_interval"),
        CheckConstraint("cost >= 0", name="ck_delivery_cost"),
        # Вторая линия защиты от двойного назначения: PostgreSQL не даст сохранить пересекающиеся
        # по времени активные рейсы одной машины или одного водителя (GiST-индекс, btree_gist).
        ExcludeConstraint(
            ("vehicle_id", "="),
            (func.tstzrange(text("planned_start"), text("planned_end")), "&&"),
            name="ex_vehicle_busy",
            using="gist",
            where=ACTIVE_DELIVERY,
        ),
        ExcludeConstraint(
            ("driver_id", "="),
            (func.tstzrange(text("planned_start"), text("planned_end")), "&&"),
            name="ex_driver_busy",
            using="gist",
            where=ACTIVE_DELIVERY,
        ),
        # не более одного активного рейса на заказ
        Index("ux_delivery_active_order", "order_id", unique=True, postgresql_where=ACTIVE_DELIVERY),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="RESTRICT"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="RESTRICT"))
    planned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[DeliveryStatus] = mapped_column(
        _enum(DeliveryStatus, "delivery_status"), default=DeliveryStatus.PLANNED
    )
    cost: Mapped[float] = mapped_column(Numeric(12, 2))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order] = relationship(back_populates="deliveries", lazy="joined")
    route: Mapped[Route] = relationship(lazy="joined")
    vehicle: Mapped[Vehicle] = relationship(lazy="joined")
    driver: Mapped[Driver] = relationship(lazy="joined")


class OutboxEvent(Base):
    """Transactional Outbox: событие сохраняется в одной транзакции с изменением данных."""

    __tablename__ = "outbox_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Notification(Base):
    """Уведомление клиенту, созданное фоновым worker по событию (отправка SMS/e-mail имитируется)."""

    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True)  # идемпотентность worker
    channel: Mapped[str] = mapped_column(String(10), default="email")
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
