"""Модели предметной области «Склад»: товар, склад, поставка."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DeliveryStatus(Enum):
    EXPECTED = "ожидается"
    ACCEPTED = "принята"
    PLACED = "размещена"
    CANCELLED = "отменена"


# допустимые переходы статуса поставки
TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.EXPECTED: {DeliveryStatus.ACCEPTED, DeliveryStatus.CANCELLED},
    DeliveryStatus.ACCEPTED: {DeliveryStatus.PLACED, DeliveryStatus.CANCELLED},
    DeliveryStatus.PLACED: set(),
    DeliveryStatus.CANCELLED: set(),
}


@dataclass
class Entity:
    id: int
    name: str

    def short(self) -> str:
        return f"#{self.id} {self.name}"


@dataclass
class Product(Entity):
    sku: str
    price: float
    quantity: int = 0
    min_stock: int = 5
    warehouse_id: int | None = None

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("Цена товара должна быть положительной")
        if self.quantity < 0 or self.min_stock < 0:
            raise ValueError("Количество и минимальный остаток не могут быть отрицательными")

    def stock_value(self) -> float:
        return round(self.price * self.quantity, 2)

    def is_low(self) -> bool:
        return self.quantity <= self.min_stock

    def get_report_data(self) -> str:
        mark = " ⚠ мало" if self.is_low() else ""
        return (f"Товар {self.sku} «{self.name}»: {self.quantity} шт. × {self.price:.2f} = "
                f"{self.stock_value():.2f} руб.{mark}")


@dataclass
class Warehouse(Entity):
    address: str
    capacity: int
    product_ids: list[int] = field(default_factory=list)

    def get_report_data(self) -> str:
        return (f"Склад «{self.name}» ({self.address}), вместимость {self.capacity} шт., "
                f"позиций: {len(self.product_ids)}")


@dataclass
class Delivery(Entity):
    product_id: int
    quantity: int
    supplier: str
    status: DeliveryStatus = DeliveryStatus.EXPECTED

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Количество в поставке должно быть положительным")

    def can_change_to(self, new_status: DeliveryStatus) -> bool:
        return new_status in TRANSITIONS[self.status]

    def get_report_data(self) -> str:
        return (f"Поставка {self.name} от «{self.supplier}»: товар #{self.product_id}, "
                f"{self.quantity} шт., статус — {self.status.value}")
