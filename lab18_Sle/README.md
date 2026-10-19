# Лабораторная №18 — автоматизированное тестирование (вариант 17 «Склад»)

Приложение складского учёта (Repository → Service → Interface) и набор тестов pytest:
поступление, списание, перемещение, поиск, контроль отрицательного остатка.

## Структура
```
src/models/entities.py               Product, Warehouse, Movement, MovementType
src/repositories/base.py             интерфейс хранилища (Protocol)
src/repositories/sqlite_repository.py SQLite, транзакции, CHECK quantity >= 0
src/services/inventory_service.py    бизнес-логика
src/services/exceptions.py, notifier.py
src/main.py                          консольный интерфейс
src/api/app.py                       REST API (FastAPI)
tests/unit/                          unit-тесты (Mock, patch, параметризация)
tests/integration/                   Service → Repository → SQLite
tests/api/                           HTTP-эндпоинты
mutation_test.py                     мутационное тестирование сервиса
.github/workflows/ci.yml             CI
```

## Запуск
```bash
pip install -r requirements.txt
python -m src.main                       # консоль (БД в памяти с демо-данными)
uvicorn src.api.app:app                  # REST API, документация /docs
python -m pytest -v                      # все тесты
python -m pytest --cov=src --cov-report=term-missing
python -m pytest tests/unit              # только unit
python mutation_test.py                  # мутационное тестирование
```
