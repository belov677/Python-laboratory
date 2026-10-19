"""Модели предметной области «Склад»."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MovementType(str, Enum):
    RECEIPT = "receipt"        # поступление
    WRITE_OFF = "write_off"    # списание
    TRANSFER = "transfer"      # перемещение между складами


@dataclass
class Product:
    sku: str
    name: str
    unit: str = "шт"
    min_stock: int = 0
    id: int | None = None


@dataclass
class Warehouse:
    name: str
    city: str
    id: int | None = None


@dataclass
class Movement:
    type: MovementType
    product_id: int
    quantity: int
    source_id: int | None = None       # склад-источник (списание, перемещение)
    target_id: int | None = None       # склад-получатель (поступление, перемещение)
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    id: int | None = None
