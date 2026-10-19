from datetime import date

import pytest

from infrastructure.container import Container
from models.entities import InsufficientStockError, PerishableProduct, Product, ProductNotFoundError
from models.enums import OperationType
from operations.stock_operations import Inventory, Receipt, ReturnToSupplier, Transfer, WriteOff
from repositories.json_repository import JsonFileStockRepository
from repositories.memory_repository import InMemoryStockRepository
from services.report_service import ReportGenerator
from services.stock_service import StockService


class FakeNotifier:
    """Тестовая заглушка: запоминает сообщения вместо отправки."""

    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)


@pytest.fixture(params=["memory", "json"])
def repository(request, tmp_path):
    """Одни и те же тесты выполняются для обеих реализаций (проверка LSP)."""
    if request.param == "memory":
        return InMemoryStockRepository()
    return JsonFileStockRepository(tmp_path / "stock.json")


@pytest.fixture
def service(repository):
    service = StockService(repository, FakeNotifier())
    service.register_product(Product("NB-001", "Ноутбук", 50000))
    service.register_product(PerishableProduct("MLK-1", "Молоко", 90, date(2026, 10, 20)))
    service.execute(Receipt("A", "NB-001", 10))
    return service


def test_receipt_increases_stock(service):
    service.execute(Receipt("A", "NB-001", 5))
    assert service.repository.get_quantity("A", "NB-001") == 15


def test_receipt_of_unknown_product_fails(service):
    with pytest.raises(ProductNotFoundError):
        service.execute(Receipt("A", "XXX", 1))


def test_write_off_more_than_stock_fails(service):
    with pytest.raises(InsufficientStockError):
        service.execute(WriteOff("A", "NB-001", 11))
    assert service.repository.get_quantity("A", "NB-001") == 10


def test_transfer_moves_between_warehouses(service):
    service.execute(Transfer("A", "B", "NB-001", 4))
    assert service.repository.get_quantity("A", "NB-001") == 6
    assert service.repository.get_quantity("B", "NB-001") == 4
    assert service.total_quantity("NB-001") == 10


def test_inventory_records_difference(service):
    result = service.execute(Inventory("A", "NB-001", 8))
    assert result.changes == {"A": -2}
    assert service.repository.get_quantity("A", "NB-001") == 8


def test_notifier_receives_message(service):
    assert service.notifier.messages[-1].startswith("поступление: NB-001")


def test_new_operation_without_changing_service(service):
    result = service.execute(ReturnToSupplier("A", "NB-001", 3))
    assert result.operation is OperationType.RETURN
    assert service.repository.get_quantity("A", "NB-001") == 7


def test_report_uses_only_read_interface(service):
    report = ReportGenerator(service.repository, service.repository)
    assert report.total_value() == 10 * 50000
    assert report.expiring(date(2026, 10, 15), 10) == ["MLK-1 Молоко: осталось 5 дн."]


@pytest.mark.parametrize("quantity", [0, -5])
def test_non_positive_quantity_rejected(service, quantity):
    with pytest.raises(ValueError):
        service.execute(Receipt("A", "NB-001", quantity))


def test_json_repository_persists(tmp_path):
    path = tmp_path / "s.json"
    first = JsonFileStockRepository(path)
    first.add_product(Product("X", "Товар", 10))
    first.set_quantity("A", "X", 7)
    second = JsonFileStockRepository(path)
    assert second.get_quantity("A", "X") == 7
    assert second.get_product("X").name == "Товар"


def test_container_resolves_registered_dependency():
    container = Container()
    container.register(FakeNotifier, lambda c: FakeNotifier())
    assert container.resolve(FakeNotifier) is container.resolve(FakeNotifier)
    with pytest.raises(KeyError):
        container.resolve(StockService)
