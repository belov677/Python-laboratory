"""Unit-тесты проверок входных данных (параметризация, граничные значения)."""
import pytest

from src.services.exceptions import ValidationError
from src.services.inventory_service import MAX_QUANTITY, InventoryService


@pytest.mark.parametrize("quantity", [1, 2, 500, MAX_QUANTITY - 1, MAX_QUANTITY])
def test_validate_quantity_accepts_values_in_range(quantity):
    assert InventoryService.validate_quantity(quantity) == quantity


@pytest.mark.parametrize("quantity, message", [
    (0, "не меньше 1"),                       # граница снизу
    (-5, "не меньше 1"),
    (MAX_QUANTITY + 1, "не может превышать"),  # за пределами диапазона
    (2.5, "целым числом"),
    ("10", "целым числом"),
    (None, "целым числом"),
    (True, "целым числом"),                    # bool — подкласс int, но не количество
])
def test_validate_quantity_rejects_invalid_values(quantity, message):
    with pytest.raises(ValidationError, match=message):
        InventoryService.validate_quantity(quantity)


@pytest.mark.parametrize("value, valid", [(1, True), (999, True), (0, False), (-1, False),
                                          ("1", False), (None, False)])
def test_validate_id(value, valid):
    if valid:
        assert InventoryService.validate_id(value, "товара") == value
    else:
        with pytest.raises(ValidationError, match="Некорректный идентификатор"):
            InventoryService.validate_id(value, "товара")


@pytest.mark.parametrize("sku, name, min_stock", [
    ("", "Ноутбук", 0),            # пустая строка
    ("EL1001", "Ноутбук", 0),      # нет дефиса
    ("E-1001", "Ноутбук", 0),      # одна буква
    ("EL-1001", "   ", 0),         # пустое название
    ("EL-1001", "Ноутбук", -1),    # отрицательный минимум
])
def test_create_product_with_invalid_data(service, repo_mock, sku, name, min_stock):
    with pytest.raises(ValidationError):
        service.create_product(sku, name, min_stock=min_stock)
    repo_mock.add_product.assert_not_called()


def test_quantity_limit_is_exactly_ten_thousand():
    """Требование задано числом: тест не должен зависеть от константы, которую проверяет."""
    assert InventoryService.validate_quantity(10_000) == 10_000
    with pytest.raises(ValidationError):
        InventoryService.validate_quantity(10_001)


def test_create_product_default_min_stock_is_zero(service, repo_mock):
    repo_mock.get_product_by_sku.return_value = None
    repo_mock.add_product.side_effect = lambda p: p
    assert service.create_product("EL-3001", "Кабель").min_stock == 0
