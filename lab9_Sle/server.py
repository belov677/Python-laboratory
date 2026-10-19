"""TCP-сервер аптеки (лабораторная №9, вариант 17).

Запуск: python server.py [--port 5017]
Дополнительно: UDP-статус на порту port+1, ping, request_id, история запросов,
ограничение частоты запросов, graceful shutdown.
"""
from __future__ import annotations

import argparse
import logging
import os
import socket
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import protocol
from exceptions import PharmacyError, ProtocolError
from repository import MedicineRepository
from service import PharmacyService

HOST = "127.0.0.1"
CLIENT_TIMEOUT = 60          # сек. бездействия клиента
RATE_LIMIT = (20, 10)        # не более 20 запросов за 10 секунд
ADMIN_TOKEN = os.getenv("PHARMACY_ADMIN_TOKEN", "admin-secret")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler("server.log", encoding="utf-8")])
log = logging.getLogger("server")


def seed(service: PharmacyService) -> None:
    for item in [
        dict(name="Нурофен", category="обезболивающие", manufacturer="Reckitt", price=320.0, quantity=40),
        dict(name="Парацетамол", category="обезболивающие", manufacturer="Фармстандарт", price=45.5, quantity=120),
        dict(name="Амоксициллин", category="антибиотики", manufacturer="Сандоз", price=210.0, quantity=15, prescription=True),
        dict(name="Компливит", category="витамины", manufacturer="Отисифарм", price=290.0, quantity=0),
        dict(name="Аскорбиновая кислота", category="витамины", manufacturer="Марбиофарм", price=39.0, quantity=200),
        dict(name="Ингавирин", category="противовирусные", manufacturer="Валента", price=520.0, quantity=25),
    ]:
        service.create_medicine(item)


class PharmacyServer:
    def __init__(self, host: str, port: int, service: PharmacyService) -> None:
        self.host, self.port, self.service = host, port, service
        self.stop_event = threading.Event()
        self.history: deque[str] = deque(maxlen=20)
        self.clients = 0
        self.connections: set[socket.socket] = set()
        self._lock = threading.Lock()
        self.handlers = {
            "list": lambda d: [m.to_dict() for m in self.service.list_medicines()],
            "get": lambda d: self.service.get_medicine(d.get("id")).to_dict(),
            "create": lambda d: self.service.create_medicine(d).to_dict(),
            "update": lambda d: self.service.update_medicine(
                d.get("id"), {k: v for k, v in d.items() if k != "id"}).to_dict(),
            "delete": lambda d: self.service.delete_medicine(d.get("id")) or {"deleted": d.get("id")},
            "search_by_category": lambda d: [m.to_dict() for m in
                                             self.service.search_by_category(d.get("category"))],
            "ping": lambda d: {"message": "pong", "server_time": time.time()},
            "history": lambda d: list(self.history),
            "slow": self._slow,
            "shutdown": self._shutdown,
        }

    # ----- служебные команды -----
    def _slow(self, data: dict) -> dict:
        seconds = min(float(data.get("seconds", 3)), 10)
        time.sleep(seconds)
        return {"slept": seconds}

    def _shutdown(self, data: dict) -> dict:
        if data.get("token") != ADMIN_TOKEN:
            raise PharmacyError("Неверный токен администратора")
        log.warning("Получена команда shutdown — сервер завершает работу")
        self.stop_event.set()
        return {"message": "server is shutting down"}

    # ----- обработка запроса (без сети) -----
    def handle_request(self, raw: bytes, client: str) -> dict:
        request_id = None
        try:
            message = protocol.decode(raw)
            request_id = message.get("request_id")
            command, data = protocol.validate_request(message)
            log.info("Command from %s: %s %s", client, command, data or "")
            with self._lock:
                self.history.append(f"{time.strftime('%H:%M:%S')} {client} {command}")
            handler = self.handlers.get(command)
            if handler is None:
                raise ProtocolError(f"Неизвестная команда: {command}")
            result = handler(data)
            log.info("Command %s from %s: OK", command, client)
            return protocol.ok(result, request_id)
        except PharmacyError as err:
            log.warning("Bad request from %s: %s", client, err)
            return protocol.error(str(err), request_id)
        except Exception as err:                         # непредвиденная ошибка сервера
            log.exception("Internal error while handling %s", client)
            return protocol.error(f"Внутренняя ошибка сервера: {type(err).__name__}", request_id)

    # ----- сетевая часть -----
    def serve_client(self, conn: socket.socket, addr: tuple) -> None:
        client = f"{addr[0]}:{addr[1]}"
        with self._lock:
            self.clients += 1
            self.connections.add(conn)
        log.info("Client connected: %s (активных: %d)", client, self.clients)
        conn.settimeout(CLIENT_TIMEOUT)
        reader = protocol.MessageReader(conn)
        requests: deque[float] = deque()
        try:
            while not self.stop_event.is_set():
                try:
                    raw = reader.read()
                except socket.timeout:
                    log.info("Client %s: тайм-аут бездействия %d с", client, CLIENT_TIMEOUT)
                    break
                except ProtocolError as err:
                    conn.sendall(protocol.encode(protocol.error(str(err))))
                    break
                if raw is None:
                    break
                now = time.monotonic()
                while requests and now - requests[0] > RATE_LIMIT[1]:
                    requests.popleft()
                if len(requests) >= RATE_LIMIT[0]:
                    response = protocol.error("Слишком много запросов, повторите позже")
                    log.warning("Rate limit exceeded: %s", client)
                else:
                    requests.append(now)
                    response = self.handle_request(raw, client)
                conn.sendall(protocol.encode(response))
        except (ConnectionResetError, BrokenPipeError):
            log.warning("Connection with %s was reset", client)
        finally:
            conn.close()
            with self._lock:
                self.clients -= 1
                self.connections.discard(conn)
            log.info("Client disconnected: %s", client)

    def serve_udp(self) -> None:
        """UDP: быстрый запрос статуса сервера, потеря датаграммы не критична."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind((self.host, self.port + 1))
            udp.settimeout(1)
            while not self.stop_event.is_set():
                try:
                    data, addr = udp.recvfrom(1024)
                except socket.timeout:
                    continue
                if data.strip() == b"status":
                    status = {"status": "running", "clients": self.clients,
                              **self.service.statistics()}
                    udp.sendto(protocol.encode(status), addr)

    def run(self) -> None:
        threading.Thread(target=self.serve_udp, daemon=True).start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server, \
                ThreadPoolExecutor(max_workers=10) as pool:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()
            server.settimeout(1)           # чтобы периодически проверять stop_event
            log.info("Server started on %s:%d (UDP status on %d)", self.host, self.port,
                     self.port + 1)
            while not self.stop_event.is_set():
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                pool.submit(self.serve_client, conn, addr)
            log.info("Прекращён приём новых клиентов, ожидание завершения текущих операций")
            with self._lock:
                for conn in self.connections:     # «будим» клиентов, ожидающих recv()
                    try:
                        conn.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
        log.info("Server stopped")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5017)
    args = parser.parse_args()
    service = PharmacyService(MedicineRepository())
    seed(service)
    PharmacyServer(HOST, args.port, service).run()


if __name__ == "__main__":
    main()
