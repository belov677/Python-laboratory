"""ORM-модели: клиент, отправление, груз, событие отслеживания."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Status(enum.Enum):
    CREATED = "создано"
    IN_TRANSIT = "в пути"
    DELIVERED = "доставлено"
    CANCELLED = "отменено"


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str] = mapped_column(String(100))
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="client",
                                                       order_by="Shipment.id")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email, "phone": self.phone,
                "city": self.city}


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (CheckConstraint("distance_km > 0", name="ck_distance"),
                      CheckConstraint("cost >= 0", name="ck_cost"))
    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(20), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"))
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    distance_km: Mapped[int]
    status: Mapped[Status] = mapped_column(Enum(Status, name="shipment_status_web"),
                                           default=Status.CREATED)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    client: Mapped[Client] = relationship(back_populates="shipments")
    cargos: Mapped[list["Cargo"]] = relationship(back_populates="shipment",
                                                 cascade="all, delete-orphan")
    events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="TrackingEvent.id")

    @property
    def weight(self) -> Decimal:
        return sum((c.weight_kg for c in self.cargos), Decimal(0))

    def to_dict(self) -> dict:
        return {"id": self.id, "tracking_number": self.tracking_number,
                "client": {"id": self.client.id, "name": self.client.name},
                "origin": self.origin, "destination": self.destination,
                "distance_km": self.distance_km, "status": self.status.name,
                "status_title": self.status.value, "cost": float(self.cost),
                "weight_kg": float(self.weight),
                "cargos": [{"description": c.description, "weight_kg": float(c.weight_kg),
                            "cargo_type": c.cargo_type} for c in self.cargos],
                "events": [{"status": e.status.name, "location": e.location,
                            "time": e.created_at.isoformat(timespec="minutes")} for e in self.events]}


class Cargo(Base):
    __tablename__ = "cargos"
    __table_args__ = (CheckConstraint("weight_kg > 0", name="ck_weight"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(String(200))
    cargo_type: Mapped[str] = mapped_column(String(30))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shipment: Mapped[Shipment] = relationship(back_populates="cargos")


class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    status: Mapped[Status] = mapped_column(Enum(Status, name="shipment_status_web"))
    location: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    shipment: Mapped[Shipment] = relationship(back_populates="events")
