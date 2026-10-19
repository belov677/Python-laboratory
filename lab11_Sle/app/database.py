"""Подключение к PostgreSQL (psycopg 3)."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DB_DIR = Path(__file__).resolve().parents[1] / "db"


class Database:
    def __init__(self, url: str) -> None:
        self.url = url

    @contextmanager
    def connection(self):
        """Соединение = транзакция: COMMIT при успехе, ROLLBACK при исключении."""
        with psycopg.connect(self.url, row_factory=dict_row) as conn:
            yield conn

    def run_script(self, *names: str) -> None:
        with self.connection() as conn:
            for name in names:
                conn.execute((DB_DIR / name).read_text(encoding="utf-8"))

    def reset(self) -> None:
        self.run_script("schema.sql", "indexes.sql", "seed.sql")
