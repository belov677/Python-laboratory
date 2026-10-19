"""Подписчик Redis Pub/Sub: получает события item.created / item.updated / item.deleted."""
import json
import sys

import redis

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
r = redis.Redis.from_url("redis://localhost:6379/1", decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe("warehouse.events")
print("Подписка на канал warehouse.events", flush=True)
received = 0
for message in pubsub.listen():
    if message["type"] != "message":
        continue
    event = json.loads(message["data"])
    print(f"  событие {event['event']:13} товар {event['sku']}", flush=True)
    received += 1
    if limit and received >= limit:
        break
