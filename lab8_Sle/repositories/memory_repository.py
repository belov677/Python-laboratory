from __future__ import annotations

from typing import Any

from models.entities import EntityNotFoundError


class InMemoryRepository:
    def __init__(self) -> None:
        self._items: dict[int, Any] = {}

    def add(self, entity: Any) -> Any:
        self._items[entity.id] = entity
        return entity

    def get(self, entity_id: int) -> Any:
        try:
            return self._items[entity_id]
        except KeyError:
            raise EntityNotFoundError(f"Объект id={entity_id} не найден") from None

    def get_all(self) -> list[Any]:
        return list(self._items.values())

    def delete(self, entity_id: int) -> None:
        self.get(entity_id)
        del self._items[entity_id]

    def next_id(self) -> int:
        return max(self._items, default=0) + 1

    def save(self) -> None:
        """В памяти сохранять нечего."""
