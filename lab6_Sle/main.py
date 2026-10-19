"""Лабораторная работа №6. Вариант 17 — «Склад».

Меню формируется автоматически: методы ConsoleApp, помеченные декоратором
@command, находятся через inspect.getmembers().
"""
from __future__ import annotations

import inspect
from pathlib import Path

from context import OperationLogger, StockTransaction
from decorators import command, log_call, measure_time, repeat
from exceptions import WarehouseError
from introspection import inspect_object
from models import Delivery, DeliveryStatus, Product, Warehouse
from protocols import Reportable, print_report
from services import WarehouseService

LOG_FILE = Path(__file__).parent / "operations.log"


def read_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Ошибка: введите целое число.")


def read_float(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt).replace(",", "."))
        except ValueError:
            print("Ошибка: введите число.")


def seed(service: WarehouseService) -> None:
    service.entities += [
        Warehouse(1, "Центральный", "Москва, ул. Складская, 1", capacity=2000),
        Warehouse(2, "Северный", "Химки, ш. Ленинградское, 15", capacity=500),
        Product(3, "Ноутбук Lenovo", "NB-001", 54990, 12, 5, 1),
        Product(4, "Мышь Logitech", "MS-010", 1490, 3, 10, 1),
        Product(5, "Монитор Samsung 27\"", "MN-027", 21990, 6, 4, 1),
        Product(6, "Клавиатура Defender", "KB-002", 990, 0, 8, 2),
        Product(7, "Кабель HDMI 2 м", "CB-HDMI", 390, 150, 30, 2),
    ]
    for w in service.of_type(Warehouse):
        w.product_ids = [p.id for p in service.of_type(Product) if p.warehouse_id == w.id]
    service.entities += [
        Delivery(8, "П-0001", product_id=4, quantity=40, supplier="ООО Периферия"),
        Delivery(9, "П-0002", product_id=6, quantity=25, supplier="ИП Клавишин",
                 status=DeliveryStatus.ACCEPTED),
        Delivery(10, "П-0003", product_id=3, quantity=5, supplier="Lenovo Rus",
                 status=DeliveryStatus.PLACED),
    ]


@log_call
@measure_time
def demo_sum(a: int, b: int) -> int:
    """Пример функции с двумя декораторами."""
    return a + b


@repeat(3)
def demo_ping() -> str:
    print("  ping")
    return "pong"


class ConsoleApp:
    def __init__(self, service: WarehouseService) -> None:
        self.service = service

    # ----- поиск команд через интроспекцию -----
    def commands(self) -> list:
        found = [m for _, m in inspect.getmembers(self, inspect.ismethod)
                 if hasattr(m, "menu_command")]
        return sorted(found, key=lambda m: m.menu_order)

    def run(self) -> None:
        commands = self.commands()
        while True:
            print("\n===== СКЛАД: МЕНЮ =====")
            for number, method in enumerate(commands, 1):
                print(f"{number:2}. {method.menu_command}")
            print(" 0. Выход")
            choice = input("Выберите пункт: ").strip()
            if choice == "0":
                print("Работа завершена.")
                return
            if not choice.isdigit() or not 1 <= int(choice) <= len(commands):
                print("Ошибка: неизвестный пункт меню.")
                continue
            method = commands[int(choice) - 1]
            try:
                with OperationLogger(method.__name__, LOG_FILE):
                    method()
            except WarehouseError as error:
                print(f"Ошибка ({type(error).__name__}): {error}")
            except ValueError as error:
                print(f"Ошибка данных: {error}")

    # ----- пункты меню -----
    @command("Добавить объект", 1)
    def add_entity(self) -> None:
        kind = input("Тип (1 — товар, 2 — склад, 3 — поставка): ").strip()
        new_id = self.service.next_id()
        if kind == "1":
            entity = Product(new_id, input("Название: "), input("Артикул: "),
                             read_float("Цена: "), read_int("Количество: "),
                             read_int("Минимальный остаток: "), read_int("id склада: "))
        elif kind == "2":
            entity = Warehouse(new_id, input("Название: "), input("Адрес: "),
                               read_int("Вместимость: "))
        elif kind == "3":
            entity = Delivery(new_id, input("Номер поставки: "), read_int("id товара: "),
                              read_int("Количество: "), input("Поставщик: "))
            self.service.get(entity.product_id, Product)
        else:
            print("Неизвестный тип.")
            return
        self.service.add(entity)
        print("Добавлено:", entity.get_report_data())

    @command("Удалить объект", 2)
    def delete_entity(self) -> None:
        print("Удалено:", self.service.remove(read_int("id объекта: ")).short())

    @command("Найти объект", 3)
    def find_entity(self) -> None:
        result = self.service.find(input("Название или артикул: "))
        print_report(result) if result else print("Ничего не найдено.")

    @command("Вывести все объекты", 4)
    def show_all(self) -> None:
        for kind, title in ((Warehouse, "Склады"), (Product, "Товары"), (Delivery, "Поставки")):
            print(f"--- {title} ---")
            for e in self.service.of_type(kind):
                print(f"{e.id:3}. {e.get_report_data()}")

    @command("Изменить статус поставки", 5)
    def change_delivery(self) -> None:
        delivery_id = read_int("id поставки: ")
        action = input("1 — принять, 2 — разместить, 3 — отменить: ").strip()
        operations = {"1": self.service.accept_delivery, "2": self.service.place_delivery,
                      "3": self.service.cancel_delivery}
        if action not in operations:
            print("Неизвестное действие.")
            return
        print("Новый статус:", operations[action](delivery_id).status.value)

    @command("Стоимость запасов и товары с минимальным остатком", 6)
    def domain_operations(self) -> None:
        print(f"Стоимость запасов: {self.service.stock_value():,.2f} руб.")
        print("Товары с минимальным остатком:")
        for p in self.service.low_stock_products():
            print(f"   {p.sku}: {p.quantity} шт. (порог {p.min_stock})")

    @command("Списать товар (в транзакции)", 7)
    def write_off(self) -> None:
        product_id = read_int("id товара: ")
        quantity = read_int("Количество: ")
        with StockTransaction(self.service):
            product = self.service.write_off(product_id, quantity)
        print(f"Остаток {product.sku}: {product.quantity}")

    @command("Статистика", 8)
    def statistics(self) -> None:
        for key, value in self.service.statistics().items():
            print(f"{key:33} {value}")

    @command("Интроспекция объекта", 9)
    def introspect(self) -> None:
        inspect_object(self.service.get(read_int("id объекта: ")))

    @command("Демонстрация декораторов", 10)
    def decorators_demo(self) -> None:
        print("demo_sum.__name__ =", demo_sum.__name__, "| __doc__ =", demo_sum.__doc__)
        demo_sum(2, 3)
        print("@repeat(3):", demo_ping())
        print("@require_status — попытка принять размещённую поставку П-0003:")
        try:
            self.service.accept_delivery(10)
        except WarehouseError as error:
            print("   ", type(error).__name__, error)

    @command("Демонстрация контекстного менеджера", 11)
    def context_demo(self) -> None:
        product = self.service.get(7, Product)
        print(f"Кабель HDMI до транзакции: {product.quantity}")
        try:
            with StockTransaction(self.service):
                self.service.write_off(7, 100)
                print("   списано 100, текущий остаток:", self.service.get(7).quantity)
                self.service.write_off(7, 1000)      # ошибка → откат
        except ValueError as error:
            print("   исключение передано дальше:", error)
        print(f"Кабель HDMI после отката: {self.service.get(7).quantity}")
        with OperationLogger("demo_operation", LOG_FILE, product_id=7):
            pass
        print("Последние записи журнала operations.log:")
        print("\n".join(LOG_FILE.read_text(encoding="utf-8").strip().split("\n")[-6:]))

    @command("Демонстрация Protocol (отчёт)", 12)
    def protocol_demo(self) -> None:
        reportables: list[Reportable] = [self.service.get(1), self.service.get(4),
                                         self.service.get(8)]
        print_report(reportables)


def main() -> None:
    LOG_FILE.unlink(missing_ok=True)
    service = WarehouseService()
    seed(service)
    ConsoleApp(service).run()


if __name__ == "__main__":
    main()
