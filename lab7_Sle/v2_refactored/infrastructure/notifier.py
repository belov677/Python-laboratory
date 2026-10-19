"""Реализации уведомлений. Сервис знает только протокол Notifier."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


class ConsoleNotifier:
    def send(self, message: str) -> None:
        print(f"[УВЕДОМЛЕНИЕ] {message}")


class EmailNotifier:
    """Учебная заглушка отправки e-mail."""

    def __init__(self, address: str) -> None:
        self.address = address

    def send(self, message: str) -> None:
        print(f"[EMAIL → {self.address}] {message}")


class FileNotifier:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def send(self, message: str) -> None:
        with open(self.path, "a", encoding="utf-8") as file:
            file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")
