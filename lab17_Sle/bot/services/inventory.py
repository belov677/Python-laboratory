"""Бизнес-логика склада: каталог, поступление, списание, критические остатки."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Operation, Product, Stock, Supplier, User, Warehouse
from bot.repositories.repositories import CatalogRepository, UserRepository

from .exceptions import NotEnoughStockError, NotFoundError, ValidationError
from .validators import parse_name, parse_price, parse_search, parse_sku

log = logging.getLogger("bot.service")


@dataclass
class MovementResult:
    product: Product
    warehouse: Warehouse
    quantity: int
    left: int
    critical: bool          # остаток стал ниже минимального


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CatalogRepository(session)
        self.users = UserRepository(session)

    # ---------- чтение ----------
    async def warehouses(self) -> list[Warehouse]:
        return await self.repo.warehouses()

    async def suppliers(self) -> list[Supplier]:
        return await self.repo.suppliers()

    async def get_product(self, product_id: int) -> Product:
        product = await self.repo.product(product_id)
        if product is None:
            raise NotFoundError("Товар не найден (возможно, он был удалён)")
        return product

    async def get_warehouse(self, warehouse_id: int) -> Warehouse:
        warehouse = await self.repo.warehouse(warehouse_id)
        if warehouse is None:
            raise NotFoundError("Склад не найден")
        return warehouse

    async def stock_in_warehouse(self, warehouse_id: int) -> tuple[Warehouse, list[Stock]]:
        warehouse = await self.get_warehouse(warehouse_id)
        return warehouse, await self.repo.stocks_in(warehouse_id)

    async def search(self, text: str) -> list[Product]:
        return await self.repo.search(parse_search(text))

    async def critical(self) -> list[Product]:
        return [p for p in await self.repo.products() if p.is_critical]

    # ---------- CRUD товара ----------
    async def create_product(self, name: str, sku: str, price: str, min_stock: int,
                             supplier_id: int) -> Product:
        name, sku, price_value = parse_name(name), parse_sku(sku), parse_price(price)
        if await self.repo.product_by_sku(sku):
            raise ValidationError(f"Товар с артикулом {sku} уже существует")
        supplier = await self.repo.supplier(supplier_id)
        if supplier is None:
            raise NotFoundError("Поставщик не найден")
        warehouses = await self.repo.warehouses()
        product = Product(name=name, sku=sku, price=price_value, min_stock=min_stock,
                          supplier=supplier, stocks=[Stock(warehouse=w, quantity=0) for w in warehouses])
        self.session.add(product)
        await self.session.commit()
        log.info("Создан товар %s %s", sku, name)
        return product

    async def update_product(self, product_id: int, field: str, value: str) -> Product:
        product = await self.get_product(product_id)
        if field == "price":
            product.price = parse_price(value)
        elif field == "min_stock":
            if not value.strip().isdigit():
                raise ValidationError("Минимальный остаток — целое неотрицательное число")
            product.min_stock = int(value)
        elif field == "name":
            product.name = parse_name(value)
        else:
            raise ValidationError(f"Поле {field} нельзя изменить")
        await self.session.commit()
        log.info("Изменён товар %s: %s = %s", product.sku, field, value)
        return product

    async def delete_product(self, product_id: int) -> str:
        product = await self.get_product(product_id)
        name = product.name
        await self.session.delete(product)
        await self.session.commit()
        log.info("Удалён товар %s", product.sku)
        return name

    # ---------- движение товара ----------
    async def _stock(self, product_id: int, warehouse_id: int) -> tuple[Product, Warehouse, Stock]:
        product = await self.get_product(product_id)
        warehouse = await self.get_warehouse(warehouse_id)
        stock = await self.repo.stock(product_id, warehouse_id)
        if stock is None:
            stock = Stock(product=product, warehouse=warehouse, quantity=0)
            self.session.add(stock)
        return product, warehouse, stock

    async def receive(self, product_id: int, warehouse_id: int, quantity: int,
                      user_id: int) -> MovementResult:
        """Поступление товара на склад."""
        if quantity <= 0:
            raise ValidationError("Количество должно быть больше нуля")
        product, warehouse, stock = await self._stock(product_id, warehouse_id)
        stock.quantity += quantity
        self.session.add(Operation(kind="receipt", product=product, warehouse=warehouse,
                                   quantity=quantity, user_id=user_id))
        await self.session.commit()
        await self.session.refresh(product, ["stocks"])
        log.info("Поступление: %s +%s на %s", product.sku, quantity, warehouse.name)
        return MovementResult(product, warehouse, quantity, stock.quantity, product.is_critical)

    async def write_off(self, product_id: int, warehouse_id: int, quantity: int,
                        user_id: int) -> MovementResult:
        """Списание товара; остаток не может стать отрицательным."""
        if quantity <= 0:
            raise ValidationError("Количество должно быть больше нуля")
        product, warehouse, stock = await self._stock(product_id, warehouse_id)
        if quantity > stock.quantity:     # изменений ещё не было — откатывать нечего
            raise NotEnoughStockError(
                f"Недостаточно товара на складе «{warehouse.name}»: есть {stock.quantity}, "
                f"требуется {quantity}")
        was_critical = product.is_critical
        stock.quantity -= quantity
        self.session.add(Operation(kind="writeoff", product=product, warehouse=warehouse,
                                   quantity=quantity, user_id=user_id))
        await self.session.commit()
        await self.session.refresh(product, ["stocks"])
        log.info("Списание: %s −%s со склада %s", product.sku, quantity, warehouse.name)
        return MovementResult(product, warehouse, quantity, stock.quantity,
                              product.is_critical and not was_critical)

    # ---------- статистика ----------
    async def statistics(self) -> dict:
        ops = await self.repo.operations_by_kind()
        return {"users": await self.repo.count(User), "messages": await self.users.total_messages(),
                "products": await self.repo.count(Product), "warehouses": await self.repo.count(Warehouse),
                "suppliers": await self.repo.count(Supplier), "stocks": await self.repo.count(Stock),
                "receipts": ops.get("receipt", 0), "writeoffs": ops.get("writeoff", 0),
                "critical": len(await self.critical())}

    async def users_list(self) -> list[User]:
        return await self.users.all()

    async def last_operations(self) -> list[Operation]:
        return await self.repo.operations()
