"""Сравнение повторяющегося чтения: PostgreSQL vs Redis (100 / 1000 / 10000 запросов)."""
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psycopg
import redis
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).parent / "app"))
from config import DATABASE_URL  # noqa: E402
from repository import ITEM_SELECT  # noqa: E402

counts = [100, 1000, 10000]
r = redis.Redis(decode_responses=True)
results = {"PostgreSQL": [], "Redis": []}
with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
    item = conn.execute(f"{ITEM_SELECT} WHERE i.id = %s", (1,)).fetchone()
    r.set("bench:item:1", json.dumps(item, ensure_ascii=False))
    for n in counts:
        start = time.perf_counter()
        for _ in range(n):
            conn.execute(f"{ITEM_SELECT} WHERE i.id = %s", (1,)).fetchone()
        results["PostgreSQL"].append(time.perf_counter() - start)
        start = time.perf_counter()
        for _ in range(n):
            json.loads(r.get("bench:item:1"))
        results["Redis"].append(time.perf_counter() - start)
r.delete("bench:item:1")

print(f"{'запросов':>9} | {'PostgreSQL, с':>14} | {'на запрос, мс':>13} | {'Redis, с':>9} | {'на запрос, мс':>13}")
for i, n in enumerate(counts):
    pg, rd = results["PostgreSQL"][i], results["Redis"][i]
    print(f"{n:>9} | {pg:14.4f} | {pg / n * 1000:13.4f} | {rd:9.4f} | {rd / n * 1000:13.4f}")

plt.figure(figsize=(7, 4.2))
for name, marker in (("PostgreSQL", "o"), ("Redis", "s")):
    plt.plot(counts, results[name], marker=marker, label=name)
plt.xscale("log"); plt.yscale("log")
plt.xlabel("Количество запросов"); plt.ylabel("Общее время, с")
plt.title("Повторное чтение товара по id"); plt.grid(True, which="both", alpha=0.3)
plt.legend(); plt.tight_layout()
plt.savefig(Path(__file__).parent / "screenshots" / "benchmark_chart.png", dpi=120)
print("График сохранён: screenshots/benchmark_chart.png")
