"""Тестовые данные: 3 склада, 4 поставщика, 12 товаров, 36 остатков (55 записей)."""
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Product, Stock, Supplier, Warehouse

WAREHOUSES = [("Центральный", "Москва"), ("Северный", "Санкт-Петербург"), ("Восточный", "Казань")]
SUPPLIERS = [("ООО «ТехноПоставка»", "+7 495 111-22-33"), ("АО «СтройКомплект»", "+7 812 222-33-44"),
             ("ООО «Офис-Плюс»", "+7 495 333-44-55"), ("ООО «Агро-Снаб»", "+7 843 444-55-66")]
PRODUCTS = [  # sku, name, price, min, supplier, остатки по складам
    ("EL-1001", "Ноутбук Lenovo IdeaPad 5", 68990, 5, 0, (4, 3, 0)),
    ("EL-1002", "Монитор Samsung 27\"", 23490, 8, 0, (6, 2, 3)),
    ("EL-1003", "Клавиатура Logitech K120", 1290, 30, 0, (25, 20, 10)),
    ("EL-1004", "Мышь беспроводная", 890, 40, 0, (8, 5, 2)),
    ("BD-3001", "Цемент М500, мешок 50 кг", 520, 100, 1, (120, 60, 40)),
    ("BD-3002", "Гипсокартон 12,5 мм", 410, 150, 1, (30, 20, 0)),
    ("BD-3003", "Краска фасадная белая", 380, 80, 1, (50, 45, 30)),
    ("OF-5001", "Бумага A4, пачка 500 л.", 420, 100, 2, (80, 60, 40)),
    ("OF-5002", "Ручка шариковая синяя", 25, 300, 2, (150, 100, 120)),
    ("OF-5003", "Папка-регистратор", 210, 60, 2, (10, 12, 5)),
    ("FD-2001", "Мука пшеничная в/с, кг", 52, 500, 3, (400, 200, 300)),
    ("FD-2002", "Сахар-песок, кг", 79, 400, 3, (100, 50, 80)),
]


async def seed(session: AsyncSession) -> None:
    warehouses = [Warehouse(name=n, city=c) for n, c in WAREHOUSES]
    suppliers = [Supplier(name=n, phone=p) for n, p in SUPPLIERS]
    session.add_all(warehouses + suppliers)
    for sku, name, price, min_stock, sup, quantities in PRODUCTS:
        product = Product(sku=sku, name=name, price=price, min_stock=min_stock,
                          supplier=suppliers[sup])
        product.stocks = [Stock(warehouse=w, quantity=q) for w, q in zip(warehouses, quantities)]
        session.add(product)
    await session.commit()
