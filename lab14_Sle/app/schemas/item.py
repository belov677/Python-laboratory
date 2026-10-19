"""Pydantic-схемы ресурса /items."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ItemBase(BaseModel):
    sku: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9-]+$", examples=["NB-001"])
    name: str = Field(min_length=2, max_length=200, examples=["Ноутбук Lenovo IdeaPad"])
    category: str = Field(min_length=2, max_length=100, examples=["электроника"])
    quantity: int = Field(ge=0, examples=[12])
    min_stock: int = Field(default=0, ge=0, examples=[5])
    price: float = Field(gt=0, examples=[54990])
    supplier: str = Field(min_length=2, max_length=150, examples=["Lenovo Rus"])
    location: str = Field(pattern=r"^[A-Z]-\d{2}$", examples=["A-01"],
                          description="Зона и стеллаж, например A-01")
    expiry_date: date | None = Field(default=None, examples=[None])


class ItemCreate(ItemBase):
    pass


class ItemReplace(ItemBase):
    """PUT — полное изменение, все поля обязательны."""


class ItemUpdate(BaseModel):
    """PATCH — только переданные поля."""
    name: str | None = Field(default=None, min_length=2, max_length=200)
    category: str | None = Field(default=None, min_length=2)
    quantity: int | None = Field(default=None, ge=0)
    min_stock: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, gt=0)
    supplier: str | None = Field(default=None, min_length=2)
    location: str | None = Field(default=None, pattern=r"^[A-Z]-\d{2}$")
    expiry_date: date | None = None

    @model_validator(mode="after")
    def not_empty(self):
        if not self.model_fields_set:
            raise ValueError("Не передано ни одного поля для изменения")
        return self


class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    below_min: bool = False

    @model_validator(mode="after")
    def compute_below_min(self):
        self.below_min = self.quantity < self.min_stock
        return self


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    skip: int
    limit: int


class ItemStatistics(BaseModel):
    total_items: int
    total_units: int
    stock_value: float
    average_price: float
    below_min: int
    expiring_30_days: int
    by_category: dict[str, int]


SortField = Literal["id", "sku", "name", "category", "quantity", "price", "expiry_date"]
SortOrder = Literal["asc", "desc"]
