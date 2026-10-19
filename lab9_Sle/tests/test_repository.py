import pytest

from exceptions import MedicineNotFoundError, ValidationError
from repository import MedicineRepository

DATA = dict(name="Нурофен", category="обезболивающие", manufacturer="Reckitt",
            price=320.0, quantity=10)


def test_add_object_assigns_id():
    repo = MedicineRepository()
    first, second = repo.add(DATA), repo.add(DATA)
    assert (first.id, second.id) == (1, 2)
    assert len(repo.get_all()) == 2


def test_delete_object():
    repo = MedicineRepository()
    repo.add(DATA)
    repo.delete(1)
    with pytest.raises(MedicineNotFoundError):
        repo.get(1)


def test_update_revalidates():
    repo = MedicineRepository()
    repo.add(DATA)
    with pytest.raises(ValidationError):
        repo.update(1, {"price": -5})
    assert repo.get(1).price == 320.0
