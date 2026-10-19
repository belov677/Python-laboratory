# Лабораторная №15 — веб-приложение «Логистическая компания» (вариант 17)

Flask + Jinja2 + SQLAlchemy + PostgreSQL. Создание и отслеживание отправлений клиентов.

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env            # при необходимости изменить DATABASE_URL
cd app
RESET_DB=1 python app.py        # пересоздать таблицы и загрузить демо-данные
# http://127.0.0.1:5015/
```
Docker: `docker compose up --build`.

## Страницы
| URL | Назначение |
|---|---|
| `/` | главная: статистика, отслеживание, последние отправления |
| `/shipments` | список: поиск `q`, фильтры `status`, `client_id`, сортировка `sort=created/cost/distance`, `order`, `page` |
| `/shipments/<id>` | карточка, грузы, история, смена статуса |
| `/shipments/new`, `/shipments/<id>/edit`, `/shipments/<id>/delete` | создание, редактирование, удаление |
| `/track?number=LG-00001` | отслеживание по трек-номеру |
| `/clients`, `/clients/<id>`, `/clients/new` | клиенты |

## REST API
`GET/POST /api/shipments`, `GET/PUT/DELETE /api/shipments/<id>`, `POST /api/shipments/<id>/status`,
`GET /api/track/<number>`, `GET/POST /api/clients`, `GET /api/clients/<id>/shipments`, `GET /health`.

Коды ошибок: 400 (валидация, CSRF), 404, 409 (дубликат, недопустимый переход статуса), 500.

## Тесты
```bash
python -m pytest -v --cov=app tests     # БД logistics_web_test
```
