import copy
import time
from datetime import date, datetime

import pytest
import redis

from exceptions import ItemNotFoundError, ValidationError
from mongodb import get_database
from seed import ITEMS


def test_mongodb_connection():
    assert get_database(name="warehouse_test").client.admin.command("ping")["ok"] == 1


def test_add_document(service):
    item = copy.deepcopy(ITEMS[0])
    item.sku = "NB-777"
    added = service.add_item(item)
    assert len(added.id) == 24 and service.repo.count() == 25


def test_duplicate_sku_rejected(service):
    with pytest.raises(ValidationError):
        service.add_item(copy.deepcopy(ITEMS[0]))


def test_get_document(service):
    item = service.repo.get_by_sku("SR-RS")
    assert item.supplier["city"] == "Тверь" and item.batches[0].batch_no == "D-0920"
    assert service.repo.get_by_id(item.id).sku == "SR-RS"


@pytest.mark.parametrize("bad_id", ["123", "zzzzzzzzzzzzzzzzzzzzzzzz", None])
def test_invalid_identifier(service, bad_id):
    with pytest.raises(ValidationError):
        service.repo.get_by_id(bad_id)


def test_update_document(service):
    item = service.update_item("PN-BL", price=30, min_stock=10)
    assert item.price == 30 and item.status == "in_stock"


def test_delete_document(service):
    service.delete_item("TB-120")
    with pytest.raises(ItemNotFoundError):
        service.repo.get_by_sku("TB-120")
    assert service.cache.stock("TB-120") is None


@pytest.mark.parametrize("kind, value, expected", [
    ("category", "мебель", {"CH-OF", "TB-120", "SH-05", "CB-WD"}),
    ("city", "Тверь", {"MLK-32", "KF-1", "TV-5", "SR-RS", "BT-82"}),
    ("tag", "хит", {"NB-001", "MN-027", "PP-A4", "CH-OF"}),
    ("price", "10000-20000", {"TB-120", "CB-WD"}),
])
def test_filters(service, kind, value, expected):
    assert {i.sku for i in service.search(kind, value)} == expected


def test_sort_and_limit(service):
    top = service.repo.top_expensive(3)
    assert [i.sku for i in top] == ["NB-001", "MN-027", "CB-WD"]
    expiring = service.repo.expiring_before(datetime(2026, 10, 25))
    assert [i.sku for i in expiring] == ["KF-1", "MLK-32"]


def test_aggregation(service):
    by_category = {r["_id"]: r for r in service.repo.stats_by_category()}
    assert by_category["мебель"]["units"] == 14
    months = {r["_id"]: r["units"] for r in service.repo.expiring_by_month()}
    assert months["2026-10"] == 120


def test_redis_write_and_read(service):
    service.cache.set_item("TEST", {"a": 1})
    assert service.cache.get_item("TEST") == {"a": 1}
    assert service.cache.stock("NB-001") == 12


def test_cache_aside(service):
    assert service.get_item("BT-82")[1] == "MongoDB"
    assert service.get_item("BT-82")[1] == "Redis"


def test_ttl(service):
    service.cache.ttl = 1
    service.get_item("ST-24")
    assert 0 < service.cache.ttl_of("ST-24") <= 1
    time.sleep(1.2)
    assert service.get_item("ST-24")[1] == "MongoDB"


def test_cache_invalidation(service):
    service.get_item("CH-OF")
    service.update_item("CH-OF", price=7990)
    data, source = service.get_item("CH-OF")
    assert source == "MongoDB" and data["price"] == 7990


def test_write_off_fefo(service):
    item = service.write_off("MLK-32", 40)
    assert [b.quantity for b in item.batches] == [0, 40]     # сначала партия с ранним сроком
    with pytest.raises(ValidationError):
        service.write_off("MLK-32", 1000)


def test_receive_batch_updates_stock_hash(service):
    service.receive_batch("MS-010", "P-1015", 20, None)
    assert service.stock_of("MS-010") == (23, "Redis")
    assert "MS-010" not in service.cache.low_skus()


def test_works_without_redis(service):
    service.cache.r = redis.Redis(port=6399, socket_timeout=0.2, socket_connect_timeout=0.2)
    data, source = service.get_item("NB-001")
    assert source == "MongoDB" and data["sku"] == "NB-001"
