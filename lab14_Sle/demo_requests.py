"""Демонстрация API: запрос → код ответа → JSON (сценарий защиты)."""
import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, timeout=5)


def show(method: str, url: str, headers=None, **kwargs) -> httpx.Response:
    response = client.request(method, url, headers=headers, **kwargs)
    body = kwargs.get("json") or kwargs.get("data")
    print(f"\n>>> {method} {url}" + (f"\n    body: {json.dumps(body, ensure_ascii=False)}" if body else ""))
    extra = f"  X-Cache: {response.headers['X-Cache']}" if "X-Cache" in response.headers else ""
    print(f"<<< {response.status_code} {response.reason_phrase}{extra}")
    if response.content:
        text = json.dumps(response.json(), ensure_ascii=False)
        print("    " + (text if len(text) < 600 else text[:600] + " ..."))
    return response


section = sys.argv[2] if len(sys.argv) > 2 else "crud"
admin_token = client.post("/auth/login", data={"username": "admin", "password": "admin12345"}).json()["access_token"]
ADMIN = {"Authorization": f"Bearer {admin_token}"}

if section == "auth":
    show("GET", "/items")
    show("POST", "/auth/register", json={"username": "ivan", "password": "password123"})
    show("POST", "/auth/register", json={"username": "ivan", "password": "password123"})
    show("POST", "/auth/login", data={"username": "ivan", "password": "wrong-password"})
    user_token = show("POST", "/auth/login", data={"username": "ivan", "password": "password123"}).json()["access_token"]
    USER = {"Authorization": f"Bearer {user_token}"}
    show("GET", "/profile", headers=USER)
    show("GET", "/items/1", headers=USER)
    show("DELETE", "/items/1", headers=USER)
    show("GET", "/profile", headers={"Authorization": "Bearer invalid.token.value"})
elif section == "crud":
    new = {"sku": "CB-HDMI", "name": "Кабель HDMI 2 м", "category": "электроника", "quantity": 40,
           "min_stock": 10, "price": 390, "supplier": "ООО Периферия", "location": "A-05"}
    created = show("POST", "/items", headers=ADMIN, json=new).json()
    item = f"/items/{created['id']}"
    show("GET", item, headers=ADMIN)
    show("GET", item, headers=ADMIN)
    show("PUT", item, headers=ADMIN, json={**new, "name": "Кабель HDMI 2.1, 2 м", "price": 450})
    show("PATCH", item, headers=ADMIN, json={"quantity": 8})
    show("GET", item, headers=ADMIN)
    show("DELETE", item, headers=ADMIN)
    show("DELETE", item, headers=ADMIN)
    show("GET", item, headers=ADMIN)
elif section == "query":
    show("GET", "/items?category=мебель&sort=price&order=desc", headers=ADMIN)
    show("GET", "/items?below_min=true&sort=quantity&limit=3", headers=ADMIN)
    show("GET", "/items?skip=5&limit=5&sort=sku", headers=ADMIN)
    show("GET", "/items/search?q=молкомб", headers=ADMIN)
    show("GET", "/items/statistics", headers=ADMIN)
elif section == "errors":
    show("POST", "/items", headers=ADMIN, json={"sku": "nb 1", "name": "X", "category": "э",
                                               "quantity": -3, "price": 0, "supplier": "S",
                                               "location": "склад"})
    show("POST", "/items", headers=ADMIN, json={"sku": "NB-001", "name": "Дубль", "category": "электроника",
                                               "quantity": 1, "price": 10, "supplier": "Тест",
                                               "location": "A-09"})
    show("PATCH", "/items/2", headers=ADMIN, json={})
    show("GET", "/items/abc", headers=ADMIN)
    show("GET", "/items?sort=color&limit=500", headers=ADMIN)
    show("GET", "/health")
