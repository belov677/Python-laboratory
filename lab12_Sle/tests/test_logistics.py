from decimal import Decimal

import pytest

from models import Shipment, ShipmentStatus
from repositories.repositories import ShipmentRepository
from services.exceptions import (DuplicateError, InvalidStatusError, NotFoundError,
                                 ValidationError)


def test_create_and_get_client(service):
    client = service.create_client("ООО Ромашка", "info@romashka.ru", "Тверь")
    assert service.get_client(client.id).email == "info@romashka.ru"


def test_duplicate_email(service):
    with pytest.raises(DuplicateError):
        service.create_client("Копия", "smirnova@mail.ru", "Казань")


@pytest.mark.parametrize("email", ["без-собаки", "a@b", "@mail.ru"])
def test_invalid_email(service, email):
    with pytest.raises(ValidationError):
        service.create_client("Тест", email, "Тула")


def test_update_and_delete_client(service):
    assert service.update_client(5, city="Тула").city == "Тула"
    service.delete_client(5)
    with pytest.raises(NotFoundError):
        service.get_client(5)


def test_search_and_sort(service):
    assert {c.name for c in service.search_clients("москва")} == {"ООО «ТехноМир»", "Пётр Иванов"}
    assert [c.city for c in service.list_clients("city")][:2] == ["Екатеринбург", "Казань"]


def test_shipment_cost_calculation(service):
    shipment = service.create_shipment(5, "Москва", "Владимир", 190, [2, 7])
    # 500 + (60 + 90) * 190 * 0.02 = 1070
    assert shipment.cost == Decimal("1070.00")
    assert shipment.tracking_number == "LG-2026-0006"


def test_related_objects(service):
    shipments = service.client_shipments(1)
    assert [s.destination for s in shipments] == ["Санкт-Петербург", "Казань"]
    assert len(shipments[1].cargos) == 2


def test_transaction_rollback_on_missing_cargo(service):
    before = service.statistics()["count"]
    with pytest.raises(NotFoundError):
        service.create_shipment(1, "Москва", "Тула", 180, [1, 999])
    assert service.statistics()["count"] == before


def test_status_transitions(service):
    shipment = service.change_status("LG-2026-0002", ShipmentStatus.DELIVERED, "Пермь")
    assert shipment.delivered_at is not None
    with pytest.raises(InvalidStatusError):
        service.change_status("LG-2026-0003", ShipmentStatus.IN_TRANSIT, "Краснодар")


def test_tracking_events_order(service):
    events = service.track("LG-2026-0001").events
    assert [e.status for e in events] == [ShipmentStatus.CREATED, ShipmentStatus.IN_TRANSIT,
                                          ShipmentStatus.DELIVERED]


def test_filter_multiple_conditions(service):
    found = service.filter_shipments(city="Москва", min_cost=1000, sort="cost", descending=True)
    assert [s.tracking_number for s in found] == ["LG-2026-0003", "LG-2026-0004", "LG-2026-0001"]


def test_foreign_key_violation(service):
    with pytest.raises(ValidationError):
        with service.transaction() as session:
            ShipmentRepository(session).create(tracking_number="X-1", client_id=999,
                                                origin="A", destination="B", distance_km=1)


def test_aggregates_and_pagination(service):
    stats = service.statistics()
    assert stats["count"] == 5 and stats["max"] == Decimal("12650.00")
    assert len(service.list_clients("id", page=2, page_size=3)) == 2
