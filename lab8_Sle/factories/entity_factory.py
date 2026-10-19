"""Фабрики: создание сущностей и стратегий в одном месте (Factory)."""
from __future__ import annotations

from datetime import date
from typing import Any

from models.entities import Batch, Product, Supply
from models.enums import SupplyStatus
from strategies.picking import ExpiryStrategy, FifoStrategy, PriorityStrategy


class EntityFactory:
    _types = {"product": Product, "batch": Batch, "supply": Supply}

    @classmethod
    def create(cls, kind: str, **data: Any):
        try:
            entity_class = cls._types[kind]
        except KeyError:
            raise ValueError(f"Неизвестный тип объекта: {kind}") from None
        if kind == "batch" and isinstance(data.get("expiry_date"), str):
            data["expiry_date"] = date.fromisoformat(data["expiry_date"])
        if kind == "supply" and isinstance(data.get("status"), str):
            data["status"] = SupplyStatus[data["status"]]
        return entity_class(**data)

    @classmethod
    def kind_of(cls, entity: Any) -> str:
        for kind, entity_class in cls._types.items():
            if type(entity) is entity_class:
                return kind
        raise ValueError(f"Неизвестный класс {type(entity).__name__}")


class StrategyFactory:
    """Factory + Strategy: стратегия создаётся по имени."""
    _strategies = {"fifo": FifoStrategy, "priority": PriorityStrategy, "expiry": ExpiryStrategy}

    @classmethod
    def create(cls, name: str):
        try:
            return cls._strategies[name]()
        except KeyError:
            raise ValueError(f"Неизвестная стратегия: {name}. "
                             f"Доступны: {', '.join(cls._strategies)}") from None

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._strategies)
