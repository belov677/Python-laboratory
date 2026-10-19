"""Бизнес-логика: проверки, кэширование (cache-aside) и инвалидирование кэша."""
from __future__ import annotations

from cache import RedisCache
from exceptions import ValidationError
from repository import SORT_COLUMNS, ItemRepository
from schemas import validate_item, validate_movement


class ItemService:
    def __init__(self, repository: ItemRepository, cache: RedisCache) -> None:
        self.repository = repository
        self.cache = cache

    @staticmethod
    def item_key(item_id: int) -> str:
        return f"item:{item_id}"

    def _invalidate(self, item_id: int | None = None) -> None:
        keys = ["items:low-stock", "items:statistics"]
        if item_id is not None:
            keys.append(self.item_key(item_id))
        self.cache.delete(*keys)

    def get_items(self, sort: str = "id", order: str = "asc", **filters) -> list[dict]:
        if sort not in SORT_COLUMNS:
            raise ValidationError(f"Сортировка возможна по: {', '.join(SORT_COLUMNS)}")
        if order not in ("asc", "desc"):
            raise ValidationError("order должен быть asc или desc")
        return self.repository.get_all(sort=sort, order=order, **filters)

    def get_item(self, item_id: int) -> tuple[dict, str]:
        """Cache-aside: Redis → (промах) PostgreSQL → Redis."""
        self.cache.hit(item_id)
        cached = self.cache.get(self.item_key(item_id))
        if cached is not None:
            return cached, "HIT"
        item = self.repository.get_by_id(item_id)
        self.cache.set(self.item_key(item_id), item)
        return item, "MISS"

    def create_item(self, data: object) -> dict:
        item = self.repository.create(validate_item(data))
        self._invalidate()
        return item

    def replace_item(self, item_id: int, data: object) -> dict:
        item = self.repository.update(item_id, validate_item(data))
        self._invalidate(item_id)
        return item

    def patch_item(self, item_id: int, data: object) -> dict:
        item = self.repository.update(item_id, validate_item(data, partial=True))
        self._invalidate(item_id)
        return item

    def delete_item(self, item_id: int) -> None:
        self.repository.delete(item_id)
        self._invalidate(item_id)

    def receive(self, item_id: int, data: object) -> dict:
        quantity, supplier = validate_movement(data)
        item = self.repository.register_movement(item_id, "in", quantity, supplier)
        self._invalidate(item_id)
        return item

    def ship(self, item_id: int, data: object) -> dict:
        quantity, _ = validate_movement(data)
        item = self.repository.register_movement(item_id, "out", quantity)
        self._invalidate(item_id)
        return item

    def low_stock(self) -> list[dict]:
        cached = self.cache.get("items:low-stock")
        if cached is None:
            cached = self.repository.low_stock()
            self.cache.set("items:low-stock", cached, ttl=30)
        return cached

    def statistics(self) -> dict:
        stats = self.repository.statistics()
        stats["popular"] = [{"item_id": int(i), "requests": int(n)}
                            for i, n in self.cache.popular()]
        return stats
