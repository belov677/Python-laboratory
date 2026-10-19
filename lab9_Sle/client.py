"""TCP-клиент аптеки (лабораторная №9, вариант 17).

Запуск: python client.py [--port 5017] [--timeout 5]
"""
from __future__ import annotations

import argparse
import json
import socket
import time
import uuid

import protocol
from exceptions import ProtocolError

HOST = "127.0.0.1"


class PharmacyClient:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.reader = protocol.MessageReader(self.sock)

    def send_raw(self, payload: bytes) -> dict:
        self.sock.sendall(payload)
        raw = self.reader.read()
        if raw is None:
            raise ConnectionError("Сервер закрыл соединение")
        return protocol.decode(raw)

    def request(self, command: str, data: dict | None = None) -> dict:
        request_id = uuid.uuid4().hex[:8]
        response = self.send_raw(protocol.encode(
            {"request_id": request_id, "command": command, "data": data or {}}))
        if response.get("request_id") not in (request_id, None):
            raise ProtocolError("Ответ относится к другому запросу")
        return response

    def udp_status(self) -> dict:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(2)
            udp.sendto(b"status", (self.host, self.port + 1))
            try:
                data, _ = udp.recvfrom(4096)
            except socket.timeout:
                return {"status": "нет ответа — датаграмма могла быть потеряна"}
            return protocol.decode(data.strip())

    def close(self) -> None:
        self.sock.close()


def print_medicines(items: list[dict]) -> None:
    if not items:
        print("  (пусто)")
    for m in items:
        rx = " Rx" if m["prescription"] else ""
        print(f"  {m['id']:>3} {m['name']:22} {m['category']:16} {m['manufacturer']:12} "
              f"{m['price']:8.2f} руб. {m['quantity']:4} шт.{rx}")


def show(response: dict) -> None:
    if response["status"] == "error":
        print(f"Ошибка сервера: {response['error']}")
        return
    data = response["data"]
    if isinstance(data, list) and data and isinstance(data[0], dict) and "category" in data[0]:
        print_medicines(data)
    elif isinstance(data, dict) and "category" in data:
        print_medicines([data])
    elif isinstance(data, list):
        for line in data:
            print(" ", line)
    else:
        print(" ", data)


def ask_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Введите целое число.")


def medicine_form(partial: bool = False) -> dict:
    data = {}
    for key, title, cast in (("name", "Название", str), ("category", "Категория", str),
                             ("manufacturer", "Производитель", str), ("price", "Цена", float),
                             ("quantity", "Количество", int)):
        value = input(f"{title}{' (пусто — не менять)' if partial else ''}: ").strip()
        if value == "" and partial:
            continue
        try:
            data[key] = cast(value)
        except ValueError:
            data[key] = value               # пусть сервер проверит и вернёт ошибку
    if not partial:
        data["prescription"] = input("Рецептурный? (д/н): ").strip().lower() == "д"
    return data


MENU = """
=== CLIENT: АПТЕКА ===
1. Получить список            7. ping
2. Получить препарат          8. История запросов сервера
3. Создать                    9. Статус сервера (UDP)
4. Изменить                  10. Долгая операция (проверка тайм-аута)
5. Удалить                   11. Отправить произвольный текст
6. Поиск по категории        12. Остановить сервер (admin)
0. Выход"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5017)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--name", default="client")
    args = parser.parse_args()
    try:
        client = PharmacyClient(HOST, args.port, args.timeout)
    except (ConnectionRefusedError, socket.timeout, OSError) as error:
        print(f"Сервер {HOST}:{args.port} недоступен: {error}")
        return
    print(f"[{args.name}] подключено к {HOST}:{args.port}, тайм-аут {args.timeout} с")
    actions = {
        "1": lambda: client.request("list"),
        "2": lambda: client.request("get", {"id": ask_int("id: ")}),
        "3": lambda: client.request("create", medicine_form()),
        "4": lambda: client.request("update", {"id": ask_int("id: "), **medicine_form(True)}),
        "5": lambda: client.request("delete", {"id": ask_int("id: ")}),
        "6": lambda: client.request("search_by_category", {"category": input("Категория: ").strip()}),
        "8": lambda: client.request("history"),
        "10": lambda: client.request("slow", {"seconds": float(input("Секунд: "))}),
        "11": lambda: client.send_raw(input("Текст: ").encode() + b"\n"),
        "12": lambda: client.request("shutdown", {"token": input("Токен: ")}),
    }
    try:
        while True:
            print(MENU)
            choice = input(f"[{args.name}] Введите команду: ").strip()
            if choice == "0":
                break
            try:
                if choice == "7":
                    start = time.perf_counter()
                    response = client.request("ping")
                    print(f"  {response['data']['message']}, время ответа "
                          f"{(time.perf_counter() - start) * 1000:.2f} мс")
                elif choice == "9":
                    print(" ", json.dumps(client.udp_status(), ensure_ascii=False))
                elif choice in actions:
                    show(actions[choice]())
                else:
                    print("Неизвестная команда.")
            except socket.timeout:
                print(f"Ошибка: сервер не ответил за {args.timeout} с (тайм-аут)")
                break
            except (ConnectionError, OSError) as error:
                print(f"Ошибка: соединение разорвано ({error})")
                break
            except ProtocolError as error:
                print("Ошибка протокола:", error)
    finally:
        client.close()
        print(f"[{args.name}] соединение закрыто")


if __name__ == "__main__":
    main()
