from repository import ItemRepository
from tests.conftest import NEW


def test_create_and_get():
    repo = ItemRepository()
    item = repo.create(NEW)
    assert item.id == 1 and repo.get_by_id(1).sku == "KB-01"


def test_delete_returns_flag():
    repo = ItemRepository()
    repo.create(NEW)
    assert repo.delete(1) is True
    assert repo.delete(1) is False
