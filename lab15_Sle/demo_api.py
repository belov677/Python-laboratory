"""Демонстрация REST API (urllib, без внешних зависимостей)."""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5015"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            code, raw = resp.status, resp.read().decode()
    except urllib.error.HTTPError as error:
        code, raw = error.code, error.read().decode()
    print(f">>> {method} {path}" + (f"  {json.dumps(body, ensure_ascii=False)}" if body else ""))
    text = json.dumps(json.loads(raw), ensure_ascii=False) if raw else "(пусто)"
    print(f"<<< {code} {text[:300]}{'…' if len(text) > 300 else ''}\n")


call("GET", "/health")
call("GET", "/api/shipments?status=IN_TRANSIT&sort=cost&order=desc&size=2")
call("POST", "/api/shipments", {"client_id": 4, "origin": "Краснодар", "destination": "Ростов-на-Дону",
                                "distance_km": 280, "cargos": [{"description": "Фрукты",
                                                                "weight_kg": 300, "cargo_type": "обычный"}]})
call("POST", "/api/shipments/9/status", {"status": "IN_TRANSIT", "location": "Тихорецк"})
call("GET", "/api/track/LG-00009")
call("POST", "/api/shipments", {"client_id": 99, "origin": "Тула", "destination": "тула",
                                "distance_km": 0})
call("POST", "/api/shipments/1/status", {"status": "CANCELLED", "location": "СПб"})
call("POST", "/api/clients", {"name": "Дубль", "email": "farm@fermer.ru", "city": "Тула"})
call("DELETE", "/api/shipments/2")
call("GET", "/api/shipments/12345")
