"""Unit-тесты сервиса: репозиторий и уведомления заменены Mock-объектами."""
from datetime import datetime
from unittest.mock import ANY, call, patch

import pytest

from src.models.entities import Movement, MovementType, Product
from src.services.exceptions import (DuplicateError, InsufficientStockError, NotFoundError,
                                     ValidationError)


def test_create_product_with_valid_data(service, repo_mock):
    # Arrange
    repo_mock.get_product_by_sku.return_value = None
    repo_mock.add_product.side_effect = lambda p: Product(p.sku, p.name, p.unit, p.min_stock, id=7)
    # Act
    product = service.create_product(" el-2001 ", " Мышь ", min_stock=10)
    # Assert
    assert (product.id, product.sku, product.name) == (7, "EL-2001", "Мышь")
    repo_mock.get_product_by_sku.assert_called_once_with("EL-2001")
    repo_mock.add_product.assert_called_once_with(Product("EL-2001", "Мышь", "шт", 10))


def test_create_product_twice_raises_duplicate(service, repo_mock):
    repo_mock.get_product_by_sku.return_value = Product("EL-1001", "Ноутбук", id=1)
    with pytest.raises(DuplicateError, match="уже существует"):
        service.create_product("EL-1001", "Ноутбук")
    repo_mock.add_product.assert_not_called()


def test_get_missing_product_raises_not_found(service, repo_mock):
    repo_mock.get_product.return_value = None
    with pytest.raises(NotFoundError, match="id=42"):
        service.get_product(42)
    repo_mock.get_product.assert_called_once_with(42)


def test_receive_increases_balance(service, repo_mock):
    repo_mock.get_balance.return_value = 3
    assert service.receive(1, 2, 10, "поставка №5") == 13
    repo_mock.set_balance.assert_called_once_with(1, 2, 13)
    movement = repo_mock.add_movement.call_args.args[0]
    assert (movement.type, movement.quantity, movement.target_id, movement.source_id) == \
        (MovementType.RECEIPT, 10, 2, None)


def test_receive_to_missing_warehouse(service, repo_mock):
    with pytest.raises(NotFoundError, match="Склад с id=99"):
        service.receive(1, 99, 5)
    repo_mock.set_balance.assert_not_called()


def test_write_off_whole_balance_reaches_zero(service, repo_mock):
    repo_mock.get_balance.return_value = 5
    repo_mock.balances.return_value = {1: 0, 2: 10}
    assert service.write_off(1, 1, 5) == 0               # граница: остаток ровно 0
    repo_mock.set_balance.assert_called_once_with(1, 1, 0)


def test_write_off_more_than_balance_is_rejected(service, repo_mock):
    repo_mock.get_balance.return_value = 4
    with pytest.raises(InsufficientStockError, match="остаток 4, требуется 5"):
        service.write_off(1, 1, 5)                       # граница: на 1 больше остатка
    repo_mock.set_balance.assert_not_called()
    repo_mock.add_movement.assert_not_called()


def test_write_off_below_minimum_notifies(service, repo_mock, notifier):
    repo_mock.get_balance.return_value = 6
    repo_mock.balances.return_value = {1: 2, 2: 2}       # после списания всего 4 < min 5
    service.write_off(1, 1, 4)
    notifier.notify_low_stock.assert_called_once_with(repo_mock.get_product.return_value, 4)


def test_write_off_above_minimum_does_not_notify(service, repo_mock, notifier):
    repo_mock.get_balance.return_value = 10
    repo_mock.balances.return_value = {1: 5}             # 5 == min 5 — ещё не критично
    service.write_off(1, 1, 5)
    notifier.notify_low_stock.assert_not_called()


def test_transfer_moves_quantity_between_warehouses(service, repo_mock):
    repo_mock.get_balance.side_effect = lambda product_id, warehouse_id: {1: 8, 2: 1}[warehouse_id]
    assert service.transfer(1, 1, 2, 3) == (5, 4)
    assert repo_mock.set_balance.call_args_list == [call(1, 1, 5), call(1, 2, 4)]
    repo_mock.add_movement.assert_called_once_with(ANY)
    assert repo_mock.add_movement.call_args.args[0].type is MovementType.TRANSFER


def test_transfer_to_same_warehouse_is_invalid(service, repo_mock):
    with pytest.raises(ValidationError, match="должны различаться"):
        service.transfer(1, 1, 1, 3)
    repo_mock.get_product.assert_not_called()           # проверка до обращения к хранилищу


def test_transfer_more_than_available(service, repo_mock):
    repo_mock.get_balance.return_value = 2
    with pytest.raises(InsufficientStockError, match="для перемещения"):
        service.transfer(1, 1, 2, 3)
    repo_mock.set_balance.assert_not_called()


def test_search_strips_query_and_calls_repository(service, repo_mock):
    repo_mock.search_products.return_value = []
    assert service.search("  ноут ") == []               # пустой список результатов
    repo_mock.search_products.assert_called_once_with("ноут")


@pytest.mark.parametrize("query", ["", "   ", None])
def test_search_with_empty_query(service, repo_mock, query):
    with pytest.raises(ValidationError, match="не может быть пустым"):
        service.search(query)
    repo_mock.search_products.assert_not_called()


def test_low_stock_with_empty_list_returns_empty(service, repo_mock):
    assert service.low_stock([]) == []
    repo_mock.get_product.assert_not_called()


def test_delete_product_with_stock_is_forbidden(service, repo_mock):
    repo_mock.balances.return_value = {1: 1}
    with pytest.raises(InsufficientStockError, match="Нельзя удалить"):
        service.delete_product(1)
    repo_mock.delete_product.assert_not_called()


def test_movement_time_is_taken_from_clock(service, repo_mock):
    fixed = datetime(2026, 10, 1, 9, 30)
    repo_mock.get_balance.return_value = 0
    with patch("src.services.inventory_service.datetime") as clock:
        clock.now.return_value = fixed
        service.receive(1, 1, 1)
    movement: Movement = repo_mock.add_movement.call_args.args[0]
    assert movement.created_at == fixed
    clock.now.assert_called_once_with()


def test_delete_product_without_stock(service, repo_mock):
    repo_mock.balances.return_value = {}
    service.delete_product(1)
    repo_mock.delete_product.assert_called_once_with(1)


def test_low_stock_returns_only_critical_products(service, repo_mock):
    products = {1: Product("EL-1001", "Ноутбук", min_stock=5, id=1),
                2: Product("OF-5001", "Бумага", min_stock=50, id=2)}
    repo_mock.get_product.side_effect = products.get
    repo_mock.balances.side_effect = lambda pid: {1: {1: 10}, 2: {1: 49}}[pid]
    assert service.low_stock([1, 2]) == [products[2]]


@pytest.mark.parametrize("name, city", [("", "Москва"), ("Склад", "  ")])
def test_create_warehouse_requires_name_and_city(service, repo_mock, name, city):
    with pytest.raises(ValidationError):
        service.create_warehouse(name, city)
    repo_mock.add_warehouse.assert_not_called()


def test_low_stock_excludes_product_exactly_at_minimum(service, repo_mock):
    repo_mock.balances.return_value = {1: 5}            # остаток == минимум 5 — не критично
    assert service.low_stock([1]) == []


def test_transfer_entire_available_quantity(service, repo_mock):
    repo_mock.get_balance.side_effect = lambda product_id, warehouse_id: {1: 3, 2: 0}[warehouse_id]
    assert service.transfer(1, 1, 2, 3) == (0, 3)       # граница: перемещается весь остаток
