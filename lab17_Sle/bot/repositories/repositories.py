"""Доступ к данным (SQLAlchemy async)."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from bot.database.models import Operation, Product, Stock, Supplier, User, Warehouse


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def touch(self, telegram_id: int, full_name: str, username: str | None) -> User:
        """Регистрирует пользователя при первом обращении и увеличивает счётчик сообщений."""
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, full_name=full_name, username=username, messages=0)
            self.session.add(user)
        user.messages += 1
        await self.session.commit()
        return user

    async def all(self) -> list[User]:
        return list(await self.session.scalars(select(User).order_by(User.created_at)))

    async def total_messages(self) -> int:
        return await self.session.scalar(select(func.coalesce(func.sum(User.messages), 0)))


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def warehouses(self) -> list[Warehouse]:
        return list(await self.session.scalars(select(Warehouse).order_by(Warehouse.id)))

    async def warehouse(self, warehouse_id: int) -> Warehouse | None:
        return await self.session.get(Warehouse, warehouse_id)

    async def suppliers(self) -> list[Supplier]:
        return list(await self.session.scalars(select(Supplier).order_by(Supplier.id)))

    async def supplier(self, supplier_id: int) -> Supplier | None:
        return await self.session.get(Supplier, supplier_id)

    async def products(self) -> list[Product]:
        return list((await self.session.scalars(select(Product).order_by(Product.name))).unique())

    async def product(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def product_by_sku(self, sku: str) -> Product | None:
        return await self.session.scalar(select(Product).where(Product.sku == sku))

    async def search(self, text: str) -> list[Product]:
        pattern = f"%{text.lower()}%"
        stmt = (select(Product).join(Supplier)
                .where(or_(func.lower(Product.name).like(pattern),
                           func.lower(Product.sku).like(pattern),
                           func.lower(Supplier.name).like(pattern)))
                .order_by(Product.name))
        return list((await self.session.scalars(stmt)).unique())

    async def stock(self, product_id: int, warehouse_id: int) -> Stock | None:
        return await self.session.scalar(select(Stock).where(
            Stock.product_id == product_id, Stock.warehouse_id == warehouse_id))

    async def stocks_in(self, warehouse_id: int) -> list[Stock]:
        stmt = (select(Stock).join(Stock.product).options(contains_eager(Stock.product))
                .where(Stock.warehouse_id == warehouse_id).order_by(Product.name))
        return list(await self.session.scalars(stmt))

    async def operations(self, limit: int = 10) -> list[Operation]:
        stmt = select(Operation).order_by(Operation.id.desc()).limit(limit)
        return list(await self.session.scalars(stmt))

    async def count(self, model) -> int:
        return await self.session.scalar(select(func.count()).select_from(model))

    async def operations_by_kind(self) -> dict[str, int]:
        rows = await self.session.execute(
            select(Operation.kind, func.count()).group_by(Operation.kind))
        return dict(rows.all())
