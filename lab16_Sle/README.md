# СкладУчёт — лабораторная №16 (Django, вариант 17 «Склад»)

Веб-приложение складского учёта: товары, поставщики, склады, остатки, поставки, поиск и контроль
критических остатков.

## Технологии
Python 3.13, Django 6 (ORM, миграции, шаблоны, формы, Admin, auth), PostgreSQL 16 (psycopg 3),
Playwright (скриншоты), Docker Compose.

## Структура
```
lab16_Sle/
├── manage.py
├── config/            settings.py (настройки из переменных окружения), urls.py, wsgi.py, asgi.py
├── inventory/         приложение
│   ├── models.py      Warehouse, Supplier, Product, StockItem, Shipment
│   ├── forms.py       ModelForm + форма фильтров
│   ├── views.py       FBV (товары, остатки, статистика) и CBV (поставщики, поставки)
│   ├── urls.py, admin.py, middleware.py, tests.py
│   ├── management/commands/   seed, orm_demo, n1_demo
│   ├── templates/inventory/   шаблоны страниц
│   └── static/inventory/style.css
├── templates/         base.html, registration/login.html, 403.html, 404.html
└── requirements.txt, Dockerfile, docker-compose.yml, .env.example
```

## Установка и запуск
```bash
pip install -r requirements.txt
cp .env.example .env               # и экспортировать переменные
createdb warehouse_django          # или DB_ENGINE=sqlite
python manage.py migrate
python manage.py seed              # 3 склада, 6 поставщиков, 24 товара, 52 остатка, 14 поставок, 3 пользователя
python manage.py runserver
```
Администратор: `python manage.py createsuperuser` (seed уже создаёт admin / admin12345).
Пользователи: manager / manager12345 (группа «Менеджеры склада» — CRUD), viewer / viewer12345 (просмотр).

## URL
| URL | Страница |
|---|---|
| `/` | главная |
| `/products/?q=&category=&supplier=&critical=on&sort=-price&page=2` | товары |
| `/products/<id>/`, `/products/create/`, `/products/<id>/edit/`, `/products/<id>/delete/` | CRUD |
| `/stock/`, `/critical/` | остатки и критические остатки |
| `/suppliers/`, `/shipments/` | поставщики и поставки |
| `/statistics/` | статистика |
| `/admin/` | Django Admin |
| `/accounts/login/` | вход |

## Тесты и демонстрации
```bash
python manage.py test inventory       # 22 теста
python manage.py orm_demo             # запросы ORM
python manage.py n1_demo              # проблема N+1
```

## Docker
`docker compose up --build`, затем `docker compose exec web python manage.py seed`.
