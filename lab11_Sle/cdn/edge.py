"""Локальная имитация CDN edge-сервера (кэширующий обратный прокси).

Клиент → edge (порт 8090) → [кэш в памяти] → origin (Flask API, порт 5000, /static/...).
Задержка ORIGIN_LATENCY имитирует удалённость origin-сервера от пользователя.
"""
from __future__ import annotations

import os
import re
import time

import requests
from flask import Flask, Response

ORIGIN = os.getenv("ORIGIN", "http://127.0.0.1:5000")
ORIGIN_LATENCY = float(os.getenv("ORIGIN_LATENCY", "0.08"))   # 80 мс «до origin»
app = Flask(__name__, static_folder=None)   # только проксирование, без локальной статики
cache: dict[str, tuple[float, int, bytes, dict]] = {}       # path → (время, max_age, тело, заголовки)


def max_age(headers: dict) -> int:
    match = re.search(r"max-age=(\d+)", headers.get("Cache-Control", ""))
    return int(match.group(1)) if match else 0


@app.get("/static/<path:name>")
def edge(name: str):
    path = f"/static/{name}"
    now = time.time()
    entry = cache.get(path)
    if entry and now - entry[0] < entry[1]:
        stored, ttl, body, headers = entry
        return Response(body, headers={**headers, "Age": str(int(now - stored)),
                                       "X-Cache": "HIT", "X-Edge": "edge-msk-1"})
    time.sleep(ORIGIN_LATENCY)
    origin = requests.get(ORIGIN + path, timeout=5)
    keep = {k: v for k, v in origin.headers.items()
            if k in ("Content-Type", "Cache-Control", "ETag", "Last-Modified")}
    if origin.status_code == 200 and max_age(keep) > 0:
        cache[path] = (now, max_age(keep), origin.content, keep)
    return Response(origin.content, status=origin.status_code,
                    headers={**keep, "Age": "0", "X-Cache": "MISS", "X-Edge": "edge-msk-1"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 8090)))
