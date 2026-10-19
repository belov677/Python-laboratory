"""Интеграционные тесты: Service → Repository → SQLite (без Mock репозитория)."""
import sqlite3
from unittest.mock import patch

import pytest

from src.models.entities import MovementType
from src.repositories.sqlite_repository import SQLiteInventoryRepository
from src.services.exceptions import InsufficientStockError
from src.services.inventory_service import InventoryService


def test_full_cycle_receive_transfer_write_off(real_service, sqlite_repo):
    real_service.receive(1, 1, 10)
    real_service.transfer(1, 1, 2, 4)
    real_service.write_off(1, 2, 1)
    assert sqlite_repo.balances(1) == {1: 6, 2: 3}
    assert [m.type for m in real_service.history(1)] == [
        MovementType.RECEIPT, MovementType.TRANSFER, MovementType.WRITE_OFF]


def test_negative_balance_is_never_stored(real_service, sqlite_repo):
    real_service.receive(2, 1, 3)
    with pytest.raises(InsufficientStockError):
        real_service.write_off(2, 1, 4)
    assert real_service.balance(2, 1) == 3
    with pytest.raises(sqlite3.IntegrityError):          # вторая линия защиты — CHECK в БД
        sqlite_repo.set_balance(2, 1, -1)


def test_transaction_rollback_on_failure(real_service, sqlite_repo):
    real_service.receive(1, 1, 5)
    with patch.object(sqlite_repo, "add_movement", side_effect=RuntimeError("диск заполнен")):
        with pytest.raises(RuntimeError):
            real_service.transfer(1, 1, 2, 2)
    assert sqlite_repo.balances(1) == {1: 5}              # частичное перемещение откатано


def test_data_persists_between_connections(tmp_path):
    path = str(tmp_path / "persist.db")
    service = InventoryService(SQLiteInventoryRepository(path))
    service.create_warehouse("Центральный", "Москва")
    service.create_product("BD-3001", "Цемент М500", "мешок", 100)
    service.receive(1, 1, 150)
    service.repo.close()
    reopened = InventoryService(SQLiteInventoryRepository(path))
    assert reopened.balance(1, 1) == 150
    reopened.repo.close()


def test_search_is_case_insensitive_for_cyrillic(real_service):
    assert [p.sku for p in real_service.search("ноутбук")] == ["EL-1001"]
    assert [p.sku for p in real_service.search("of-50")] == ["OF-5001"]
    assert real_service.search("холодильник") == []


def test_low_stock_notification_with_real_storage(real_service, notifier):
    real_service.receive(2, 1, 60)
    real_service.write_off(2, 1, 15)                      # 45 < 50
    notifier.notify_low_stock.assert_called_once()
    product, total = notifier.notify_low_stock.call_args.args
    assert (product.sku, total) == ("OF-5001", 45)
