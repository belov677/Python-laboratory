"""Консольный интерфейс складского учёта: python -m src.main [путь к БД]"""
from __future__ import annotations

import logging
import sys

from src.repositories.sqlite_repository import SQLiteInventoryRepository
from src.services.exceptions import WarehouseError
from src.services.inventory_service import InventoryService
from src.services.notifier import LogNotifier

MENU = """
=== СКЛАД ===
1. Поступление    2. Списание    3. Перемещение
4. Остатки товара 5. Поиск       6. История движений
0. Выход"""


def seed(service: InventoryService) -> None:
    service.create_warehouse("Центральный", "Москва")
    service.create_warehouse("Северный", "Санкт-Петербург")
    for sku, name, unit, min_stock in [("EL-1001", "Ноутбук Lenovo", "шт", 5),
                                       ("EL-1002", "Монитор Samsung 27\"", "шт", 8),
                                       ("BD-3001", "Цемент М500", "мешок", 100),
                                       ("OF-5001", "Бумага A4", "пачка", 50)]:
        service.create_product(sku, name, unit, min_stock)
    for product_id, warehouse_id, qty in [(1, 1, 6), (1, 2, 3), (2, 1, 10), (3, 1, 150), (4, 2, 60)]:
        service.receive(product_id, warehouse_id, qty, "начальный остаток")


def ask_int(prompt: str) -> int:
    value = input(prompt).strip()
    try:
        return int(value)
    except ValueError:
        raise WarehouseError(f"Ожидалось целое число, получено «{value}»") from None


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    repo = SQLiteInventoryRepository(sys.argv[1] if len(sys.argv) > 1 else ":memory:")
    service = InventoryService(repo, LogNotifier())
    if repo.get_product(1) is None:
        seed(service)
    while True:
        print(MENU)
        choice = input("Выбор: ").strip()
        if choice == "0":
            break
        try:
            if choice == "1":
                left = service.receive(ask_int("id товара: "), ask_int("id склада: "), ask_int("Количество: "))
                print(f"Поступление выполнено, остаток на складе: {left}")
            elif choice == "2":
                left = service.write_off(ask_int("id товара: "), ask_int("id склада: "), ask_int("Количество: "))
                print(f"Списание выполнено, остаток на складе: {left}")
            elif choice == "3":
                src, dst = service.transfer(ask_int("id товара: "), ask_int("Со склада: "),
                                            ask_int("На склад: "), ask_int("Количество: "))
                print(f"Перемещено. Остатки: источник {src}, получатель {dst}")
            elif choice == "4":
                product = service.get_product(ask_int("id товара: "))
                balances = repo.balances(product.id)
                print(f"{product.sku} {product.name}: " + ", ".join(
                    f"склад {w}: {q}" for w, q in balances.items()) + f"; всего {sum(balances.values())}")
            elif choice == "5":
                for p in service.search(input("Текст: ")):
                    print(f"  {p.id}. {p.sku} {p.name}")
            elif choice == "6":
                for m in service.history(ask_int("id товара: ")):
                    print(f"  {m.created_at:%H:%M:%S} {m.type.value:9} {m.quantity:5} "
                          f"{m.source_id or '-'} → {m.target_id or '-'} {m.comment}")
            else:
                print("Неизвестный пункт")
        except WarehouseError as error:
            print(f"Ошибка ({type(error).__name__}): {error}")


if __name__ == "__main__":
    main()
