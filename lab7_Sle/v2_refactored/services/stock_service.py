"""Сервис складских операций. Не содержит input()/print() и не создаёт зависимости сам (DIP)."""
from __future__ import annotations

from interfaces.repository import StockRepository
from interfaces.services import Notifier, StockOperation
from models.entities import OperationResult, Product


class StockService:
    def __init__(self, repository: StockRepository, notifier: Notifier) -> None:
        self.repository = repository          # Constructor Injection
        self.notifier = notifier
        self.history: list[OperationResult] = []

    def register_product(self, product: Product) -> Product:
        self.repository.add_product(product)
        return product

    def execute(self, operation: StockOperation) -> OperationResult:
        """Выполнение любой операции через абстракцию StockOperation (OCP)."""
        result = operation.execute(self.repository)
        self.history.append(result)
        self.notifier.send(f"{result.operation.value}: {result.sku} — {result.details}")
        return result

    def total_quantity(self, sku: str) -> int:
        return sum(q for (_, s), q in self.repository.all_stock().items() if s == sku)
