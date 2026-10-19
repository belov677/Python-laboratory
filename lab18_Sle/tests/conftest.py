"""Общие фикстуры."""
from contextlib import nullcontext
from unittest.mock import MagicMock, create_autospec

import pytest

from src.models.entities import Product, Warehouse
from src.repositories.sqlite_repository import SQLiteInventoryRepository
from src.services.inventory_service import InventoryService


@pytest.fixture
def repo_mock():
    """Mock-репозиторий со спецификацией реального класса: опечатка в имени метода → ошибка."""
    repo = create_autospec(SQLiteInventoryRepository, instance=True)
    repo.transaction.side_effect = lambda: nullcontext()
    repo.get_product.return_value = Product("EL-1001", "Ноутбук", "шт", 5, id=1)
    repo.get_warehouse.side_effect = lambda wid: {1: Warehouse("Центральный", "Москва", 1),
                                                  2: Warehouse("Северный", "СПб", 2)}.get(wid)
    return repo


@pytest.fixture
def notifier():
    return MagicMock(name="notifier")


@pytest.fixture
def service(repo_mock, notifier):
    return InventoryService(repo_mock, notifier)


@pytest.fixture
def sqlite_repo(tmp_path):
    """Отдельная файловая SQLite-база для каждого интеграционного теста (setup/teardown)."""
    repo = SQLiteInventoryRepository(str(tmp_path / "test.db"))
    yield repo
    repo.close()


@pytest.fixture
def real_service(sqlite_repo, notifier):
    service = InventoryService(sqlite_repo, notifier)
    service.create_warehouse("Центральный", "Москва")
    service.create_warehouse("Северный", "Санкт-Петербург")
    service.create_product("EL-1001", "Ноутбук Lenovo", "шт", 5)
    service.create_product("OF-5001", "Бумага А4", "пачка", 50)
    return service
