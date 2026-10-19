"""Бизнес-логика склада: MongoDB — основное хранилище, Redis — быстрый доступ."""
from __future__ import annotations

import time
from datetime import date, datetime

from cache import RedisCache
from exceptions import ValidationError
from models import Batch, WarehouseItem
from repository import MongoRepository


class WarehouseService:
    def __init__(self, repository: MongoRepository, cache: RedisCache) -> None:
        self.repo = repository
        self.cache = cache

    def _sync(self, item: WarehouseItem) -> None:
        self.cache.invalidate(item.sku)                        # инвалидирование
        self.cache.set_stock(item.sku, item.quantity, item.status != "in_stock")

    # ---------- CRUD ----------
    def add_item(self, item: WarehouseItem) -> WarehouseItem:
        item = self.repo.add(item)
        self._sync(item)
        self.cache.publish("item.created", item.sku)
        return item

    def get_item(self, sku: str) -> tuple[dict, str]:
        """Cache-aside с защитой от cache stampede. Возвращает (данные, источник)."""
        self.cache.hit(sku)
        cached = self.cache.get_item(sku)
        if cached is not None:
            return cached, "Redis"
        with self.cache.lock(sku):
            cached = self.cache.get_item(sku)          # другой процесс мог уже загрузить
            if cached is not None:
                return cached, "Redis"
            data = self.repo.get_by_sku(sku).to_public()
            self.cache.set_item(sku, data)
            return data, "MongoDB"

    def list_items(self) -> list[WarehouseItem]:
        return self.repo.list()

    def update_item(self, sku: str, price: float | None = None, min_stock: int | None = None,
                    location: dict | None = None) -> WarehouseItem:
        fields = {}
        if price is not None:
            if price <= 0:
                raise ValidationError("Цена должна быть положительной")
            fields["price"] = price
        if min_stock is not None:
            if min_stock < 0:
                raise ValidationError("Минимальный остаток не может быть отрицательным")
            fields["min_stock"] = min_stock
        if location:
            fields["location"] = location
        if not fields:
            raise ValidationError("Нет данных для изменения")
        item = self.repo.update_fields(sku, fields)
        item = self.repo.replace(item)                 # пересчёт статуса
        self._sync(item)
        self.cache.publish("item.updated", sku)
        return item

    def receive_batch(self, sku: str, batch_no: str, quantity: int,
                      expiry: date | None) -> WarehouseItem:
        if quantity <= 0:
            raise ValidationError("Количество в партии должно быть положительным")
        item = self.repo.get_by_sku(sku)
        item.batches.append(Batch(batch_no, quantity, date.today(), expiry))
        item = self.repo.replace(item)
        self._sync(item)
        self.cache.publish("item.updated", sku)
        return item

    def write_off(self, sku: str, quantity: int) -> WarehouseItem:
        """Списание по FEFO: сначала партии с ближайшим сроком годности."""
        item = self.repo.get_by_sku(sku)
        if quantity <= 0 or quantity > item.quantity:
            raise ValidationError(f"Нельзя списать {quantity} шт.: в наличии {item.quantity}")
        for batch in sorted(item.batches, key=lambda b: b.expiry_date or date.max):
            take = min(batch.quantity, quantity)
            batch.quantity -= take
            quantity -= take
        item = self.repo.replace(item)
        self._sync(item)
        self.cache.publish("item.updated", sku)
        return item

    def delete_item(self, sku: str) -> None:
        self.repo.delete(sku)
        self.cache.invalidate(sku)
        self.cache.remove_stock(sku)
        self.cache.publish("item.deleted", sku)

    def stock_of(self, sku: str) -> tuple[int, str]:
        """Быстрый остаток по артикулу из Redis Hash, при отсутствии — из MongoDB."""
        value = self.cache.stock(sku)
        if value is not None:
            return value, "Redis"
        item = self.repo.get_by_sku(sku)
        self.cache.set_stock(sku, item.quantity, item.status != "in_stock")
        return item.quantity, "MongoDB"

    def search(self, kind: str, value: str) -> list[WarehouseItem]:
        self.cache.remember_search(f"{kind}:{value}")
        if kind == "category":
            return self.repo.by_category(value)
        if kind == "city":
            return self.repo.by_supplier_city(value)
        if kind == "tag":
            return self.repo.by_tag(value)
        if kind == "name":
            return self.repo.search_name(value)
        if kind == "expiring":
            return self.repo.expiring_before(datetime.fromisoformat(value))
        if kind == "price":
            low, high = (float(x) for x in value.split("-"))
            return self.repo.price_between(low, high)
        if kind == "low":
            return self.repo.low_stock()
        raise ValidationError(f"Неизвестный тип поиска: {kind}")

    def statistics(self) -> dict:
        return {"total": self.repo.count(), "by_category": self.repo.stats_by_category(),
                "by_supplier": self.repo.stats_by_supplier(),
                "expiring_by_month": self.repo.expiring_by_month(),
                "top_by_value": self.repo.top_by_value(3),
                "popular": self.cache.popular()}

    def warm_up(self) -> int:
        for item in self.repo.list(1000):
            self.cache.set_stock(item.sku, item.quantity, item.status != "in_stock")
        return len(self.cache.all_stock())

    def benchmark(self, sku: str, counts=(100, 1000, 10000)) -> list[tuple[int, float, float]]:
        self.get_item(sku)
        rows = []
        for n in counts:
            start = time.perf_counter()
            for _ in range(n):
                self.repo.get_by_sku(sku).to_public()
            mongo = time.perf_counter() - start
            start = time.perf_counter()
            for _ in range(n):
                self.cache.get_item(sku)
            rows.append((n, mongo, time.perf_counter() - start))
        return rows
