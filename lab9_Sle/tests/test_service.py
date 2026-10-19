import pytest

from exceptions import MedicineNotFoundError, ValidationError
from repository import MedicineRepository
from service import PharmacyService


@pytest.fixture
def service():
    s = PharmacyService(MedicineRepository())
    s.create_medicine(dict(name="Нурофен", category="обезболивающие", manufacturer="R",
                           price=320.0, quantity=5))
    s.create_medicine(dict(name="Парацетамол", category="обезболивающие", manufacturer="Ф",
                           price=45.0, quantity=50))
    s.create_medicine(dict(name="Компливит", category="витамины", manufacturer="О",
                           price=290.0, quantity=0))
    return s


def test_find_object(service):
    assert service.get_medicine(2).name == "Парацетамол"


def test_search_by_category_sorted_by_price(service):
    names = [m.name for m in service.search_by_category("обезболивающие")]
    assert names == ["Парацетамол", "Нурофен"]


@pytest.mark.parametrize("data", [
    dict(name="", category="витамины", manufacturer="X", price=10, quantity=1),
    dict(name="A", category="космос", manufacturer="X", price=10, quantity=1),
    dict(name="A", category="витамины", manufacturer="X", price=0, quantity=1),
    dict(name="A", category="витамины", manufacturer="X", price=10, quantity=-1),
    dict(name="A", category="витамины", price=10, quantity=1),
])
def test_invalid_object(service, data):
    with pytest.raises(ValidationError):
        service.create_medicine(data)


@pytest.mark.parametrize("bad_id", [0, -1, "5", None, True])
def test_invalid_id(service, bad_id):
    with pytest.raises(ValidationError):
        service.get_medicine(bad_id)


def test_missing_object(service):
    with pytest.raises(MedicineNotFoundError):
        service.delete_medicine(99)


def test_statistics(service):
    assert service.statistics() == {"medicines": 3, "units": 55, "out_of_stock": 1,
                                    "categories": 2}
