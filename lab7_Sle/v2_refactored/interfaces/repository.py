"""Узкие интерфейсы хранилища (ISP): чтение, запись и каталог разделены."""
from __future__ import annotations

from typing import Protocol

from models.entities import Product


class StockReader(Protocol):
    def get_quantity(self, warehouse: str, sku: str) -> int: ...
    def all_stock(self) -> dict[tuple[str, str], int]: ...


class StockWriter(Protocol):
    def set_quantity(self, warehouse: str, sku: str, quantity: int) -> None: ...


class ProductCatalog(Protocol):
    def add_product(self, product: Product) -> None: ...
    def get_product(self, sku: str) -> Product: ...
    def list_products(self) -> list[Product]: ...


class StockRepository(StockReader, StockWriter, ProductCatalog, Protocol):
    """Полный репозиторий — объединение узких интерфейсов."""
