from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.item import Item


class ItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, skip: int, limit: int, sort: str, order: str, category: str | None,
             supplier: str | None, min_quantity: int | None,
             below_min: bool | None) -> tuple[list[Item], int]:
        stmt = select(Item)
        if category:
            stmt = stmt.where(Item.category == category)
        if supplier:
            stmt = stmt.where(Item.supplier.ilike(f"%{supplier}%"))
        if min_quantity is not None:
            stmt = stmt.where(Item.quantity >= min_quantity)
        if below_min is not None:
            stmt = stmt.where((Item.quantity < Item.min_stock) == below_min)
        total = self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        column = getattr(Item, sort)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Item.id)
        return list(self.session.scalars(stmt.offset(skip).limit(limit))), total

    def search(self, query: str) -> list[Item]:
        pattern = f"%{query}%"
        stmt = select(Item).where(or_(Item.name.ilike(pattern), Item.sku.ilike(pattern),
                                      Item.supplier.ilike(pattern))).order_by(Item.name)
        return list(self.session.scalars(stmt))

    def get(self, item_id: int) -> Item | None:
        return self.session.get(Item, item_id)

    def get_by_sku(self, sku: str) -> Item | None:
        return self.session.scalar(select(Item).where(Item.sku == sku))

    def add(self, item: Item) -> Item:
        self.session.add(item)
        self.session.flush()
        return item

    def delete(self, item: Item) -> None:
        self.session.delete(item)

    def statistics(self, today: date) -> dict:
        row = self.session.execute(select(
            func.count(Item.id), func.coalesce(func.sum(Item.quantity), 0),
            func.coalesce(func.sum(Item.quantity * Item.price), 0),
            func.coalesce(func.avg(Item.price), 0),
            func.count().filter(Item.quantity < Item.min_stock),
            func.count().filter(Item.expiry_date.is_not(None),
                                Item.expiry_date <= today + timedelta(days=30)))).one()
        by_category = dict(self.session.execute(
            select(Item.category, func.count()).group_by(Item.category).order_by(Item.category)).all())
        return {"total_items": row[0], "total_units": int(row[1]), "stock_value": float(row[2]),
                "average_price": round(float(row[3]), 2), "below_min": row[4],
                "expiring_30_days": row[5], "by_category": by_category}
