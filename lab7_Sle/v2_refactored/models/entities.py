"""Сущности предметной области «Склад»."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from models.enums import OperationType


@dataclass(frozen=True)
class Product:
    """Базовая сущность — любой товар. Не содержит понятия срока годности."""
    sku: str
    name: str
    price: float

    def __post_init__(self) -> None:
        if not self.sku or self.price <= 0:
            raise ValueError("Артикул обязателен, цена должна быть положительной")


@dataclass(frozen=True)
class PerishableProduct(Product):
    """Скоропортящийся товар — расширяет базовый класс, не ломая его контракт (LSP)."""
    expiry_date: date = date.max

    def days_to_expire(self, today: date) -> int:
        return (self.expiry_date - today).days


@dataclass(frozen=True)
class Warehouse:
    code: str
    name: str


@dataclass
class OperationResult:
    operation: OperationType
    sku: str
    details: str
    changes: dict[str, int] = field(default_factory=dict)   # склад -> изменение количества
    created_at: datetime = field(default_factory=datetime.now)


class StockError(Exception):
    """Базовая ошибка складских операций."""


class InsufficientStockError(StockError):
    pass


class ProductNotFoundError(StockError):
    pass
