"""Smoke-тест развёрнутой системы (CI, после docker compose up): python scripts/smoke_test.py"""

import os
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx

BASE = os.getenv("BASE_URL", "http://localhost:8000")


def main() -> int:
    api = httpx.Client(base_url=BASE, timeout=10)
    for _ in range(30):
        try:
            if api.get("/health").json()["status"] == "healthy":
                break
        except httpx.HTTPError:
            pass
        time.sleep(2)
    else:
        print("система не стала healthy")
        return 1
    email = f"smoke-{uuid.uuid4().hex[:6]}@example.com"
    assert (
        api.post(
            "/auth/register", json={"email": email, "password": "Smoke2026", "full_name": "Smoke Test"}
        ).status_code
        == 201
    )
    token = api.post("/auth/login", json={"email": email, "password": "Smoke2026"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert api.get("/routes", headers=headers).headers["X-Cache"] in ("MISS", "HIT")
    pickup = datetime.now(UTC) + timedelta(days=3)
    order = api.post(
        "/orders",
        headers=headers,
        json={
            "origin": "Казань",
            "destination": "Самара",
            "cargo": "Smoke",
            "weight_kg": 100,
            "pickup_at": pickup.isoformat(),
            "deadline_at": (pickup + timedelta(days=1)).isoformat(),
        },
    )
    assert order.status_code == 201, order.text
    for _ in range(20):  # событие → брокер → worker → уведомление
        if api.get("/auth/me/notifications", headers=headers).json():
            print("smoke OK: регистрация, вход, кэш, заказ, событие и уведомление worker")
            return 0
        time.sleep(1)
    print("уведомление от worker не получено")
    return 1


if __name__ == "__main__":
    sys.exit(main())
