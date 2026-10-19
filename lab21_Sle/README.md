# Логистическая система — итоговый проект (лабораторная №21, вариант 17)

**Назначение.** Приём заказов на перевозку грузов и планирование доставок: клиент оформляет заказ,
диспетчер подбирает машину и водителя, система проверяет грузоподъёмность, категории прав и занятость,
рассчитывает стоимость, отслеживает выполнение рейса и уведомляет клиента.

**Уровень сложности:** B (монолит + PostgreSQL + Redis + RabbitMQ + фоновый worker).

## Функциональность
- регистрация и вход (JWT), роли **USER** (клиент) и **ADMIN** (диспетчер);
- справочники: маршруты (кэш Redis), транспорт, водители — CRUD для ADMIN;
- заказы: создание, поиск с фильтрами/сортировкой/пагинацией, изменение, отмена; клиент видит только свои;
- доставки: подбор свободных ресурсов, назначение рейса, запуск, завершение, отмена; отслеживание заказа;
- события (Transactional Outbox → RabbitMQ) и уведомления клиентам фоновым worker (отправка e-mail имитируется);
- /health (БД, Redis, брокер, очередь outbox), /metrics, документация /swagger и /redoc.

## Бизнес-правила
1. Подача — только в будущем; перевозка — только по существующему маршруту; срок доставки не короче времени в пути.
2. Груз не превышает грузоподъёмность машины; машина не на обслуживании.
3. У водителя есть категория прав для машины; водитель активен.
4. Машина и водитель не заняты в окне рейса (проверка в сервисе + EXCLUDE-ограничение PostgreSQL).
5. Рейс должен завершиться до срока заказа; изменить заказ можно только в статусе NEW, отменить — до начала перевозки.
6. Переходы рейса: PLANNED → IN_TRANSIT → DELIVERED, PLANNED → CANCELLED.

## Архитектура
`docs/architecture.png`, `docs/er.png`. Слои: `api` (роутеры, зависимости) → `services` (правила) →
`repositories` (SQLAlchemy) → PostgreSQL; `core` — безопасность, кэш, события, журнал и метрики.

## Стек
Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2 (async, psycopg 3), Alembic, PostgreSQL 16, Redis 7,
RabbitMQ 3.12 (aio-pika), PyJWT, pytest, ruff, Docker, Docker Compose, GitHub Actions.

## Требования
Docker 24+ с Compose v2. Для разработки без Docker: Python 3.13, PostgreSQL 16 (расширение btree_gist), Redis, RabbitMQ.

## Установка и запуск
```bash
git clone <repository> && cd lab21_Sle
cp .env.example .env              # или ./scripts/make_env.sh — случайные секреты
docker compose up --build -d
docker compose ps                  # app, worker, db, redis, rabbitmq
open http://localhost:8000/swagger
```
Диспетчер создаётся при старте из `ADMIN_EMAIL` / `ADMIN_PASSWORD`; демонстрационные справочники — при `SEED_DEMO_DATA=1`.
Схема БД создаётся миграциями Alembic при запуске контейнера `app` (`alembic upgrade head`).

## Переменные окружения
| Переменная | Назначение |
|---|---|
| POSTGRES_PASSWORD, RABBITMQ_PASSWORD | пароли БД и брокера (Compose) |
| DATABASE_URL, REDIS_URL, BROKER_URL | подключения (для запуска без Docker) |
| JWT_SECRET, JWT_TTL_MINUTES | подпись и срок жизни токенов |
| ADMIN_EMAIL, ADMIN_PASSWORD | учётная запись диспетчера |
| CACHE_TTL_SECONDS, SEED_DEMO_DATA, LOG_LEVEL, PUBLIC_PORT | прочие настройки |
| TEST_DATABASE_URL | отдельная БД для тестов |

Файл `.env` не хранится в Git.

## Тесты
```bash
pip install -r requirements-dev.txt
python -m pytest --cov            # 66 тестов: unit, интеграционные (PostgreSQL, RabbitMQ), API; покрытие ≈ 92 %
./ci_local.sh                     # все этапы CI локально
python demo.py                    # демонстрационный сценарий против запущенной системы
```

## Docker
Один образ (многоэтапная сборка, пользователь без прав root) для `app` (`api`: миграции + uvicorn) и `worker`.
`docker build -t logistics-final/app .`

## API (основное)
| Метод | Путь | Роль |
|---|---|---|
| POST | /auth/register, /auth/login | — |
| GET | /auth/me, /auth/me/notifications | USER, ADMIN |
| GET | /routes, /routes/{id} (X-Cache: HIT/MISS/BYPASS) | USER, ADMIN |
| POST/PUT/DELETE | /routes, /vehicles, /drivers | ADMIN |
| POST, GET | /orders (status, city, sort, page, size) | USER (свои), ADMIN (все) |
| GET, PUT, DELETE | /orders/{id}; GET /orders/{id}/tracking | владелец или ADMIN |
| GET | /deliveries/available?order_id= | ADMIN |
| POST, GET | /deliveries; PATCH /deliveries/{id}/status | ADMIN |
| GET | /health, /metrics, /swagger, /redoc | — |

Ошибки: `{"error": "VEHICLE_BUSY", "message": "Транспорт К404КК16 занят в это время"}`; коды 400/401/403/404/409/422/500.

## CI
`.github/workflows/lab21-ci.yml`: lint (ruff + bandit) → test (PostgreSQL service, pytest, покрытие ≥ 85 %,
проверка миграций) → build-and-smoke (docker compose build/up, smoke-тест) → publish (GHCR, только main).

## Ограничения
Уведомления не отправляются во внешние системы (имитация); нет оплаты и геолокации; одна БД — горизонтальное
масштабирование ограничено ей; маршрут выбирается из справочника (без построения по карте).
