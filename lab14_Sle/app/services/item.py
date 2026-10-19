"""Бизнес-логика товаров: проверки, кэш, транзакции."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from cache import ItemCache
from exceptions import ConflictError, NotFoundError
from models.item import Item
from repositories.item import ItemRepository
from schemas.item import ItemCreate, ItemReplace, ItemResponse, ItemUpdate


class ItemService:
    def __init__(self, session: Session, cache: ItemCache) -> None:
        self.session = session
        self.repo = ItemRepository(session)
        self.cache = cache

    def _get_or_404(self, item_id: int) -> Item:
        item = self.repo.get(item_id)
        if item is None:
            raise NotFoundError(f"Item with id {item_id} not found")
        return item

    def list(self, **params) -> tuple[list[Item], int]:
        return self.repo.list(**params)

    def search(self, query: str) -> list[Item]:
        return self.repo.search(query)

    def get(self, item_id: int) -> tuple[dict, str]:
        """Cache-aside: Redis → (MISS) PostgreSQL → Redis."""
        cached = self.cache.get(item_id)
        if cached is not None:
            return cached, "HIT"
        data = ItemResponse.model_validate(self._get_or_404(item_id)).model_dump(mode="json")
        self.cache.set(item_id, data)
        return data, "MISS"

    def create(self, data: ItemCreate) -> Item:
        if self.repo.get_by_sku(data.sku):
            raise ConflictError(f"Item with sku {data.sku} already exists")
        item = self.repo.add(Item(**data.model_dump()))
        self.session.commit()
        return item

    def replace(self, item_id: int, data: ItemReplace) -> Item:
        item = self._get_or_404(item_id)
        other = self.repo.get_by_sku(data.sku)
        if other is not None and other.id != item_id:
            raise ConflictError(f"Item with sku {data.sku} already exists")
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        self.session.commit()
        self.cache.invalidate(item_id)
        return item

    def update(self, item_id: int, data: ItemUpdate) -> Item:
        item = self._get_or_404(item_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.session.commit()
        self.cache.invalidate(item_id)
        return item

    def delete(self, item_id: int) -> None:
        self.repo.delete(self._get_or_404(item_id))
        self.session.commit()
        self.cache.invalidate(item_id)

    def statistics(self) -> dict:
        return self.repo.statistics(date.today())
