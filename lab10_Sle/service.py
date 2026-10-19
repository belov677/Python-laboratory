from __future__ import annotations

from dataclasses import replace

from exceptions import ConflictError, ItemNotFoundError, ValidationError
from models import Item
from repository import ItemRepository
from schemas import validate_item

SORT_FIELDS = {"id", "name", "quantity", "price", "category"}


class ItemService:
    def __init__(self, repository: ItemRepository) -> None:
        self.repository = repository

    def get_items(self, category: str | None = None, location: str | None = None,
                  min_quantity: int | None = None, max_quantity: int | None = None,
                  search: str | None = None, sort: str = "id", order: str = "asc") -> list[Item]:
        if sort not in SORT_FIELDS:
            raise ValidationError(f"Сортировка возможна по полям: {', '.join(sorted(SORT_FIELDS))}")
        if order not in ("asc", "desc"):
            raise ValidationError("order должен быть asc или desc")
        items = self.repository.get_all()
        if category:
            items = [i for i in items if i.category.lower() == category.lower()]
        if location:
            items = [i for i in items if i.location.lower().startswith(location.lower())]
        if min_quantity is not None:
            items = [i for i in items if i.quantity >= min_quantity]
        if max_quantity is not None:
            items = [i for i in items if i.quantity <= max_quantity]
        if search:
            items = [i for i in items if search.lower() in i.name.lower()
                     or search.lower() in i.sku.lower()]
        return sorted(items, key=lambda i: getattr(i, sort), reverse=order == "desc")

    def get_item(self, item_id: int) -> Item:
        item = self.repository.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError(f"Item with id {item_id} not found")
        return item

    def create_item(self, data: object) -> Item:
        clean = validate_item(data)
        self._check_unique_sku(clean["sku"])
        return self.repository.create(clean)

    def replace_item(self, item_id: int, data: object) -> Item:
        item = self.get_item(item_id)
        clean = validate_item(data)
        self._check_unique_sku(clean["sku"], exclude_id=item_id)
        return self.repository.update(Item(id=item.id, **clean))

    def patch_item(self, item_id: int, data: object) -> Item:
        item = self.get_item(item_id)
        clean = validate_item(data, partial=True)
        if "sku" in clean:
            self._check_unique_sku(clean["sku"], exclude_id=item_id)
        return self.repository.update(replace(item, **clean))

    def delete_item(self, item_id: int) -> None:
        if not self.repository.delete(item_id):
            raise ItemNotFoundError(f"Item with id {item_id} not found")

    def low_stock(self) -> list[Item]:
        """Специализированная операция: товары ниже минимального остатка."""
        return sorted((i for i in self.repository.get_all() if i.below_min),
                      key=lambda i: i.quantity - i.min_stock)

    def statistics(self) -> dict:
        items = self.repository.get_all()
        return {"items": len(items), "units": sum(i.quantity for i in items),
                "stock_value": round(sum(i.quantity * i.price for i in items), 2),
                "below_min": len(self.low_stock())}

    def _check_unique_sku(self, sku: str, exclude_id: int | None = None) -> None:
        if any(i.sku == sku and i.id != exclude_id for i in self.repository.get_all()):
            raise ConflictError(f"Товар с артикулом {sku} уже существует")
