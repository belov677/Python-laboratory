"""Лабораторная №7, вариант 17 «Склад». ВЕРСИЯ 2 — после рефакторинга по SOLID.

Здесь (и только здесь) создаются конкретные реализации и передаются в сервисы.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from infrastructure.container import Container
from infrastructure.notifier import ConsoleNotifier, EmailNotifier
from interfaces.repository import StockRepository
from interfaces.services import Notifier
from models.entities import PerishableProduct, Product
from operations.stock_operations import Receipt
from repositories.json_repository import JsonFileStockRepository
from repositories.memory_repository import InMemoryStockRepository
from services.report_service import ReportGenerator
from services.stock_service import StockService
from ui.console import ConsoleUI

DATA_FILE = Path(__file__).parent / "stock.json"


def build_container(storage: str, notifier: str) -> Container:
    container = Container()
    if storage == "2":
        container.register(StockRepository, lambda c: JsonFileStockRepository(DATA_FILE))
    else:
        container.register(StockRepository, lambda c: InMemoryStockRepository())
    if notifier == "2":
        container.register(Notifier, lambda c: EmailNotifier("manager@sklad.ru"))
    else:
        container.register(Notifier, lambda c: ConsoleNotifier())
    container.register(StockService, lambda c: StockService(c.resolve(StockRepository),
                                                            c.resolve(Notifier)))
    container.register(ReportGenerator, lambda c: ReportGenerator(c.resolve(StockRepository),
                                                                  c.resolve(StockRepository)))
    return container


def seed(service: StockService) -> None:
    if service.repository.list_products():
        return
    service.register_product(Product("NB-001", "Ноутбук Lenovo", 54990))
    service.register_product(Product("MS-010", "Мышь Logitech", 1490))
    service.register_product(PerishableProduct("MLK-1", "Молоко 3,2%", 89,
                                               expiry_date=date(2026, 10, 20)))
    for operation in (Receipt("Центральный", "NB-001", 12), Receipt("Центральный", "MS-010", 40),
                      Receipt("Северный", "MLK-1", 120)):
        service.execute(operation)


def main() -> None:
    print("Выберите хранилище:\n1. Память\n2. Файл (stock.json)")
    storage = input("> ").strip()
    print("Выберите способ уведомлений:\n1. Консоль\n2. E-mail (заглушка)")
    notifier = input("> ").strip()
    container = build_container(storage, notifier)
    service = container.resolve(StockService)
    seed(service)
    print(f"Хранилище: {type(service.repository).__name__}, "
          f"уведомления: {type(service.notifier).__name__}")
    ConsoleUI(service, container.resolve(ReportGenerator)).run()


if __name__ == "__main__":
    main()
