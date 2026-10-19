from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Item:
    """Товар на складе."""
    id: int
    sku: str
    name: str
    category: str
    quantity: int
    min_stock: int
    price: float
    location: str

    @property
    def below_min(self) -> bool:
        return self.quantity < self.min_stock

    def to_dict(self) -> dict:
        data = asdict(self)
        data["below_min"] = self.below_min
        return data
