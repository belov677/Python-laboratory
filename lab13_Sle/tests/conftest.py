import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from cache import RedisCache  # noqa: E402
from mongodb import get_database  # noqa: E402
from redis_client import get_redis  # noqa: E402
from repository import MongoRepository  # noqa: E402
from seed import ITEMS  # noqa: E402
from service import WarehouseService  # noqa: E402


@pytest.fixture
def service():
    db = get_database(name="warehouse_test")
    repo = MongoRepository(db)
    repo.collection.drop()
    repo.create_indexes()
    redis_client = get_redis("redis://localhost:6379/14")
    redis_client.flushdb()
    svc = WarehouseService(repo, RedisCache(redis_client, 120))
    for item in ITEMS:
        svc.add_item(copy.deepcopy(item))
    return svc
