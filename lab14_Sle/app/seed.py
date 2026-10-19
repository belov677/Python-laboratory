"""Заполнение БД тестовыми товарами: python app/seed.py"""
from datetime import date

from config import settings
from database import Database
from models.item import Item

ITEMS = [
    ("NB-001", "Ноутбук Lenovo IdeaPad", "электроника", 12, 5, 54990, "Lenovo Rus", "A-01", None),
    ("MS-010", "Мышь Logitech M185", "электроника", 3, 10, 1490, "ООО Периферия", "A-02", None),
    ("KB-002", "Клавиатура Defender", "электроника", 25, 10, 990, "ООО Периферия", "A-03", None),
    ("MN-027", "Монитор Samsung 27", "электроника", 6, 4, 21990, "Lenovo Rus", "A-04", None),
    ("PP-A4", "Бумага A4 500 л.", "канцелярия", 80, 40, 420, "ТД Канцлер", "B-01", None),
    ("PN-BL", "Ручка шариковая синяя", "канцелярия", 15, 50, 25, "ТД Канцлер", "B-02", None),
    ("ST-24", "Степлер №24", "канцелярия", 9, 5, 310, "ТД Канцлер", "B-03", None),
    ("CH-OF", "Кресло офисное", "мебель", 7, 2, 8990, "Мебель-Опт", "C-01", None),
    ("TB-120", "Стол письменный 120 см", "мебель", 0, 1, 12500, "Мебель-Опт", "C-02", None),
    ("SH-05", "Стеллаж металлический", "мебель", 4, 2, 6400, "Мебель-Опт", "C-03", None),
    ("DT-1L", "Средство для мытья пола", "бытовая химия", 30, 20, 190, "ИП Чистов", "D-01", date(2028, 10, 1)),
    ("SP-500", "Мыло жидкое 500 мл", "бытовая химия", 12, 25, 140, "ИП Чистов", "D-02", date(2027, 3, 1)),
    ("MLK-32", "Молоко 3,2% 1 л", "продукты", 80, 40, 89, "Молкомбинат", "E-01", date(2026, 10, 23)),
    ("KF-1", "Кефир 1% 0,9 л", "продукты", 22, 30, 79, "Молкомбинат", "E-02", date(2026, 10, 18)),
    ("SR-RS", "Сыр российский 1 кг", "продукты", 16, 10, 690, "Молкомбинат", "E-03", date(2026, 12, 20)),
]
FIELDS = ("sku", "name", "category", "quantity", "min_stock", "price", "supplier", "location",
          "expiry_date")


def seed(db: Database) -> int:
    with db.session_factory() as session:
        if session.query(Item).count():
            return 0
        session.add_all(Item(**dict(zip(FIELDS, row))) for row in ITEMS)
        session.commit()
        return len(ITEMS)


if __name__ == "__main__":
    database = Database(settings.database_url)
    database.create_all()
    print("Добавлено товаров:", seed(database))
