"""Формирование отчётов. Зависит только от интерфейсов чтения (ISP)."""
from __future__ import annotations

from datetime import date

from interfaces.repository import ProductCatalog, StockReader
from models.entities import PerishableProduct


class ReportGenerator:
    def __init__(self, reader: StockReader, catalog: ProductCatalog) -> None:
        self.reader = reader
        self.catalog = catalog

    def stock_lines(self) -> list[str]:
        lines = []
        for (warehouse, sku), qty in sorted(self.reader.all_stock().items()):
            product = self.catalog.get_product(sku)
            lines.append(f"{warehouse:12} {sku:7} {product.name:18} {qty:6} шт. "
                         f"{qty * product.price:12,.2f} руб.")
        return lines

    def total_value(self) -> float:
        return sum(qty * self.catalog.get_product(sku).price
                   for (_, sku), qty in self.reader.all_stock().items())

    def expiring(self, today: date, days: int) -> list[str]:
        """Только скоропортящиеся товары имеют срок годности — без NotImplementedError."""
        result = []
        for product in self.catalog.list_products():
            if isinstance(product, PerishableProduct):
                left = product.days_to_expire(today)
                if left <= days:
                    result.append(f"{product.sku} {product.name}: осталось {left} дн.")
        return result
