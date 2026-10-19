import pytest

from exceptions import ConflictError, ItemNotFoundError, ValidationError
from repository import ItemRepository
from service import ItemService
from tests.conftest import NEW


@pytest.fixture
def service():
    s = ItemService(ItemRepository())
    s.create_item(NEW)
    s.create_item({**NEW, "sku": "MS-02", "name": "Мышь", "quantity": 2, "min_stock": 10})
    return s


def test_low_stock_returns_only_items_below_min(service):
    assert [i.sku for i in service.low_stock()] == ["MS-02"]


def test_duplicate_sku_conflict(service):
    with pytest.raises(ConflictError):
        service.create_item(NEW)


@pytest.mark.parametrize("bad", [
    {**NEW, "price": -1}, {**NEW, "quantity": -5}, {**NEW, "name": "  "},
    {**NEW, "quantity": "много"}, {k: v for k, v in NEW.items() if k != "sku"},
    {**NEW, "color": "red"}, [1, 2, 3]])
def test_validation(service, bad):
    with pytest.raises(ValidationError):
        service.create_item(bad)


def test_patch_keeps_other_fields(service):
    item = service.patch_item(1, {"quantity": 1})
    assert item.quantity == 1 and item.name == "Клавиатура"


def test_get_missing(service):
    with pytest.raises(ItemNotFoundError):
        service.get_item(42)
