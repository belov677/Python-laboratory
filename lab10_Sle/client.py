"""Консольный HTTP-клиент REST API склада (requests)."""
from __future__ import annotations

import argparse

import requests

FIELDS = [("sku", "Артикул", str), ("name", "Название", str), ("category", "Категория", str),
          ("quantity", "Количество", int), ("min_stock", "Минимальный остаток", int),
          ("price", "Цена", float), ("location", "Место хранения", str)]


class ApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "X-API-Key": api_key})

    def call(self, method: str, path: str, **kwargs) -> requests.Response:
        response = self.session.request(method, self.base + path, timeout=5, **kwargs)
        print(f"→ {method} {path}{'?' + '&'.join(f'{k}={v}' for k, v in kwargs['params'].items()) if kwargs.get('params') else ''}"
              f"  ←  {response.status_code} {response.reason}")
        return response


def print_items(items: list[dict]) -> None:
    if not items:
        print("  (пусто)")
    for i in items:
        flag = "  ⚠ ниже минимума" if i["below_min"] else ""
        print(f"  {i['id']:>3} {i['sku']:7} {i['name']:24} {i['category']:12} "
              f"{i['quantity']:4}/{i['min_stock']:<4} {i['price']:9.2f} {i['location']}{flag}")


def show(response: requests.Response) -> None:
    if response.status_code == 204:
        print("  объект удалён")
        return
    body = response.json()
    if isinstance(body, list):
        print_items(body)
    elif isinstance(body, dict) and "items" in body and "page" in body:
        print_items(body["items"])
        print(f"  страница {body['page']}, по {body['limit']}, всего {body['total']}")
    elif isinstance(body, dict) and "sku" in body:
        print_items([body])
    else:
        print(" ", body)


def form(partial: bool) -> dict:
    data = {}
    for key, title, cast in FIELDS:
        raw = input(f"{title}{' (пусто — не менять)' if partial else ''}: ").strip()
        if partial and raw == "":
            continue
        try:
            data[key] = cast(raw)
        except ValueError:
            data[key] = raw
    return data


MENU = """
=========================
REST CLIENT — СКЛАД
=========================
1. Получить список        6. Удалить
2. Получить объект        7. Фильтрация
3. Создать                8. Сортировка
4. Изменить (PUT)         9. Товары ниже минимального остатка
5. Частично изменить     10. Статистика / пагинация
0. Выход"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--api-key", default="secret-key")
    args = parser.parse_args()
    client = ApiClient(args.url, args.api_key)
    actions = {
        "1": lambda: client.call("GET", "/items"),
        "2": lambda: client.call("GET", f"/items/{input('id: ')}"),
        "3": lambda: client.call("POST", "/items", json=form(False)),
        "4": lambda: client.call("PUT", f"/items/{input('id: ')}", json=form(False)),
        "5": lambda: client.call("PATCH", f"/items/{input('id: ')}", json=form(True)),
        "6": lambda: client.call("DELETE", f"/items/{input('id: ')}"),
        "7": lambda: client.call("GET", "/items", params={k: v for k, v in {
            "category": input("Категория (пусто — любая): ").strip(),
            "min_quantity": input("Количество от: ").strip(),
            "max_quantity": input("Количество до: ").strip()}.items() if v}),
        "8": lambda: client.call("GET", "/items", params={
            "sort": input("Поле (name/quantity/price/category): ").strip(),
            "order": input("Порядок (asc/desc): ").strip() or "asc"}),
        "9": lambda: client.call("GET", "/items/low-stock"),
        "10": lambda: (show(client.call("GET", "/items/statistics")),
                       client.call("GET", "/items", params={"page": 2, "limit": 2}))[1],
    }
    while True:
        print(MENU)
        choice = input("Выберите действие: ").strip()
        if choice == "0":
            break
        if choice not in actions:
            print("Неизвестное действие.")
            continue
        try:
            show(actions[choice]())
        except requests.ConnectionError:
            print("Ошибка: сервер недоступен")
        except requests.Timeout:
            print("Ошибка: превышено время ожидания ответа")


if __name__ == "__main__":
    main()
