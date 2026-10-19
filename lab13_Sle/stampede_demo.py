"""Защита от cache stampede: 30 потоков одновременно запрашивают отсутствующий в Redis товар."""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))
from cache import RedisCache  # noqa: E402
from mongodb import get_database  # noqa: E402
from redis_client import get_redis  # noqa: E402
from repository import MongoRepository  # noqa: E402
from service import WarehouseService  # noqa: E402


class CountingRepository(MongoRepository):
    loads = 0

    def get_by_sku(self, sku):
        CountingRepository.loads += 1
        return super().get_by_sku(sku)


def run(with_lock: bool) -> int:
    CountingRepository.loads = 0
    cache = RedisCache(get_redis(), 120)
    cache.invalidate("NB-001")
    service = WarehouseService(CountingRepository(get_database()), cache)
    barrier = threading.Barrier(30)

    def worker():
        barrier.wait()
        if with_lock:
            service.get_item("NB-001")
        else:                                   # наивный cache-aside без блокировки
            if cache.get_item("NB-001") is None:
                cache.set_item("NB-001", service.repo.get_by_sku("NB-001").to_public())

    threads = [threading.Thread(target=worker) for _ in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return CountingRepository.loads


print("30 одновременных запросов отсутствующего в кэше товара NB-001")
print(f"  без блокировки: обращений к MongoDB = {run(False)}")
print(f"  с Redis lock (SET NX EX): обращений к MongoDB = {run(True)}")
