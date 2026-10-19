"""Repository на SQLite (стандартный модуль sqlite3)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from src.models.entities import Movement, MovementType, Product, Warehouse

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'шт',
    min_stock INTEGER NOT NULL DEFAULT 0 CHECK (min_stock >= 0)
);
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS balances (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (product_id, warehouse_id)
);
CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    source_id INTEGER REFERENCES warehouses(id),
    target_id INTEGER REFERENCES warehouses(id),
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _lower(value: str | None) -> str | None:
    return value.lower() if value is not None else None


class SQLiteInventoryRepository:
    def __init__(self, path: str = ":memory:") -> None:
        # FastAPI выполняет синхронные обработчики в пуле потоков, поэтому соединение
        # должно быть доступно не только потоку, который его создал
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.create_function("py_lower", 1, _lower)   # lower() SQLite не знает кириллицу
        self.conn.executescript(SCHEMA)
        self._in_transaction = False

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Все изменения внутри блока фиксируются вместе или откатываются."""
        self._in_transaction = True
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self._in_transaction = False

    def _commit(self) -> None:
        if not self._in_transaction:
            self.conn.commit()

    # ---------- товары ----------
    @staticmethod
    def _product(row: sqlite3.Row | None) -> Product | None:
        return Product(row["sku"], row["name"], row["unit"], row["min_stock"], row["id"]) if row else None

    def add_product(self, product: Product) -> Product:
        cur = self.conn.execute("INSERT INTO products (sku, name, unit, min_stock) VALUES (?, ?, ?, ?)",
                                (product.sku, product.name, product.unit, product.min_stock))
        self._commit()
        product.id = cur.lastrowid
        return product

    def get_product(self, product_id: int) -> Product | None:
        return self._product(self.conn.execute("SELECT * FROM products WHERE id = ?",
                                               (product_id,)).fetchone())

    def get_product_by_sku(self, sku: str) -> Product | None:
        return self._product(self.conn.execute("SELECT * FROM products WHERE sku = ?",
                                               (sku,)).fetchone())

    def search_products(self, text: str) -> list[Product]:
        pattern = f"%{text.lower()}%"
        rows = self.conn.execute(
            "SELECT * FROM products WHERE py_lower(name) LIKE ? OR py_lower(sku) LIKE ? ORDER BY name",
            (pattern, pattern)).fetchall()
        return [self._product(r) for r in rows]

    def delete_product(self, product_id: int) -> None:
        self.conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self._commit()

    # ---------- склады ----------
    def add_warehouse(self, warehouse: Warehouse) -> Warehouse:
        cur = self.conn.execute("INSERT INTO warehouses (name, city) VALUES (?, ?)",
                                (warehouse.name, warehouse.city))
        self._commit()
        warehouse.id = cur.lastrowid
        return warehouse

    def get_warehouse(self, warehouse_id: int) -> Warehouse | None:
        row = self.conn.execute("SELECT * FROM warehouses WHERE id = ?", (warehouse_id,)).fetchone()
        return Warehouse(row["name"], row["city"], row["id"]) if row else None

    # ---------- остатки ----------
    def get_balance(self, product_id: int, warehouse_id: int) -> int:
        row = self.conn.execute("SELECT quantity FROM balances WHERE product_id = ? AND warehouse_id = ?",
                                (product_id, warehouse_id)).fetchone()
        return row["quantity"] if row else 0

    def set_balance(self, product_id: int, warehouse_id: int, quantity: int) -> None:
        self.conn.execute(
            "INSERT INTO balances (product_id, warehouse_id, quantity) VALUES (?, ?, ?) "
            "ON CONFLICT (product_id, warehouse_id) DO UPDATE SET quantity = excluded.quantity",
            (product_id, warehouse_id, quantity))
        self._commit()

    def balances(self, product_id: int) -> dict[int, int]:
        rows = self.conn.execute("SELECT warehouse_id, quantity FROM balances WHERE product_id = ? "
                                 "ORDER BY warehouse_id", (product_id,)).fetchall()
        return {r["warehouse_id"]: r["quantity"] for r in rows}

    # ---------- журнал движений ----------
    def add_movement(self, movement: Movement) -> Movement:
        cur = self.conn.execute(
            "INSERT INTO movements (type, product_id, quantity, source_id, target_id, comment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (movement.type.value, movement.product_id, movement.quantity, movement.source_id,
             movement.target_id, movement.comment, movement.created_at.isoformat()))
        self._commit()
        movement.id = cur.lastrowid
        return movement

    def movements(self, product_id: int) -> list[Movement]:
        rows = self.conn.execute("SELECT * FROM movements WHERE product_id = ? ORDER BY id",
                                 (product_id,)).fetchall()
        return [Movement(MovementType(r["type"]), r["product_id"], r["quantity"], r["source_id"],
                         r["target_id"], r["comment"], datetime.fromisoformat(r["created_at"]), r["id"])
                for r in rows]
