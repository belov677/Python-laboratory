"""Складские операции — каждая в своём классе (OCP, SRP)."""
from __future__ import annotations

from dataclasses import dataclass

from interfaces.repository import StockRepository
from interfaces.services import StockOperation
from models.entities import InsufficientStockError, OperationResult
from models.enums import OperationType


def _check_positive(quantity: int) -> None:
    if quantity <= 0:
        raise ValueError("Количество должно быть положительным")


@dataclass
class Receipt(StockOperation):
    warehouse: str
    sku: str
    quantity: int

    def execute(self, repository: StockRepository) -> OperationResult:
        _check_positive(self.quantity)
        repository.get_product(self.sku)
        new_qty = repository.get_quantity(self.warehouse, self.sku) + self.quantity
        repository.set_quantity(self.warehouse, self.sku, new_qty)
        return OperationResult(OperationType.RECEIPT, self.sku,
                               f"+{self.quantity} на склад {self.warehouse}",
                               {self.warehouse: self.quantity})


@dataclass
class WriteOff(StockOperation):
    warehouse: str
    sku: str
    quantity: int
    reason: str = "списание"

    def execute(self, repository: StockRepository) -> OperationResult:
        _check_positive(self.quantity)
        current = repository.get_quantity(self.warehouse, self.sku)
        if current < self.quantity:
            raise InsufficientStockError(
                f"Нельзя списать {self.quantity} шт. {self.sku}: на складе {self.warehouse} {current}")
        repository.set_quantity(self.warehouse, self.sku, current - self.quantity)
        return OperationResult(OperationType.WRITE_OFF, self.sku,
                               f"-{self.quantity} со склада {self.warehouse} ({self.reason})",
                               {self.warehouse: -self.quantity})


@dataclass
class Transfer(StockOperation):
    source: str
    target: str
    sku: str
    quantity: int

    def execute(self, repository: StockRepository) -> OperationResult:
        _check_positive(self.quantity)
        if self.source == self.target:
            raise ValueError("Склад-источник и склад-получатель совпадают")
        current = repository.get_quantity(self.source, self.sku)
        if current < self.quantity:
            raise InsufficientStockError(
                f"Нельзя переместить {self.quantity} шт. {self.sku}: на складе {self.source} {current}")
        repository.set_quantity(self.source, self.sku, current - self.quantity)
        repository.set_quantity(self.target, self.sku,
                                repository.get_quantity(self.target, self.sku) + self.quantity)
        return OperationResult(OperationType.TRANSFER, self.sku,
                               f"{self.quantity} шт. {self.source} → {self.target}",
                               {self.source: -self.quantity, self.target: self.quantity})


@dataclass
class Inventory(StockOperation):
    """Инвентаризация: фиксирует фактический остаток и расхождение."""
    warehouse: str
    sku: str
    counted: int

    def execute(self, repository: StockRepository) -> OperationResult:
        if self.counted < 0:
            raise ValueError("Фактическое количество не может быть отрицательным")
        expected = repository.get_quantity(self.warehouse, self.sku)
        repository.set_quantity(self.warehouse, self.sku, self.counted)
        diff = self.counted - expected
        return OperationResult(OperationType.INVENTORY, self.sku,
                               f"учёт {expected}, факт {self.counted}, расхождение {diff:+}",
                               {self.warehouse: diff})


@dataclass
class ReturnToSupplier(WriteOff):
    """Новая операция добавлена без изменения StockService (демонстрация OCP)."""
    reason: str = "возврат поставщику"

    def execute(self, repository: StockRepository) -> OperationResult:
        result = super().execute(repository)
        result.operation = OperationType.RETURN
        return result
