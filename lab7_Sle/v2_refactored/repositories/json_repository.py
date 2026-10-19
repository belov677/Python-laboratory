from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from models.entities import PerishableProduct, Product
from repositories.memory_repository import InMemoryStockRepository


class JsonFileStockRepository(InMemoryStockRepository):
    """Хранение в JSON-файле: данные загружаются при создании и сохраняются при изменении.

    Полностью заменяет InMemoryStockRepository — клиентский код не меняется (LSP).
    """

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for item in data["products"]:
            if "expiry_date" in item:
                item["expiry_date"] = date.fromisoformat(item["expiry_date"])
                super().add_product(PerishableProduct(**item))
            else:
                super().add_product(Product(**item))
        for key, qty in data["stock"].items():
            warehouse, sku = key.split("|")
            super().set_quantity(warehouse, sku, qty)

    def _save(self) -> None:
        products = []
        for p in self.list_products():
            item = asdict(p)
            if "expiry_date" in item:
                item["expiry_date"] = item["expiry_date"].isoformat()
            products.append(item)
        data = {"products": products,
                "stock": {f"{w}|{s}": q for (w, s), q in self.all_stock().items()}}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def set_quantity(self, warehouse: str, sku: str, quantity: int) -> None:
        super().set_quantity(warehouse, sku, quantity)
        self._save()

    def add_product(self, product: Product) -> None:
        super().add_product(product)
        self._save()
