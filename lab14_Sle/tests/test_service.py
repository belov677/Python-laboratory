import pytest

from cache import ItemCache
from exceptions import ConflictError, NotFoundError
from schemas.item import ItemCreate, ItemUpdate
from services.item import ItemService
from tests.conftest import NEW, TEST_SETTINGS


@pytest.fixture
def service(client):
    session = client.app.state.db.session_factory()
    yield ItemService(session, ItemCache(TEST_SETTINGS.redis_url, 60))
    session.close()


def test_service_create_and_conflict(service):
    item = service.create(ItemCreate(**NEW))
    assert item.id == 16
    with pytest.raises(ConflictError):
        service.create(ItemCreate(**NEW))


def test_service_update_missing(service):
    with pytest.raises(NotFoundError):
        service.update(999, ItemUpdate(quantity=1))


def test_repository_statistics(service):
    stats = service.statistics()
    assert stats["total_units"] == 321 and stats["average_price"] == 7286.2
