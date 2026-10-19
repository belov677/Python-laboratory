"""Лабораторная №8, вариант 17 «Склад»: Repository, Factory, Strategy, Command."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from factories.entity_factory import StrategyFactory
from repositories.file_repository import FileRepository
from repositories.memory_repository import InMemoryRepository
from services.warehouse_service import WarehouseService
from ui.console import ConsoleUI

DATA_FILE = Path(__file__).parent / "warehouse.json"


def seed(service: WarehouseService) -> None:
    if service.products():
        return
    service.add_product("MLK", "Молоко 3,2%", 89)
    service.add_product("NB", "Ноутбук Lenovo", 54990)
    service.receive_batch("MLK", 50, date(2026, 10, 25), 0, "Молкомбинат")
    service.receive_batch("MLK", 30, date(2026, 10, 18), 0, "Ферма «Зорька»")
    service.receive_batch("MLK", 40, date(2026, 11, 2), 1, "Молкомбинат")
    service.receive_batch("NB", 10, date(2030, 1, 1), 0, "Lenovo Rus")


def main() -> None:
    print("Выберите хранилище:\n1. Память\n2. Файл")
    repository = FileRepository(DATA_FILE) if input("> ").strip() == "2" else InMemoryRepository()
    service = WarehouseService(repository, StrategyFactory.create("fifo"))
    seed(service)
    print("Используется:", type(repository).__name__)
    ConsoleUI(service).run()


if __name__ == "__main__":
    main()
