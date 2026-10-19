"""ORM-модели логистической компании (вариант 17)."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, Column, DateTime, Enum, ForeignKey, Numeric, String,
                        Table, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ShipmentStatus(enum.Enum):
    CREATED = "создано"
    IN_TRANSIT = "в пути"
    DELIVERED = "доставлено"
    CANCELLED = "отменено"


# many-to-many: одно отправление содержит несколько грузов, груз может быть
# перевезён несколькими отправлениями (например, с перегрузкой)
shipment_cargo = Table(
    "shipment_cargo", Base.metadata,
    Column("shipment_id", ForeignKey("shipments.id", ondelete="CASCADE"), primary_key=True),
    Column("cargo_id", ForeignKey("cargos.id", ondelete="CASCADE"), primary_key=True),
)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    shipments: Mapped[list["Shipment"]] = relationship(back_populates="client",
                                                       cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Client(id={self.id}, name={self.name!r}, city={self.city!r})"


class Cargo(Base):
    __tablename__ = "cargos"
    __table_args__ = (CheckConstraint("weight_kg > 0", name="ck_cargo_weight_positive"),
                      CheckConstraint("declared_value >= 0", name="ck_cargo_value"))

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(200))
    cargo_type: Mapped[str] = mapped_column(String(50))      # обычный, хрупкий, опасный...
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    declared_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    shipments: Mapped[list["Shipment"]] = relationship(secondary=shipment_cargo,
                                                       back_populates="cargos")

    def __repr__(self) -> str:
        return f"Cargo(id={self.id}, {self.description!r}, {self.weight_kg} кг)"


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (CheckConstraint("cost >= 0", name="ck_shipment_cost"),
                      CheckConstraint("distance_km > 0", name="ck_shipment_distance"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(20), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    distance_km: Mapped[int]
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, name="shipment_status"), default=ShipmentStatus.CREATED)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

    client: Mapped[Client] = relationship(back_populates="shipments")
    cargos: Mapped[list[Cargo]] = relationship(secondary=shipment_cargo,
                                               back_populates="shipments")
    events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan",
        order_by="TrackingEvent.created_at")

    @property
    def total_weight(self) -> Decimal:
        return sum((c.weight_kg for c in self.cargos), Decimal("0"))

    def __repr__(self) -> str:
        return f"Shipment({self.tracking_number}, {self.origin}→{self.destination}, {self.status.value})"


class TrackingEvent(Base):
    """Событие отслеживания отправления (one-to-many от Shipment)."""
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus, name="shipment_status"))
    location: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    shipment: Mapped[Shipment] = relationship(back_populates="events")
