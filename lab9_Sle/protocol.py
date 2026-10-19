"""Прикладной протокол: newline-delimited JSON.

Запрос:  {"request_id": "...", "command": "...", "data": {...}}\\n
Ответ:   {"request_id": "...", "status": "ok", "data": ...}\\n
         {"request_id": "...", "status": "error", "error": "..."}\\n
"""
from __future__ import annotations

import json
import socket

from exceptions import ProtocolError

ENCODING = "utf-8"
DELIMITER = b"\n"
MAX_MESSAGE = 64 * 1024


def encode(message: dict) -> bytes:
    return json.dumps(message, ensure_ascii=False).encode(ENCODING) + DELIMITER


def decode(raw: bytes) -> dict:
    try:
        message = json.loads(raw.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"Некорректный JSON: {error}") from None
    if not isinstance(message, dict):
        raise ProtocolError("Сообщение должно быть JSON-объектом")
    return message


def validate_request(message: dict) -> tuple[str, dict]:
    command = message.get("command")
    data = message.get("data", {})
    if not isinstance(command, str) or not command:
        raise ProtocolError("Отсутствует обязательное поле command")
    if not isinstance(data, dict):
        raise ProtocolError("Поле data должно быть объектом")
    return command, data


def ok(data=None, request_id=None) -> dict:
    return {"request_id": request_id, "status": "ok", "data": data if data is not None else {}}


def error(text: str, request_id=None) -> dict:
    return {"request_id": request_id, "status": "error", "error": text}


class MessageReader:
    """Собирает сообщения из потока байтов TCP по разделителю \\n."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = b""

    def read(self) -> bytes | None:
        while DELIMITER not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:                       # соединение закрыто
                return None
            self.buffer += chunk
            if len(self.buffer) > MAX_MESSAGE:
                raise ProtocolError("Слишком длинное сообщение")
        line, self.buffer = self.buffer.split(DELIMITER, 1)
        return line
