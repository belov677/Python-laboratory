# Лабораторная работа №6 — «Склад» (вариант 17)

Консольное приложение управления складскими товарами, складами и поставками.

## Запуск
```
python main.py
```
Требуется Python 3.10+, сторонние библиотеки не используются.

## Структура
| Файл | Назначение |
|---|---|
| main.py | консольное меню (формируется автоматически по декоратору @command) |
| models.py | dataclass-модели Entity, Product, Warehouse, Delivery и Enum DeliveryStatus |
| services.py | бизнес-логика WarehouseService |
| decorators.py | log_call, measure_time, require_status(...), repeat(n), command(...) |
| context.py | контекстные менеджеры StockTransaction и OperationLogger |
| protocols.py | Protocol Reportable и функция print_report |
| introspection.py | функция inspect_object |
| exceptions.py | пользовательские исключения |

Журнал операций записывается в `operations.log`.
