from __future__ import annotations

from models import Item


class ItemRepository:
    """Хранение товаров в памяти (база данных появится в лабораторной №11)."""

    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._next_id = 1

    def get_all(self) -> list[Item]:
        return list(self._items.values())

    def get_by_id(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def create(self, data: dict) -> Item:
        item = Item(id=self._next_id, **data)
        self._items[item.id] = item
        self._next_id += 1
        return item

    def update(self, item: Item) -> Item:
        self._items[item.id] = item
        return item

    def delete(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None
