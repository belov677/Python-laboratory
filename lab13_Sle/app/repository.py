"""MongoRepository: CRUD, запросы, агрегация и индексы коллекции warehouse_item."""
from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from exceptions import ItemNotFoundError, ValidationError
from models import WarehouseItem


class MongoRepository:
    def __init__(self, db, collection: str = "warehouse_item") -> None:
        self.collection = db[collection]

    # ---------- индексы ----------
    def create_indexes(self) -> list[str]:
        return [
            self.collection.create_index("sku", unique=True, name="ux_sku"),
            self.collection.create_index([("category", ASCENDING), ("price", DESCENDING)],
                                         name="ix_category_price"),
            self.collection.create_index("supplier.city", name="ix_supplier_city"),
            self.collection.create_index("batches.expiry_date", name="ix_batch_expiry"),
        ]

    # ---------- CRUD ----------
    def add(self, item: WarehouseItem) -> WarehouseItem:
        try:
            result = self.collection.insert_one(item.to_document())
        except DuplicateKeyError:
            raise ValidationError(f"Товар с артикулом {item.sku} уже существует") from None
        item.id = str(result.inserted_id)
        return item

    def get_by_sku(self, sku: str) -> WarehouseItem:
        doc = self.collection.find_one({"sku": sku})
        if doc is None:
            raise ItemNotFoundError(f"Товар {sku} не найден")
        return WarehouseItem.from_document(doc)

    def get_by_id(self, item_id: str) -> WarehouseItem:
        if not isinstance(item_id, str):             # ObjectId(None) создал бы новый id
            raise ValidationError(f"Некорректный идентификатор: {item_id}")
        try:
            oid = ObjectId(item_id)
        except (InvalidId, TypeError):
            raise ValidationError(f"Некорректный идентификатор: {item_id}") from None
        doc = self.collection.find_one({"_id": oid})
        if doc is None:
            raise ItemNotFoundError(f"Товар с _id={item_id} не найден")
        return WarehouseItem.from_document(doc)

    def list(self, limit: int = 100) -> list[WarehouseItem]:
        return [WarehouseItem.from_document(d) for d in self.collection.find().sort("sku").limit(limit)]

    def replace(self, item: WarehouseItem) -> WarehouseItem:
        doc = self.collection.find_one_and_replace({"sku": item.sku}, item.to_document(),
                                                   return_document=ReturnDocument.AFTER)
        if doc is None:
            raise ItemNotFoundError(f"Товар {item.sku} не найден")
        return WarehouseItem.from_document(doc)

    def update_fields(self, sku: str, fields: dict) -> WarehouseItem:
        doc = self.collection.find_one_and_update({"sku": sku}, {"$set": fields},
                                                  return_document=ReturnDocument.AFTER)
        if doc is None:
            raise ItemNotFoundError(f"Товар {sku} не найден")
        return WarehouseItem.from_document(doc)

    def delete(self, sku: str) -> None:
        if self.collection.delete_one({"sku": sku}).deleted_count == 0:
            raise ItemNotFoundError(f"Товар {sku} не найден")

    def count(self) -> int:
        return self.collection.count_documents({})

    # ---------- запросы ----------
    def _find(self, query: dict, sort=None, limit: int = 0) -> list[WarehouseItem]:
        cursor = self.collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return [WarehouseItem.from_document(d) for d in cursor]

    def by_category(self, category: str) -> list[WarehouseItem]:              # фильтр 1
        return self._find({"category": category}, [("price", DESCENDING)])

    def low_stock(self) -> list[WarehouseItem]:                               # фильтр 2
        return self._find({"$expr": {"$lt": ["$quantity", "$min_stock"]}}, [("quantity", ASCENDING)])

    def price_between(self, low: float, high: float) -> list[WarehouseItem]:  # фильтр 3
        return self._find({"price": {"$gte": low, "$lte": high}}, [("price", ASCENDING)])

    def sorted_by_price(self, descending: bool = True) -> list[WarehouseItem]:  # сортировка 1
        return self._find({}, [("price", DESCENDING if descending else ASCENDING)])

    def expiring_before(self, day: datetime) -> list[WarehouseItem]:          # сортировка 2
        return self._find({"expiry_date": {"$ne": None, "$lte": day}}, [("expiry_date", ASCENDING)])

    def top_expensive(self, n: int = 5) -> list[WarehouseItem]:               # limit
        return self._find({}, [("price", DESCENDING)], limit=n)

    def by_supplier_city(self, city: str) -> list[WarehouseItem]:             # вложенное поле
        return self._find({"supplier.city": city}, [("sku", ASCENDING)])

    def by_tag(self, tag: str) -> list[WarehouseItem]:                        # элемент массива
        return self._find({"tags": tag}, [("sku", ASCENDING)])

    def with_expiring_batch(self, day: datetime, min_qty: int = 1) -> list[WarehouseItem]:
        """$elemMatch: есть партия с остатком, срок которой истекает до даты."""
        return self._find({"batches": {"$elemMatch": {"expiry_date": {"$lte": day},
                                                      "quantity": {"$gte": min_qty}}}})

    def search_name(self, text: str) -> list[WarehouseItem]:
        return self._find({"name": {"$regex": text, "$options": "i"}}, [("name", ASCENDING)])

    # ---------- агрегация ----------
    def stats_by_category(self) -> list[dict]:
        return list(self.collection.aggregate([
            {"$group": {"_id": "$category", "items": {"$sum": 1}, "units": {"$sum": "$quantity"},
                        "value": {"$sum": {"$multiply": ["$quantity", "$price"]}},
                        "avg_price": {"$avg": "$price"}}},
            {"$sort": {"value": -1}}]))

    def stats_by_supplier(self) -> list[dict]:
        return list(self.collection.aggregate([
            {"$group": {"_id": "$supplier.name", "city": {"$first": "$supplier.city"},
                        "items": {"$sum": 1}, "low": {"$sum": {"$cond": [
                            {"$lt": ["$quantity", "$min_stock"]}, 1, 0]}}}},
            {"$sort": {"items": -1, "_id": 1}}]))

    def expiring_by_month(self) -> list[dict]:
        """$unwind партий → $match с датой → группировка по месяцу истечения срока."""
        return list(self.collection.aggregate([
            {"$unwind": "$batches"},
            {"$match": {"batches.expiry_date": {"$ne": None}, "batches.quantity": {"$gt": 0}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$batches.expiry_date"}},
                        "batches": {"$sum": 1}, "units": {"$sum": "$batches.quantity"}}},
            {"$sort": {"_id": 1}}]))

    def top_by_value(self, n: int = 5) -> list[dict]:
        return list(self.collection.aggregate([
            {"$project": {"_id": 0, "sku": 1, "name": 1,
                          "value": {"$multiply": ["$quantity", "$price"]}}},
            {"$sort": {"value": -1}}, {"$limit": n}]))

    def explain(self, query: dict) -> dict:
        stats = self.collection.find(query).explain()["executionStats"]
        plan = self.collection.find(query).explain()["queryPlanner"]["winningPlan"]
        stage = plan.get("inputStage", plan).get("stage", plan.get("stage"))
        return {"stage": stage, "returned": stats["nReturned"],
                "docs_examined": stats["totalDocsExamined"],
                "keys_examined": stats["totalKeysExamined"],
                "time_ms": stats["executionTimeMillis"]}
