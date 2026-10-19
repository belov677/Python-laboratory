"""Демонстрационный сценарий итогового проекта (система запущена: docker compose up -d).

Каждый шаг сохраняется в demo_output/<шаг>.txt для отчёта.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).parent
OUT = ROOT / "demo_output"
API = httpx.Client(base_url=os.getenv("BASE_URL", "http://localhost:8000"), timeout=30)
ENV = {
    k: v
    for k, v in (
        line.split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
}
buffer: list[str] = []


def out(text: str = "") -> None:
    print(text)
    buffer.append(text)


def save(name: str) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.txt").write_text("\n".join(buffer), encoding="utf-8")
    buffer.clear()


def call(method, path, body=None, headers=None, show=True, limit=420, **kw):
    started = time.perf_counter()
    response = API.request(method, path, json=body, headers=headers, **kw)
    ms = (time.perf_counter() - started) * 1000
    if show:
        auth = " [JWT " + ("ADMIN" if headers is ADMIN else "USER") + "]" if headers else ""
        out(f"$ {method} {path}{auth}" + (f"  {json.dumps(body, ensure_ascii=False)}" if body else ""))
        text = response.text if response.text else "(пусто)"
        try:
            text = json.dumps(response.json(), ensure_ascii=False)
        except ValueError:
            pass
        cache = f" X-Cache={response.headers['X-Cache']}" if "X-Cache" in response.headers else ""
        out(f"  → {response.status_code}{cache} за {ms:.0f} мс: {text[:limit]}{' …' if len(text) > limit else ''}")
    return response


def compose(*args):
    env = dict(os.environ, COMPOSE_FILE=os.getenv("COMPOSE_FILE", "docker-compose.yml"))
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, capture_output=True, env=env)
    out(f"$ docker compose {' '.join(args)}")


def logs(service: str, grep: str, tail: int = 200, last: int = 8) -> None:
    env = dict(os.environ, COMPOSE_FILE=os.getenv("COMPOSE_FILE", "docker-compose.yml"))
    text = subprocess.run(
        ["docker", "compose", "logs", "--no-log-prefix", "--tail", str(tail), service],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    ).stdout
    lines = [line for line in text.splitlines() if any(g in line for g in grep.split("|"))][-last:]
    out(f"  ── журнал {service} ──")
    for line in lines:
        out("  " + line[11:])


pickup = (datetime.now(UTC) + timedelta(days=2)).replace(hour=6, minute=0, second=0, microsecond=0)
ORDER = {
    "origin": "Москва",
    "destination": "Санкт-Петербург",
    "cargo": "Серверное оборудование, 6 стоек",
    "weight_kg": 4200,
    "pickup_at": pickup.isoformat(),
    "deadline_at": (pickup + timedelta(days=1)).isoformat(),
}

# 1. Регистрация и авторизация
out("=== 1. Регистрация и авторизация (JWT, роли USER и ADMIN) ===")
call("POST", "/auth/register", {"email": "client@example.com", "password": "Client2026", "full_name": "ООО «ТехноМир»"})
call("POST", "/auth/register", {"email": "client@example.com", "password": "Client2026", "full_name": "Дубль"})
call("POST", "/auth/login", {"email": "client@example.com", "password": "неверный1"})
token = call("POST", "/auth/login", {"email": "client@example.com", "password": "Client2026"}).json()["access_token"]
USER = {"Authorization": f"Bearer {token}"}
admin_token = API.post("/auth/login", json={"email": ENV["ADMIN_EMAIL"], "password": ENV["ADMIN_PASSWORD"]}).json()
ADMIN = {"Authorization": f"Bearer {admin_token['access_token']}"}
out(f"$ POST /auth/login  (диспетчер {ENV['ADMIN_EMAIL']}) → роль {admin_token['role']}")
call("GET", "/auth/me", headers=USER)
call("GET", "/orders")
call("GET", "/vehicles", headers=USER)
save("1_auth")

# 2. Каталог маршрутов и кэш
out("=== 2. Каталог маршрутов: cache miss → cache hit (Redis) ===")
API.post(
    "/routes",
    headers=ADMIN,
    json={"code": "R-999", "origin": "Тест", "destination": "Тест-2", "distance_km": 1, "duration_h": 1},
)  # сброс кэша
API.delete(f"/routes/{API.get('/routes', headers=ADMIN).json()[-1]['id']}", headers=ADMIN)
for _ in range(3):
    call("GET", "/routes", headers=USER, limit=160)
call("GET", "/routes?origin=Москва", headers=USER, limit=160)
call("GET", "/routes?origin=Москва", headers=USER, limit=160)
save("2_cache")

# 3. Заказ и бизнес-правила
out("=== 3. Создание заказа и бизнес-правила ===")
call("POST", "/orders", {**ORDER, "destination": "Владивосток"}, headers=USER)
call("POST", "/orders", {**ORDER, "deadline_at": (pickup + timedelta(hours=5)).isoformat()}, headers=USER)
call("POST", "/orders", {**ORDER, "weight_kg": 0, "deadline_at": ORDER["pickup_at"]}, headers=USER)
order = call("POST", "/orders", ORDER, headers=USER).json()
call("GET", "/orders?status=NEW&sort=-created_at&page=1&size=5", headers=USER, limit=200)
save("3_order")

# 4. Подбор ресурсов и назначение рейса (проверка нескольких сущностей)
out("=== 4. Подбор транспорта и водителя, назначение рейса ===")
options = call("GET", f"/deliveries/available?order_id={order['id']}", headers=ADMIN, limit=900).json()
call("POST", "/deliveries", {"order_id": order["id"], "vehicle_id": 1, "driver_id": 2}, headers=ADMIN)
call("POST", "/deliveries", {"order_id": order["id"], "vehicle_id": 4, "driver_id": 1}, headers=ADMIN)
delivery = call(
    "POST", "/deliveries", {"order_id": order["id"], "vehicle_id": 4, "driver_id": 2}, headers=ADMIN, limit=330
).json()
second = call("POST", "/orders", {**ORDER, "cargo": "Мебель", "weight_kg": 900}, headers=USER).json()
call("POST", "/deliveries", {"order_id": second["id"], "vehicle_id": 4, "driver_id": 3}, headers=ADMIN)
save("4_delivery")

# 5. Выполнение рейса, отслеживание и уведомления (worker)
out("=== 5. Выполнение рейса, отслеживание, уведомления от worker ===")
call("PATCH", f"/deliveries/{delivery['id']}/status", {"action": "complete"}, headers=ADMIN)
call("PATCH", f"/deliveries/{delivery['id']}/status", {"action": "start"}, headers=ADMIN, limit=120)
call("GET", f"/orders/{order['id']}/tracking", headers=USER, limit=600)
call("PATCH", f"/deliveries/{delivery['id']}/status", {"action": "complete"}, headers=ADMIN, limit=120)
call("DELETE", f"/orders/{order['id']}", headers=USER)
time.sleep(4)
response = API.get("/auth/me/notifications", headers=USER).json()
out("$ GET /auth/me/notifications [JWT USER]")
for n in reversed(response):
    out(f"  • {n['text']}")
logs("worker", "уведомление")
save("5_tracking")

# 6. Права доступа
out("=== 6. Разграничение доступа ===")
API.post("/auth/register", json={"email": "other@example.com", "password": "Other2026", "full_name": "ИП Другой"})
other = {
    "Authorization": "Bearer "
    + API.post("/auth/login", json={"email": "other@example.com", "password": "Other2026"}).json()["access_token"]
}
r = API.get(f"/orders/{second['id']}", headers=other)
out(f"$ GET /orders/{second['id']} [JWT другого клиента]\n  → {r.status_code}: {r.text}")
r = API.get("/orders", headers=other)
out(f"$ GET /orders [JWT другого клиента]\n  → {r.status_code}: total={r.json()['total']}")
call("GET", "/orders?size=1", headers=ADMIN, limit=120)
call(
    "POST",
    "/routes",
    {"code": "R-300", "origin": "Тула", "destination": "Орёл", "distance_km": 180, "duration_h": 2.5},
    headers=USER,
)
call("GET", "/orders/99999", headers=ADMIN)
save("6_access")

# 7. Отказ Redis
out("=== 7. Отказоустойчивость: недоступен Redis ===")
compose("stop", "redis")
call("GET", "/routes", headers=USER, limit=120)
call("GET", "/routes", headers=USER, limit=120)
call("GET", "/health")
compose("start", "redis")
time.sleep(16)  # recovery_timeout кэша
call("GET", "/routes", headers=USER, limit=120)
call("GET", "/routes", headers=USER, limit=120)
call("GET", "/health")
logs("app", "Redis")
save("7_redis")

# 8. Отказ брокера
out("=== 8. Отказоустойчивость: недоступен RabbitMQ (Transactional Outbox) ===")
compose("stop", "rabbitmq")
third = call("POST", "/orders", {**ORDER, "cargo": "Стройматериалы", "weight_kg": 300}, headers=USER).json()
call("GET", "/health")
time.sleep(3)
logs("app", "не опубликовано", last=2)
compose("start", "rabbitmq")
time.sleep(25)
notes = [n["text"] for n in API.get("/auth/me/notifications", headers=USER).json()]
out(f"$ GET /auth/me/notifications → последнее: {notes[0]}")
call("GET", "/health")
logs("app", "опубликовано: OrderCreated", last=1)
logs("worker", "уведомление", last=1)
save("8_broker")

out("=== 9. Метрики ===")
call("GET", "/metrics", limit=1500)
save("9_metrics")
