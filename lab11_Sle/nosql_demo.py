"""Эксперимент с Redis (вариант A NoSQL): структуры данных и базовые операции."""
import json
import time

import redis

r = redis.Redis(decode_responses=True)
r.delete("demo:item:1", "demo:views", "demo:stock", "demo:recent", "demo:low")

print("=== String: SET / GET (документ товара в JSON) ===")
doc = {"id": 1, "sku": "NB-001", "name": "Ноутбук Lenovo", "category": "электроника",
       "quantity": 12, "suppliers": [{"name": "Lenovo Rus", "price": 48000},
                                     {"name": "ООО Периферия", "price": 49500}]}
print("SET demo:item:1 →", r.set("demo:item:1", json.dumps(doc, ensure_ascii=False)))
print("GET demo:item:1 →", json.loads(r.get("demo:item:1"))["suppliers"])

print("\n=== EXPIRE / TTL ===")
r.expire("demo:item:1", 2)
print("TTL сразу:", r.ttl("demo:item:1"), "c")
time.sleep(2.1)
print("GET после истечения TTL:", r.get("demo:item:1"))

print("\n=== INCR: счётчик запросов ===")
for _ in range(3):
    print("INCR demo:views →", r.incr("demo:views"))

print("\n=== Hash: остатки по артикулам ===")
r.hset("demo:stock", mapping={"NB-001": 12, "MS-010": 3, "PN-BL": 15})
r.hincrby("demo:stock", "MS-010", 20)
print("HGETALL demo:stock →", r.hgetall("demo:stock"))

print("\n=== List: последние запрошенные товары ===")
for sku in ("NB-001", "MS-010", "PP-A4", "NB-001"):
    r.lpush("demo:recent", sku)
r.ltrim("demo:recent", 0, 2)
print("LRANGE demo:recent →", r.lrange("demo:recent", 0, -1))

print("\n=== Sorted Set: дефицит (min_stock − quantity) ===")
r.zadd("demo:low", {"MS-010": 7, "PN-BL": 35, "TB-120": 1, "SP-500": 13})
print("ZREVRANGE demo:low →", r.zrevrange("demo:low", 0, -1, withscores=True))

print("\n=== DELETE ===")
print("DEL →", r.delete("demo:views", "demo:stock", "demo:recent", "demo:low"),
      "ключа удалено; EXISTS demo:stock →", r.exists("demo:stock"))
