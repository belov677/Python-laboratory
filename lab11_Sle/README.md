# Лабораторная №11 — «Склад» (вариант 17): PostgreSQL + Redis + CDN

## Запуск
1. PostgreSQL (пользователь `lab`/`lab`, базы `warehouse`, `warehouse_test`) и Redis на localhost.
2. `pip install -r requirements.txt`
3. `python app/app.py --reset-db` — создаёт схему (`db/schema.sql`, `db/indexes.sql`) и данные (`db/seed.sql`), API на :5000.
4. `python cdn/edge.py` — имитация CDN edge на :8090, `python cdn/cdn_test.py` — эксперимент.
5. `python client.py` — консольный клиент; `pytest` — тесты.

Дополнительно: `nosql_demo.py` (операции Redis), `benchmark.py` (PostgreSQL vs Redis),
`explain.py` (EXPLAIN ANALYZE до/после индекса), `docker-compose.yml` (api + postgres + redis).
