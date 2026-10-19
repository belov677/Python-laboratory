"""Операции в виде объектов-команд (Command) с историей и отменой."""
from __future__ import annotations

from datetime import date
from typing import Protocol

from factories.entity_factory import StrategyFactory
from services.warehouse_service import WarehouseService


class Command(Protocol):
    def execute(self) -> str: ...
    def undo(self) -> str: ...


class ReceiveBatchCommand:
    def __init__(self, service: WarehouseService, sku: str, quantity: int, expiry: date,
                 priority: int = 0, supplier: str = "—") -> None:
        self.service, self.args = service, (sku, quantity, expiry, priority, supplier)
        self.batch = None

    def execute(self) -> str:
        self.batch = self.service.receive_batch(*self.args)
        return f"Принята партия #{self.batch.id}: {self.batch.sku} × {self.batch.quantity}"

    def undo(self) -> str:
        if self.batch.quantity != self.args[1]:
            raise ValueError("Партия уже частично отгружена — отмена поступления невозможна")
        self.service.remove_batch(self.batch.id)
        return f"Отменено поступление партии #{self.batch.id}"


class ShipCommand:
    def __init__(self, service: WarehouseService, sku: str, quantity: int) -> None:
        self.service, self.sku, self.quantity = service, sku, quantity
        self.taken: list[tuple[int, int]] = []

    def execute(self) -> str:
        self.taken = self.service.ship(self.sku, self.quantity)
        parts = ", ".join(f"партия #{b}: {q}" for b, q in self.taken)
        return f"Отгружено {self.sku} × {self.quantity} ({self.service.strategy.name}) — {parts}"

    def undo(self) -> str:
        self.service.restore(self.taken)
        return f"Отменена отгрузка {self.sku} × {self.quantity}, остатки партий восстановлены"


class ChangeStrategyCommand:
    def __init__(self, service: WarehouseService, name: str) -> None:
        self.service, self.name = service, name
        self.previous = None

    def execute(self) -> str:
        new_strategy = StrategyFactory.create(self.name)
        self.previous = self.service.strategy
        self.service.set_strategy(new_strategy)
        return f"Стратегия изменена: {self.previous.name} → {new_strategy.name}"

    def undo(self) -> str:
        self.service.set_strategy(self.previous)
        return f"Возвращена стратегия {self.previous.name}"


class CommandHistory:
    """Инвокер: выполняет команды и хранит историю для undo()."""

    def __init__(self) -> None:
        self._done: list[Command] = []

    def execute(self, command: Command) -> str:
        result = command.execute()
        self._done.append(command)
        return result

    def undo(self) -> str:
        if not self._done:
            return "История пуста — отменять нечего"
        command = self._done[-1]
        result = command.undo()
        self._done.pop()
        return result

    def names(self) -> list[str]:
        return [type(c).__name__ for c in self._done]
