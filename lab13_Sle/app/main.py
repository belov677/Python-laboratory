"""Лабораторная №13, вариант 17 «Склад — товары»: MongoDB + Redis.

Запуск: python app/main.py [--reset]
"""
from __future__ import annotations

import argparse
import copy
import logging
from datetime import date

from cache import RedisCache
from config import CACHE_TTL
from exceptions import WarehouseError
from models import Batch, WarehouseItem
from mongodb import get_database
from redis_client import get_redis
from repository import MongoRepository
from seed import ITEMS
from service import WarehouseService

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

MENU = """
===== СКЛАД: MongoDB + Redis =====
 1. Add          — добавить товар         6. Delete        — удалить товар
 2. Find         — найти по артикулу      7. Statistics    — агрегация MongoDB
 3. List         — список товаров         8. Cache status  — состояние Redis
 4. Search       — поиск по условию       9. Clear cache   — очистить кэш
 5. Update       — изменить товар        10. Benchmark     — MongoDB vs Redis
 0. Exit"""


def show(items: list[WarehouseItem]) -> None:
    if not items:
        print("  ничего не найдено")
    for i in items:
        expiry = f" годен до {i.nearest_expiry}" if i.nearest_expiry else ""
        print(f"  {i.sku:8} {i.name:28} {i.category:14} {i.quantity:4} шт. "
              f"(мин {i.min_stock:2}) {i.price:9.2f} {i.location['zone']}-{i.location['rack']}-"
              f"{i.location['shelf']} {i.status}{expiry}")


def ask_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Введите целое число.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    try:
        db = get_database()
    except WarehouseError as error:
        print("Ошибка:", error)
        return
    repo = MongoRepository(db)
    cache = RedisCache(get_redis(), CACHE_TTL)
    service = WarehouseService(repo, cache)
    if args.reset:
        repo.collection.drop()
        cache.clear()
        print("Созданы индексы:", ", ".join(repo.create_indexes()))
        for item in ITEMS:
            service.add_item(copy.deepcopy(item))
    print(f"MongoDB: {db.name}.{repo.collection.name}, документов: {repo.count()}; "
          f"Redis: {'доступен' if cache.status().get('error') is None else 'НЕДОСТУПЕН'}")

    while True:
        print(MENU)
        choice = input("Выберите пункт: ").strip()
        if choice == "0":
            break
        try:
            if choice == "1":
                item = WarehouseItem(
                    sku=input("Артикул: ").strip(), name=input("Название: ").strip(),
                    category=input("Категория: ").strip(), price=float(input("Цена: ")),
                    min_stock=ask_int("Минимальный остаток: "),
                    supplier={"name": input("Поставщик: "), "city": input("Город поставщика: "),
                              "contact": {"phone": input("Телефон: "), "email": ""}},
                    location={"zone": input("Зона: "), "rack": ask_int("Стеллаж: "),
                              "shelf": ask_int("Полка: ")},
                    batches=[Batch(input("Номер партии: "), ask_int("Количество: "), date.today(),
                                   date.fromisoformat(e) if (e := input("Срок годности (ГГГГ-ММ-ДД или пусто): ").strip()) else None)],
                    tags=input("Теги через запятую: ").replace(" ", "").split(","))
                print("  Добавлен, _id =", service.add_item(item).id)
            elif choice == "2":
                data, source = service.get_item(input("Артикул: ").strip())
                print(f"  [источник: {source}] {data['sku']} {data['name']}, {data['quantity']} шт., "
                      f"{data['price']} руб., поставщик {data['supplier']['name']} "
                      f"({data['supplier']['city']}), место {data['location']}")
                print("  партии:", "; ".join(f"{b['batch_no']}: {b['quantity']} шт."
                                             + (f" до {b['expiry_date']}" if b['expiry_date'] else "")
                                             for b in data["batches"]))
            elif choice == "3":
                show(service.list_items())
            elif choice == "4":
                print("  виды: category, city (поставщика), tag, name, price (мин-макс), "
                      "expiring (дата), low")
                kind = input("Вид поиска: ").strip()
                value = "" if kind == "low" else input("Значение: ").strip()
                show(service.search(kind, value))
            elif choice == "5":
                sku = input("Артикул: ").strip()
                action = input("1 — цена/мин. остаток, 2 — поступление партии, 3 — списание: ").strip()
                if action == "1":
                    price, min_stock = input("Новая цена (пусто — без изменений): "), \
                        input("Новый минимальный остаток (пусто — без изменений): ")
                    show([service.update_item(sku, float(price) if price else None,
                                              int(min_stock) if min_stock else None)])
                elif action == "2":
                    expiry = input("Срок годности (пусто — нет): ").strip()
                    show([service.receive_batch(sku, input("Номер партии: "), ask_int("Количество: "),
                                                date.fromisoformat(expiry) if expiry else None)])
                elif action == "3":
                    show([service.write_off(sku, ask_int("Количество: "))])
            elif choice == "6":
                service.delete_item(input("Артикул: ").strip())
                print("  Удалено (кэш и остаток в Redis очищены)")
            elif choice == "7":
                stats = service.statistics()
                print(f"  Всего товаров: {stats['total']}")
                print("  По категориям:")
                for row in stats["by_category"]:
                    print(f"    {row['_id']:14} позиций {row['items']:2}, единиц {row['units']:4}, "
                          f"стоимость {row['value']:11,.2f}, средняя цена {row['avg_price']:9.2f}")
                print("  По поставщикам:")
                for row in stats["by_supplier"]:
                    print(f"    {row['_id']:15} {row['city']:16} позиций {row['items']}, ниже минимума {row['low']}")
                print("  Партии по месяцу окончания срока:",
                      ", ".join(f"{r['_id']}: {r['units']} шт." for r in stats["expiring_by_month"]))
                print("  ТОП-3 по стоимости запаса:",
                      ", ".join(f"{r['sku']} ({r['value']:,.0f})" for r in stats["top_by_value"]))
                print("  Популярные (Redis):", stats["popular"])
            elif choice == "8":
                for key, value in cache.status().items():
                    print(f"  {key}: {value}")
                sku = input("Остаток по артикулу (быстрый поиск): ").strip()
                quantity, source = service.stock_of(sku)
                print(f"  {sku}: {quantity} шт. [источник: {source}]")
            elif choice == "9":
                print("  Удалено ключей:", cache.clear())
            elif choice == "10":
                sku = input("Артикул для теста: ").strip()
                print(f"  {'запросов':>9} | {'MongoDB, с':>10} | {'мс/запрос':>9} | {'Redis, с':>9} | {'мс/запрос':>9}")
                for n, mongo, redis_time in service.benchmark(sku):
                    print(f"  {n:>9} | {mongo:10.4f} | {mongo / n * 1000:9.4f} | {redis_time:9.4f} | "
                          f"{redis_time / n * 1000:9.4f}")
            else:
                print("Неизвестный пункт меню.")
        except WarehouseError as error:
            print(f"Ошибка ({type(error).__name__}): {error}")
        except ValueError as error:
            print(f"Ошибка данных: {error}")


if __name__ == "__main__":
    main()
