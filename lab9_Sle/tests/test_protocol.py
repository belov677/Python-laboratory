import socket
import threading
import time

import pytest

import protocol
from client import PharmacyClient
from exceptions import ProtocolError
from repository import MedicineRepository
from server import PharmacyServer, seed
from service import PharmacyService


def test_encode_decode_message():
    message = {"command": "get", "data": {"id": 5}}
    raw = protocol.encode(message)
    assert raw.endswith(b"\n")
    assert protocol.decode(raw.strip()) == message


@pytest.mark.parametrize("raw", [b"{not json", b"[1, 2]", b"\xff\xfe"])
def test_decode_rejects_bad_input(raw):
    with pytest.raises(ProtocolError):
        protocol.decode(raw)


def test_validate_request_requires_command():
    with pytest.raises(ProtocolError):
        protocol.validate_request({"data": {}})


def test_reader_splits_stream_into_messages():
    left, right = socket.socketpair()
    reader = protocol.MessageReader(right)
    left.sendall(b'{"a": 1}\n{"b"')          # два сообщения пришли «склеенными»
    left.sendall(b': 2}\n')
    assert protocol.decode(reader.read()) == {"a": 1}
    assert protocol.decode(reader.read()) == {"b": 2}
    left.close()
    assert reader.read() is None
    right.close()


@pytest.fixture
def running_server():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    service = PharmacyService(MedicineRepository())
    seed(service)
    server = PharmacyServer("127.0.0.1", port, service)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    yield port
    server.stop_event.set()
    thread.join(timeout=5)


def test_integration_client_server(running_server):
    client = PharmacyClient("127.0.0.1", running_server, timeout=3)
    created = client.request("create", dict(name="Цитрамон", category="обезболивающие",
                                            manufacturer="Фармстандарт", price=60.0, quantity=30))
    assert created["status"] == "ok"
    found = client.request("search_by_category", {"category": "обезболивающие"})
    assert "Цитрамон" in [m["name"] for m in found["data"]]
    assert client.request("get", {"id": 999})["status"] == "error"
    assert client.request("unknown")["error"].startswith("Неизвестная команда")
    client.close()
