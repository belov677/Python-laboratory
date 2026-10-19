from __future__ import annotations

from models.entities import Product, ProductNotFoundError


class InMemoryStockRepository:
    """Хранение остатков и каталога в памяти процесса."""

    def __init__(self) -> None:
        self._stock: dict[tuple[str, str], int] = {}
        self._products: dict[str, Product] = {}

    def get_quantity(self, warehouse: str, sku: str) -> int:
        return self._stock.get((warehouse, sku), 0)

    def set_quantity(self, warehouse: str, sku: str, quantity: int) -> None:
        if quantity < 0:
            raise ValueError("Остаток не может быть отрицательным")
        self._stock[(warehouse, sku)] = quantity

    def all_stock(self) -> dict[tuple[str, str], int]:
        return dict(self._stock)

    def add_product(self, product: Product) -> None:
        self._products[product.sku] = product

    def get_product(self, sku: str) -> Product:
        try:
            return self._products[sku]
        except KeyError:
            raise ProductNotFoundError(f"Товар {sku} отсутствует в каталоге") from None

    def list_products(self) -> list[Product]:
        return list(self._products.values())
