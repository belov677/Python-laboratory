# Лабораторная №12 — «Логистическая компания» (вариант 17)

SQLAlchemy 2.x + PostgreSQL. Сущности: Client, Cargo, Shipment, TrackingEvent (+ связь many-to-many shipment_cargo).

```
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://lab:lab@localhost:5432/logistics
python app/main.py --reset     # создать таблицы и тестовые данные
python app/main.py             # работа с существующими данными
pytest                         # тесты (база logistics_test)
```
