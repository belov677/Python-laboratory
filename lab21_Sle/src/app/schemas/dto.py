"""Схемы запросов и ответов API (валидация входных данных)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.entities import (
    DeliveryStatus,
    OrderStatus,
    Role,
    VehicleCategory,
    VehicleStatus,
)

CATEGORY_LIMIT_KG = {VehicleCategory.B: 3500, VehicleCategory.C: 20000, VehicleCategory.CE: 40000}


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- пользователи ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not (re.search(r"[A-Za-zА-Яа-я]", value) and re.search(r"\d", value)):
            raise ValueError("пароль должен содержать буквы и цифры")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — тип токена OAuth2, а не секрет
    role: Role


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: Role


# ---------- справочники ----------
class RouteIn(BaseModel):
    code: str = Field(pattern=r"^R-\d{3,5}$", examples=["R-101"])
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    distance_km: int = Field(gt=0, le=15000)
    duration_h: float = Field(gt=0, le=300)
    waypoints: list[str] = []

    @model_validator(mode="after")
    def different_points(self) -> RouteIn:
        if self.origin.strip().lower() == self.destination.strip().lower():
            raise ValueError("пункты отправления и назначения должны различаться")
        return self


class RouteOut(RouteIn, ORM):
    id: int


class VehicleIn(BaseModel):
    plate: str = Field(pattern=r"^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$", examples=["А123ВС77"])
    model: str = Field(min_length=2, max_length=80)
    category: VehicleCategory
    capacity_kg: int = Field(gt=0, le=40000)
    status: VehicleStatus = VehicleStatus.ACTIVE

    @model_validator(mode="after")
    def capacity_matches_category(self) -> VehicleIn:
        limit = CATEGORY_LIMIT_KG[self.category]
        if self.capacity_kg > limit:
            raise ValueError(f"для категории {self.category.value} грузоподъёмность не более {limit} кг")
        return self


class VehicleOut(VehicleIn, ORM):
    id: int


class DriverIn(BaseModel):
    full_name: str = Field(min_length=5, max_length=150)
    license_number: str = Field(pattern=r"^\d{2} \d{2} \d{6}$", examples=["77 12 345678"])
    license_categories: list[VehicleCategory] = Field(min_length=1)
    phone: str = Field(pattern=r"^\+7\d{10}$", examples=["+79161234567"])
    active: bool = True


class DriverOut(DriverIn, ORM):
    id: int


# ---------- заказы и доставки ----------
class OrderIn(BaseModel):
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    cargo: str = Field(min_length=3, max_length=200)
    weight_kg: int = Field(gt=0, le=40000)
    pickup_at: datetime
    deadline_at: datetime

    @model_validator(mode="after")
    def consistent(self) -> OrderIn:
        if self.origin.strip().lower() == self.destination.strip().lower():
            raise ValueError("пункты отправления и назначения должны различаться")
        if self.pickup_at.tzinfo is None or self.deadline_at.tzinfo is None:
            raise ValueError("даты указываются с часовым поясом, например 2026-11-01T09:00:00+03:00")
        if self.deadline_at <= self.pickup_at:
            raise ValueError("срок доставки должен быть позже времени подачи")
        return self


class OrderOut(ORM):
    id: int
    customer_id: int
    origin: str
    destination: str
    cargo: str
    weight_kg: int
    pickup_at: datetime
    deadline_at: datetime
    status: OrderStatus
    created_at: datetime


class DeliveryIn(BaseModel):
    order_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)
    driver_id: int = Field(gt=0)


class DeliveryOut(ORM):
    id: int
    order_id: int
    status: DeliveryStatus
    planned_start: datetime
    planned_end: datetime
    cost: float
    finished_at: datetime | None
    route: RouteOut
    vehicle: VehicleOut
    driver: DriverOut


class DeliveryAction(BaseModel):
    action: Literal["start", "complete", "cancel"]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int


class NotificationOut(ORM):
    id: int
    channel: str
    text: str
    created_at: datetime
