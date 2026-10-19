"""EXPLAIN ANALYZE: запрос истории движения товара до и после создания индекса.

Для наглядности в транзакции добавляется 200 000 записей движения, затем транзакция
откатывается — рабочие данные не меняются.
"""
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent / "app"))
from config import DATABASE_URL  # noqa: E402

QUERY = ("SELECT * FROM stock_movements WHERE item_id = 5 "
         "ORDER BY created_at DESC LIMIT 10")

with psycopg.connect(DATABASE_URL) as conn:
    conn.execute("DROP INDEX IF EXISTS idx_movements_item_date")
    conn.execute("""INSERT INTO stock_movements(item_id, movement_type, quantity, created_at)
                    SELECT 1 + (g % 12), CASE WHEN g % 3 = 0 THEN 'out' ELSE 'in' END, 1 + g % 5,
                           now() - (g || ' minutes')::interval
                    FROM generate_series(1, 200000) g""")
    conn.execute("ANALYZE stock_movements")
    for title in ("БЕЗ ИНДЕКСА", "С ИНДЕКСОМ idx_movements_item_date"):
        if "С ИНДЕКСОМ" in title:
            conn.execute("CREATE INDEX idx_movements_item_date "
                         "ON stock_movements(item_id, created_at DESC)")
            conn.execute("ANALYZE stock_movements")
        print(f"=== {title} ===")
        for (line,) in conn.execute("EXPLAIN ANALYZE " + QUERY):
            print(line)
        print()
    conn.rollback()      # отмена тестовых данных и изменений индексов
print("Транзакция отменена (ROLLBACK): тестовые записи удалены, индекс восстановлен из schema.")
