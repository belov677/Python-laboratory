"""Абстракции бизнес-логики."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from interfaces.repository import StockRepository
from models.entities import OperationResult


class Notifier(Protocol):
    def send(self, message: str) -> None: ...


class StockOperation(ABC):
    """Складская операция. Новая операция = новый подкласс (OCP)."""

    @abstractmethod
    def execute(self, repository: StockRepository) -> OperationResult:
        ...
