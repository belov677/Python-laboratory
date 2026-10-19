"""Бизнес-логика складского учёта: поступление, списание, перемещение, поиск."""
from __future__ import annotations

import re
from datetime import datetime

from src.models.entities import Movement, MovementType, Product, Warehouse
from src.repositories.base import InventoryRepository
from src.services.exceptions import (DuplicateError, InsufficientStockError, NotFoundError,
                                     ValidationError)

MAX_QUANTITY = 10_000            # максимальное количество в одной операции
SKU_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3,6}$")


class InventoryService:
    def __init__(self, repository: InventoryRepository, notifier=None) -> None:
        self.repo = repository
        self.notifier = notifier

    # ---------- проверки ----------
    @staticmethod
    def validate_quantity(quantity) -> int:
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValidationError("Количество должно быть целым числом")
        if quantity < 1:
            raise ValidationError("Количество должно быть не меньше 1")
        if quantity > MAX_QUANTITY:
            raise ValidationError(f"Количество не может превышать {MAX_QUANTITY}")
        return quantity

    @staticmethod
    def validate_id(value, title: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError(f"Некорректный идентификатор {title}: {value!r}")
        return value

    def _product(self, product_id) -> Product:
        product = self.repo.get_product(self.validate_id(product_id, "товара"))
        if product is None:
            raise NotFoundError(f"Товар с id={product_id} не найден")
        return product

    def _warehouse(self, warehouse_id) -> Warehouse:
        warehouse = self.repo.get_warehouse(self.validate_id(warehouse_id, "склада"))
        if warehouse is None:
            raise NotFoundError(f"Склад с id={warehouse_id} не найден")
        return warehouse

    # ---------- справочники ----------
    def create_product(self, sku: str, name: str, unit: str = "шт", min_stock: int = 0) -> Product:
        sku = (sku or "").strip().upper()
        name = (name or "").strip()
        if not SKU_PATTERN.match(sku):
            raise ValidationError("Артикул должен иметь формат ABC-123")
        if not name:
            raise ValidationError("Название товара не может быть пустым")
        if isinstance(min_stock, bool) or not isinstance(min_stock, int) or min_stock < 0:
            raise ValidationError("Минимальный остаток — целое неотрицательное число")
        if self.repo.get_product_by_sku(sku) is not None:
            raise DuplicateError(f"Товар с артикулом {sku} уже существует")
        return self.repo.add_product(Product(sku, name, unit, min_stock))

    def create_warehouse(self, name: str, city: str) -> Warehouse:
        if not (name or "").strip() or not (city or "").strip():
            raise ValidationError("Название и город склада обязательны")
        return self.repo.add_warehouse(Warehouse(name.strip(), city.strip()))

    def get_product(self, product_id: int) -> Product:
        return self._product(product_id)

    def delete_product(self, product_id: int) -> None:
        product = self._product(product_id)
        if self.total_stock(product.id) > 0:
            raise InsufficientStockError("Нельзя удалить товар, пока на складах есть остаток")
        self.repo.delete_product(product.id)

    def search(self, text: str) -> list[Product]:
        query = (text or "").strip()
        if not query:
            raise ValidationError("Поисковый запрос не может быть пустым")
        return self.repo.search_products(query)

    # ---------- остатки ----------
    def balance(self, product_id: int, warehouse_id: int) -> int:
        self._product(product_id)
        self._warehouse(warehouse_id)
        return self.repo.get_balance(product_id, warehouse_id)

    def total_stock(self, product_id: int) -> int:
        return sum(self.repo.balances(product_id).values())

    def low_stock(self, product_ids: list[int]) -> list[Product]:
        """Товары из списка, суммарный остаток которых ниже минимального."""
        result = []
        for product_id in product_ids:
            product = self._product(product_id)
            if self.total_stock(product.id) < product.min_stock:
                result.append(product)
        return result

    # ---------- движения ----------
    def receive(self, product_id: int, warehouse_id: int, quantity: int, comment: str = "") -> int:
        """Поступление товара на склад. Возвращает новый остаток на складе."""
        quantity = self.validate_quantity(quantity)
        product = self._product(product_id)
        warehouse = self._warehouse(warehouse_id)
        with self.repo.transaction():
            new_balance = self.repo.get_balance(product.id, warehouse.id) + quantity
            self.repo.set_balance(product.id, warehouse.id, new_balance)
            self.repo.add_movement(Movement(MovementType.RECEIPT, product.id, quantity,
                                            target_id=warehouse.id, comment=comment,
                                            created_at=datetime.now()))
        return new_balance

    def write_off(self, product_id: int, warehouse_id: int, quantity: int, comment: str = "") -> int:
        """Списание товара. Остаток не может стать отрицательным."""
        quantity = self.validate_quantity(quantity)
        product = self._product(product_id)
        warehouse = self._warehouse(warehouse_id)
        current = self.repo.get_balance(product.id, warehouse.id)
        if quantity > current:
            raise InsufficientStockError(
                f"Недостаточно товара {product.sku} на складе «{warehouse.name}»: "
                f"остаток {current}, требуется {quantity}")
        with self.repo.transaction():
            self.repo.set_balance(product.id, warehouse.id, current - quantity)
            self.repo.add_movement(Movement(MovementType.WRITE_OFF, product.id, quantity,
                                            source_id=warehouse.id, comment=comment,
                                            created_at=datetime.now()))
        self._check_low_stock(product)
        return current - quantity

    def transfer(self, product_id: int, source_id: int, target_id: int, quantity: int) -> tuple[int, int]:
        """Перемещение между складами. Возвращает новые остатки (источник, получатель)."""
        quantity = self.validate_quantity(quantity)
        if source_id == target_id:
            raise ValidationError("Склад-источник и склад-получатель должны различаться")
        product = self._product(product_id)
        source = self._warehouse(source_id)
        target = self._warehouse(target_id)
        available = self.repo.get_balance(product.id, source.id)
        if quantity > available:
            raise InsufficientStockError(
                f"Недостаточно товара на складе «{source.name}» для перемещения: "
                f"остаток {available}, требуется {quantity}")
        with self.repo.transaction():
            target_balance = self.repo.get_balance(product.id, target.id) + quantity
            self.repo.set_balance(product.id, source.id, available - quantity)
            self.repo.set_balance(product.id, target.id, target_balance)
            self.repo.add_movement(Movement(MovementType.TRANSFER, product.id, quantity,
                                            source_id=source.id, target_id=target.id,
                                            created_at=datetime.now()))
        return available - quantity, target_balance

    def history(self, product_id: int) -> list[Movement]:
        return self.repo.movements(self._product(product_id).id)

    def _check_low_stock(self, product: Product) -> None:
        total = self.total_stock(product.id)
        if self.notifier is not None and total < product.min_stock:
            self.notifier.notify_low_stock(product, total)
