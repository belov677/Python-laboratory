"""Сравнение запроса по вложенному полю до и после создания индекса (20 000 документов)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))
from mongodb import get_database  # noqa: E402
from repository import MongoRepository  # noqa: E402

db = get_database()
repo = MongoRepository(db, "explain_demo")
repo.collection.drop()
cities = ["Москва", "Казань", "Самара", "Тверь", "Пермь", "Омск", "Тула", "Сочи"]
random.seed(17)
repo.collection.insert_many([
    {"sku": f"X-{i:05d}", "name": f"Товар {i}", "category": random.choice(["a", "b", "c", "d"]),
     "price": random.randint(10, 100000), "quantity": random.randint(0, 500), "min_stock": 10,
     "supplier": {"name": f"Поставщик {i % 300}", "city": random.choice(cities)}}
    for i in range(20000)])
query = {"supplier.city": "Тверь", "price": {"$gte": 90000}}
print(f"Коллекция explain_demo: {repo.count()} документов")
print("Запрос:", query)
print("Без индекса:  ", repo.explain(query))
repo.collection.create_index([("supplier.city", 1), ("price", -1)], name="ix_city_price")
print("С индексом:   ", repo.explain(query))
repo.collection.drop()
