from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from models.enums import SupplyStatus


@dataclass
class Product:
    id: int
    sku: str
    name: str
    price: float


@dataclass
class Batch:
    """Партия товара: одна поставка одного товара с общим сроком годности."""
    id: int
    sku: str
    quantity: int
    received_order: int          # порядковый номер поступления (для FIFO)
    expiry_date: date
    priority: int = 0            # 0 — обычная, больше — важнее

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("Количество в партии не может быть отрицательным")


@dataclass
class Supply:
    id: int
    supplier: str
    batch_ids: list[int] = field(default_factory=list)
    status: SupplyStatus = SupplyStatus.EXPECTED


class WarehouseError(Exception):
    pass


class EntityNotFoundError(WarehouseError):
    pass


class InsufficientStockError(WarehouseError):
    pass
