"""Repository: все SQL-запросы приложения. Только параметризованные запросы (защита от SQL injection)."""
from __future__ import annotations

import psycopg

from database import Database
from exceptions import ConflictError, InsufficientStockError, ItemNotFoundError

ITEM_SELECT = """
    SELECT i.id, i.sku, i.name, c.name AS category, i.quantity, i.min_stock,
           i.price::float AS price, i.location, i.image_url,
           i.quantity < i.min_stock AS below_min
    FROM items i JOIN categories c ON c.id = i.category_id
"""
SORT_COLUMNS = {"id": "i.id", "name": "i.name", "quantity": "i.quantity",
                "price": "i.price", "category": "c.name"}


class ItemRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_all(self, category: str | None = None, min_quantity: int | None = None,
                max_quantity: int | None = None, search: str | None = None,
                sort: str = "id", order: str = "asc", limit: int | None = None,
                offset: int = 0) -> list[dict]:
        conditions, params = [], []
        if category:
            conditions.append("c.name = %s")
            params.append(category)
        if min_quantity is not None:
            conditions.append("i.quantity >= %s")
            params.append(min_quantity)
        if max_quantity is not None:
            conditions.append("i.quantity <= %s")
            params.append(max_quantity)
        if search:
            conditions.append("(i.name ILIKE %s OR i.sku ILIKE %s)")
            params += [f"%{search}%", f"%{search}%"]
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        # имя столбца и направление берутся только из белого списка, а не из ввода
        direction = "DESC" if order == "desc" else "ASC"
        sql = f"{ITEM_SELECT} {where} ORDER BY {SORT_COLUMNS[sort]} {direction}, i.id"
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params += [limit, offset]
        with self.db.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def count(self) -> int:
        with self.db.connection() as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM items").fetchone()["n"]

    def get_by_id(self, item_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute(f"{ITEM_SELECT} WHERE i.id = %s", (item_id,)).fetchone()
        if row is None:
            raise ItemNotFoundError(f"Item with id {item_id} not found")
        return row

    def _category_id(self, conn, name: str) -> int:
        row = conn.execute(
            "INSERT INTO categories(name) VALUES (%s) ON CONFLICT (name) DO UPDATE "
            "SET name = EXCLUDED.name RETURNING id", (name,)).fetchone()
        return row["id"]

    def create(self, data: dict) -> dict:
        try:
            with self.db.connection() as conn:
                category_id = self._category_id(conn, data["category"])
                row = conn.execute(
                    """INSERT INTO items(sku, name, category_id, quantity, min_stock, price,
                                         location, image_url)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (data["sku"], data["name"], category_id, data["quantity"],
                     data["min_stock"], data["price"], data["location"],
                     data.get("image_url"))).fetchone()
        except psycopg.errors.UniqueViolation:
            raise ConflictError(f"Товар с артикулом {data['sku']} уже существует") from None
        return self.get_by_id(row["id"])

    def update(self, item_id: int, data: dict) -> dict:
        self.get_by_id(item_id)
        columns = {k: v for k, v in data.items() if k != "category"}
        try:
            with self.db.connection() as conn:
                if "category" in data:
                    columns["category_id"] = self._category_id(conn, data["category"])
                assignments = ", ".join(f"{column} = %s" for column in columns)
                conn.execute(f"UPDATE items SET {assignments} WHERE id = %s",
                             (*columns.values(), item_id))
        except psycopg.errors.UniqueViolation:
            raise ConflictError(f"Товар с артикулом {data['sku']} уже существует") from None
        return self.get_by_id(item_id)

    def delete(self, item_id: int) -> None:
        with self.db.connection() as conn:
            if conn.execute("DELETE FROM items WHERE id = %s", (item_id,)).rowcount == 0:
                raise ItemNotFoundError(f"Item with id {item_id} not found")

    def low_stock(self) -> list[dict]:
        with self.db.connection() as conn:
            return conn.execute(f"{ITEM_SELECT} WHERE i.quantity < i.min_stock "
                                "ORDER BY i.quantity - i.min_stock").fetchall()

    def suppliers(self, item_id: int) -> list[dict]:
        self.get_by_id(item_id)
        with self.db.connection() as conn:
            return conn.execute(
                """SELECT s.id, s.name, s.city, isup.purchase_price::float AS purchase_price
                   FROM item_suppliers isup JOIN suppliers s ON s.id = isup.supplier_id
                   WHERE isup.item_id = %s ORDER BY isup.purchase_price""", (item_id,)).fetchall()

    def movements(self, item_id: int) -> list[dict]:
        self.get_by_id(item_id)
        with self.db.connection() as conn:
            return conn.execute(
                """SELECT m.id, m.movement_type, m.quantity, s.name AS supplier,
                          to_char(m.created_at, 'YYYY-MM-DD HH24:MI') AS created_at
                   FROM stock_movements m LEFT JOIN suppliers s ON s.id = m.supplier_id
                   WHERE m.item_id = %s ORDER BY m.created_at DESC""", (item_id,)).fetchall()

    def register_movement(self, item_id: int, movement_type: str, quantity: int,
                          supplier_id: int | None = None) -> dict:
        """Транзакция: запись в журнал + изменение остатка. При ошибке — ROLLBACK обоих действий."""
        self.get_by_id(item_id)
        with self.db.connection() as conn:          # одна транзакция
            conn.execute("""INSERT INTO stock_movements(item_id, supplier_id, movement_type, quantity)
                            VALUES (%s, %s, %s, %s)""",
                         (item_id, supplier_id, movement_type, quantity))
            delta = quantity if movement_type == "in" else -quantity
            try:
                conn.execute("UPDATE items SET quantity = quantity + %s WHERE id = %s",
                             (delta, item_id))
            except psycopg.errors.CheckViolation:
                raise InsufficientStockError(
                    f"Недостаточно товара для отгрузки {quantity} шт.") from None
        return self.get_by_id(item_id)

    def statistics(self) -> dict:
        with self.db.connection() as conn:
            return conn.execute(
                """SELECT COUNT(*) AS items, COALESCE(SUM(quantity), 0) AS units,
                          COALESCE(SUM(quantity * price), 0)::float AS stock_value,
                          COUNT(*) FILTER (WHERE quantity < min_stock) AS below_min,
                          (SELECT COUNT(*) FROM categories) AS categories,
                          (SELECT COUNT(*) FROM suppliers) AS suppliers
                   FROM items""").fetchone()
