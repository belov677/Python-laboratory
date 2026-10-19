"""Собственные контекстные менеджеры."""
from __future__ import annotations

import copy
import time
from datetime import datetime
from pathlib import Path
from types import TracebackType


class StockTransaction:
    """Транзакционный режим для коллекции объектов.

    При входе сохраняется копия состояния; если внутри блока возникло исключение,
    состояние восстанавливается (rollback), исключение передаётся дальше.
    """

    def __init__(self, service) -> None:
        self.service = service
        self._snapshot = None

    def __enter__(self) -> "StockTransaction":
        self._snapshot = copy.deepcopy(self.service.entities)
        print("[TRANSACTION] начало транзакции")
        return self

    def __exit__(self, exc_type: type | None, exc: BaseException | None,
                 tb: TracebackType | None) -> bool:
        if exc_type is not None:
            self.service.entities = self._snapshot
            print(f"[TRANSACTION] ROLLBACK из-за {exc_type.__name__}: {exc}")
        else:
            print("[TRANSACTION] COMMIT")
        return False


class OperationLogger:
    """Записывает в файл дату, операцию, параметры, длительность, результат и исключение."""

    def __init__(self, operation: str, log_file: str | Path = "operations.log", **params) -> None:
        self.operation = operation
        self.params = params
        self.log_file = Path(log_file)

    def __enter__(self) -> "OperationLogger":
        self._start = time.perf_counter()
        self._started_at = datetime.now()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        duration = time.perf_counter() - self._start
        lines = [f"[{self._started_at:%Y-%m-%d %H:%M:%S}]",
                 f"Operation: {self.operation}",
                 f"Parameters: {self.params}",
                 f"Duration: {duration:.4f} sec",
                 f"Result: {'ERROR' if exc_type else 'SUCCESS'}"]
        if exc_type:
            lines.append(f"Exception: {exc_type.__name__}: {exc}")
        with open(self.log_file, "a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n\n")
        return False
