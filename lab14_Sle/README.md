# Warehouse API — лабораторная №14, вариант 17 «Склад — товары»

REST API складского учёта на **FastAPI**: товары (артикул, название, категория, количество,
поставщик, место хранения, срок годности), фильтрация, сортировка, пагинация, поиск,
статистика, JWT-авторизация с ролями USER/ADMIN, кэш Redis.

## Технологии
FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL 16, Redis 7, PyJWT, pytest, Docker Compose.

## Установка и запуск
```
pip install -r requirements.txt
cp .env.example .env            # задать переменные окружения
uvicorn main:app --app-dir app --port 8000
python app/seed.py              # тестовые данные (15 товаров)
```
Переменные окружения: `DATABASE_URL`, `REDIS_URL`, `CACHE_TTL`, `JWT_SECRET`, `JWT_TTL_MINUTES`,
`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `APP_ENV` (см. `.env.example`).

## Docker
```
cp .env.example .env
docker compose up --build
```

## Документация
Swagger UI — http://127.0.0.1:8000/docs, ReDoc — http://127.0.0.1:8000/redoc
(статические файлы Swagger UI и ReDoc лежат в `app/static`, интернет не нужен).

## Примеры запросов
```
curl -X POST localhost:8000/auth/login -d "username=admin&password=admin12345"
curl -H "Authorization: Bearer $TOKEN" "localhost:8000/items?category=мебель&sort=price&order=desc&limit=5"
curl -H "Authorization: Bearer $TOKEN" localhost:8000/items/search?q=lenovo
curl -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"quantity": 3}' localhost:8000/items/1
```

## Тесты
`pytest` — 23 теста (API, сервис, кэш, авторизация); используется база `warehouse_api_test`
и Redis db 13.
