"""Консольный интерфейс: только ввод-вывод, бизнес-логика — в сервисах."""
from __future__ import annotations

from datetime import date

from models.entities import StockError
from operations.stock_operations import Inventory, Receipt, ReturnToSupplier, Transfer, WriteOff
from services.report_service import ReportGenerator
from services.stock_service import StockService


class ConsoleUI:
    def __init__(self, service: StockService, reports: ReportGenerator) -> None:
        self.service = service
        self.reports = reports
        # пункт меню → (название, функция, создающая операцию)
        self.operations = {
            "1": ("Поступление", lambda: Receipt(self._text("Склад"), self._text("Артикул"),
                                                 self._int("Количество"))),
            "2": ("Списание", lambda: WriteOff(self._text("Склад"), self._text("Артикул"),
                                               self._int("Количество"))),
            "3": ("Перемещение", lambda: Transfer(self._text("Со склада"), self._text("На склад"),
                                                  self._text("Артикул"), self._int("Количество"))),
            "4": ("Инвентаризация", lambda: Inventory(self._text("Склад"), self._text("Артикул"),
                                                      self._int("Фактическое количество"))),
            "5": ("Возврат поставщику", lambda: ReturnToSupplier(
                self._text("Склад"), self._text("Артикул"), self._int("Количество"))),
        }

    @staticmethod
    def _text(prompt: str) -> str:
        return input(f"{prompt}: ").strip()

    @staticmethod
    def _int(prompt: str) -> int:
        while True:
            try:
                return int(input(f"{prompt}: "))
            except ValueError:
                print("Введите целое число.")

    def show_report(self) -> None:
        print("=== Остатки ===")
        for line in self.reports.stock_lines():
            print(line)
        print(f"Стоимость запасов: {self.reports.total_value():,.2f} руб.")
        expiring = self.reports.expiring(date(2026, 10, 15), 10)
        print("Истекает срок годности (10 дней):", expiring or "нет")

    def show_history(self) -> None:
        for i, item in enumerate(self.service.history, 1):
            print(f"{i}. {item.operation.value:18} {item.sku:7} {item.details}")

    def run(self) -> None:
        while True:
            print("\n===== СКЛАД (SOLID) =====")
            for key, (title, _) in self.operations.items():
                print(f"{key}. {title}")
            print("6. Отчёт по остаткам\n7. Журнал операций\n0. Выход")
            choice = input("Выберите пункт: ").strip()
            if choice == "0":
                break
            if choice == "6":
                self.show_report()
            elif choice == "7":
                self.show_history()
            elif choice in self.operations:
                try:
                    result = self.service.execute(self.operations[choice][1]())
                    print("Выполнено:", result.details)
                except (StockError, ValueError) as error:
                    print(f"Ошибка: {error}")
            else:
                print("Неизвестный пункт меню.")
