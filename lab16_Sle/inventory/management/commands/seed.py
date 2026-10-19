"""Заполнение БД демонстрационными данными: python manage.py seed"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Product, Shipment, StockItem, Supplier, Warehouse

WAREHOUSES = [("Центральный", "Москва", "ул. Складская, 1"),
              ("Северный", "Санкт-Петербург", "пр. Обуховской Обороны, 120"),
              ("Восточный", "Казань", "ул. Тэцевская, 8")]
SUPPLIERS = [("ООО «ТехноПоставка»", "7701234567", "sales@technopost.ru", "Москва"),
             ("АО «СтройКомплект»", "7812345678", "info@stroykomplekt.ru", "Санкт-Петербург"),
             ("ООО «Агро-Снаб»", "1655012345", "agro@agrosnab.ru", "Казань"),
             ("ИП Кузнецов Д.А.", "502912345678", "kuznetsov@mail.ru", "Подольск"),
             ("ООО «Офис-Плюс»", "7704567890", "order@officeplus.ru", "Москва"),
             ("ООО «ТекстильПром»", "3702123456", "tp@textilprom.ru", "Иваново")]
P = Product.Category
PRODUCTS = [  # sku, name, category, unit, price, min_stock, suppliers
    ("EL-1001", "Ноутбук Lenovo IdeaPad 5", P.ELECTRONICS, "шт", 68990, 5, [0]),
    ("EL-1002", "Монитор Samsung 27\"", P.ELECTRONICS, "шт", 23490, 8, [0]),
    ("EL-1003", "Клавиатура Logitech K120", P.ELECTRONICS, "шт", 1290, 30, [0, 4]),
    ("EL-1004", "Мышь беспроводная", P.ELECTRONICS, "шт", 890, 40, [0, 4]),
    ("EL-1005", "Роутер TP-Link Archer", P.ELECTRONICS, "шт", 3990, 10, [0]),
    ("EL-1006", "Кабель HDMI 2 м", P.ELECTRONICS, "шт", 450, 50, [0, 3]),
    ("FD-2001", "Мука пшеничная в/с", P.FOOD, "кг", 52, 500, [2]),
    ("FD-2002", "Сахар-песок", P.FOOD, "кг", 79, 400, [2]),
    ("FD-2003", "Масло подсолнечное", P.FOOD, "л", 135, 200, [2, 3]),
    ("FD-2004", "Гречневая крупа", P.FOOD, "кг", 95, 300, [2]),
    ("FD-2005", "Чай чёрный листовой", P.FOOD, "кг", 890, 30, [2]),
    ("BD-3001", "Цемент М500, мешок 50 кг", P.BUILDING, "шт", 520, 100, [1]),
    ("BD-3002", "Арматура 12 мм", P.BUILDING, "м", 68, 1000, [1, 3]),
    ("BD-3003", "Гипсокартон 12,5 мм", P.BUILDING, "шт", 410, 150, [1]),
    ("BD-3004", "Краска фасадная белая", P.BUILDING, "л", 380, 80, [1, 3]),
    ("BD-3005", "Саморезы 3,5×35, 1000 шт", P.BUILDING, "шт", 690, 40, [1, 3]),
    ("CL-4001", "Куртка рабочая утеплённая", P.CLOTHES, "шт", 3200, 25, [5]),
    ("CL-4002", "Перчатки х/б", P.CLOTHES, "шт", 35, 500, [5, 3]),
    ("CL-4003", "Каска защитная", P.CLOTHES, "шт", 450, 40, [5, 1]),
    ("CL-4004", "Ботинки рабочие", P.CLOTHES, "шт", 2900, 30, [5]),
    ("OF-5001", "Бумага A4, пачка 500 л.", P.OFFICE, "шт", 420, 100, [4]),
    ("OF-5002", "Ручка шариковая синяя", P.OFFICE, "шт", 25, 300, [4]),
    ("OF-5003", "Папка-регистратор", P.OFFICE, "шт", 210, 60, [4]),
    ("OF-5004", "Степлер №24", P.OFFICE, "шт", 340, 20, [4]),
]


class Command(BaseCommand):
    help = "Создаёт склады, поставщиков, товары, остатки, поставки и пользователей"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="удалить существующие данные")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(17)
        if options["clear"]:
            Shipment.objects.all().delete()
            StockItem.objects.all().delete()
            Product.objects.all().delete()
            Supplier.objects.all().delete()
            Warehouse.objects.all().delete()
        warehouses = [Warehouse.objects.create(name=n, city=c, address=a) for n, c, a in WAREHOUSES]
        suppliers = [Supplier.objects.create(name=n, inn=i, email=e, city=c,
                                             phone=f"+7 900 {k:03d}-00-0{k}")
                     for k, (n, i, e, c) in enumerate(SUPPLIERS, 1)]
        for k, (sku, name, cat, unit, price, min_stock, sup) in enumerate(PRODUCTS):
            product = Product.objects.create(sku=sku, name=name, category=cat, unit=unit,
                                             price=Decimal(price), min_stock=min_stock)
            product.suppliers.set([suppliers[i] for i in sup])
            for w in rng.sample(warehouses, rng.randint(1, 3)):
                # каждый 4-й товар делаем критическим
                qty = rng.randint(0, min_stock // 3) if k % 4 == 1 else rng.randint(min_stock // 2, min_stock * 2)
                StockItem.objects.create(product=product, warehouse=w, quantity=qty)
        products = list(Product.objects.prefetch_related("suppliers"))
        for n in range(14):
            product = products[(n * 5) % len(products)]
            shipment = Shipment.objects.create(
                product=product, supplier=product.suppliers.first(),
                warehouse=warehouses[n % 3], quantity=product.min_stock,
                purchase_price=(product.price * Decimal("0.7")).quantize(Decimal("0.01")),
                expected_date=date(2026, 10, 1) + timedelta(days=n * 2))
            if n < 8:
                shipment.receive()
            elif n == 8:
                shipment.status = Shipment.Status.CANCELLED
                shipment.save()
        managers, _ = Group.objects.get_or_create(name="Менеджеры склада")
        managers.permissions.set(Permission.objects.filter(
            content_type__app_label="inventory",
            codename__regex=r"^(add|change|delete|view)_"))
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@sklad.local", "admin12345")
        if not User.objects.filter(username="manager").exists():
            User.objects.create_user("manager", "manager@sklad.local", "manager12345",
                                     first_name="Мария").groups.add(managers)
        if not User.objects.filter(username="viewer").exists():
            User.objects.create_user("viewer", "viewer@sklad.local", "viewer12345",
                                     first_name="Виктор")
        self.stdout.write(self.style.SUCCESS(
            f"Склады: {Warehouse.objects.count()}, поставщики: {Supplier.objects.count()}, "
            f"товары: {Product.objects.count()}, остатки: {StockItem.objects.count()}, "
            f"поставки: {Shipment.objects.count()}, пользователи: {User.objects.count()}"))
