"""Модель документа warehouse_item."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime

from exceptions import ValidationError


@dataclass
class Batch:
    batch_no: str
    quantity: int
    received: date
    expiry_date: date | None = None


@dataclass
class WarehouseItem:
    sku: str
    name: str
    category: str
    price: float
    min_stock: int
    supplier: dict                     # вложенный объект: name, city, contact{phone,email}
    location: dict                     # вложенный объект: zone, rack, shelf
    batches: list[Batch] = field(default_factory=list)   # массив партий
    tags: list[str] = field(default_factory=list)        # массив тегов
    id: str | None = None

    def __post_init__(self) -> None:
        if not self.sku or not self.name or not self.category:
            raise ValidationError("sku, name и category обязательны")
        if self.price <= 0:
            raise ValidationError("Цена должна быть положительной")
        if self.min_stock < 0:
            raise ValidationError("Минимальный остаток не может быть отрицательным")
        if not {"name", "city"} <= set(self.supplier):
            raise ValidationError("У поставщика должны быть name и city")
        for b in self.batches:
            if b.quantity < 0:
                raise ValidationError("Количество в партии не может быть отрицательным")

    @property
    def quantity(self) -> int:
        return sum(b.quantity for b in self.batches)

    @property
    def status(self) -> str:
        if self.quantity == 0:
            return "out_of_stock"
        return "low" if self.quantity < self.min_stock else "in_stock"

    @property
    def nearest_expiry(self) -> date | None:
        dates = [b.expiry_date for b in self.batches if b.expiry_date and b.quantity > 0]
        return min(dates) if dates else None

    def to_document(self) -> dict:
        doc = asdict(self)
        doc.pop("id")
        for b in doc["batches"]:                       # MongoDB хранит datetime, не date
            b["received"] = datetime.combine(b["received"], datetime.min.time())
            if b["expiry_date"]:
                b["expiry_date"] = datetime.combine(b["expiry_date"], datetime.min.time())
        expiry = self.nearest_expiry
        doc.update(quantity=self.quantity, status=self.status,
                   expiry_date=datetime.combine(expiry, datetime.min.time()) if expiry else None)
        return doc

    @classmethod
    def from_document(cls, doc: dict) -> "WarehouseItem":
        batches = [Batch(b["batch_no"], b["quantity"], b["received"].date(),
                         b["expiry_date"].date() if b.get("expiry_date") else None)
                   for b in doc.get("batches", [])]
        return cls(sku=doc["sku"], name=doc["name"], category=doc["category"],
                   price=doc["price"], min_stock=doc["min_stock"], supplier=doc["supplier"],
                   location=doc["location"], batches=batches, tags=doc.get("tags", []),
                   id=str(doc["_id"]))

    def to_public(self) -> dict:
        """Представление для вывода и кэша (JSON-совместимое)."""
        data = asdict(self)
        for b in data["batches"]:
            b["received"] = b["received"].isoformat()
            b["expiry_date"] = b["expiry_date"].isoformat() if b["expiry_date"] else None
        data.update(quantity=self.quantity, status=self.status)
        return data
