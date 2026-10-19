"""Лабораторная №12, вариант 17 «Логистическая компания» — консольное приложение.

Запуск: python app/main.py [--reset]
"""
from __future__ import annotations

import argparse
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from database import DATABASE_URL, make_engine, make_session_factory
from models import Base, Shipment, ShipmentStatus
from services.exceptions import LogisticsError
from services.services import LogisticsService


def seed(service: LogisticsService) -> None:
    clients = [service.create_client(*c) for c in [
        ("ООО «ТехноМир»", "orders@technomir.ru", "Москва", "+7 495 100-10-10"),
        ("ИП Смирнова А.В.", "smirnova@mail.ru", "Казань", "+7 843 200-20-20"),
        ("АО «СтройДеталь»", "logistic@stroydetal.ru", "Екатеринбург", None),
        ("ООО «Фермер»", "farm@fermer.ru", "Краснодар", "+7 861 300-30-30"),
        ("Пётр Иванов", "p.ivanov@yandex.ru", "Москва", None),
    ]]
    cargo = [service.register_cargo(*c) for c in [
        ("Ноутбуки, 10 шт.", "хрупкий", 25, 550000), ("Офисные кресла, 5 шт.", "обычный", 60, 45000),
        ("Арматура 12 мм", "обычный", 800, 96000), ("Краска, 40 банок", "опасный", 120, 32000),
        ("Овощи, 30 ящиков", "обычный", 450, 60000), ("Посуда, 3 коробки", "хрупкий", 18, 12000),
        ("Книги, 6 коробок", "обычный", 90, 30000), ("Мониторы, 4 шт.", "хрупкий", 28, 120000),
    ]]
    plan = [(clients[0].id, "Москва", "Санкт-Петербург", 710, [cargo[0].id, cargo[7].id]),
            (clients[2].id, "Екатеринбург", "Пермь", 360, [cargo[2].id]),
            (clients[3].id, "Краснодар", "Москва", 1350, [cargo[4].id]),
            (clients[0].id, "Москва", "Казань", 820, [cargo[1].id, cargo[3].id]),
            (clients[1].id, "Казань", "Самара", 360, [cargo[5].id, cargo[6].id])]
    numbers = [service.create_shipment(*p).tracking_number for p in plan]
    service.change_status(numbers[0], ShipmentStatus.IN_TRANSIT, "Тверь", "Выехал со склада")
    service.change_status(numbers[0], ShipmentStatus.DELIVERED, "Санкт-Петербург", "Вручено")
    service.change_status(numbers[1], ShipmentStatus.IN_TRANSIT, "Кунгур")
    service.change_status(numbers[2], ShipmentStatus.CANCELLED, "Краснодар", "Отказ клиента")


def ask(prompt: str, cast=str):
    while True:
        value = input(prompt).strip()
        try:
            return cast(value)
        except ValueError:
            print("Некорректное значение, повторите ввод.")


def print_shipments(items: list[Shipment]) -> None:
    if not items:
        print("  ничего не найдено")
    for s in items:
        print(f"  {s.tracking_number}  {s.client.name if 'client' in s.__dict__ else '':20} "
              f"{s.origin:>13} → {s.destination:15} {s.distance_km:5} км "
              f"{s.cost:>10} руб.  {s.status.value}")


MENU = """
===== ЛОГИСТИКА (SQLAlchemy + PostgreSQL) =====
 1. Список клиентов (сортировка, страницы)   9. Изменить статус отправления
 2. Найти клиента по id                      10. Отслеживание отправления
 3. Поиск клиентов                           11. Отправления клиента (связь 1:N)
 4. Добавить клиента                         12. Фильтрация отправлений
 5. Изменить клиента                         13. Статистика (COUNT/SUM/AVG/MIN/MAX)
 6. Удалить клиента                          14. Показать SQL, который строит ORM
 7. Зарегистрировать груз                    15. Демонстрация ROLLBACK
 8. Создать отправление (транзакция)
 0. Выход"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="пересоздать таблицы и данные")
    args = parser.parse_args()
    engine = make_engine()
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    service = LogisticsService(make_session_factory(engine))
    if args.reset:
        seed(service)
    print(f"Подключено: {engine.url.render_as_string(hide_password=True)}")

    while True:
        print(MENU)
        choice = input("Выберите пункт: ").strip()
        if choice == "0":
            break
        try:
            if choice == "1":
                sort = input("Сортировка (name/city/id): ").strip() or "name"
                page = ask("Страница (по 3 записи): ", int)
                for c in service.list_clients(sort, page, 3):
                    print(f"  {c.id:3} {c.name:20} {c.city:15} {c.email}")
            elif choice == "2":
                c = service.get_client(ask("id клиента: ", int))
                print(f"  {c.id} {c.name} | {c.email} | {c.phone or '—'} | {c.city} | "
                      f"с {c.created_at:%d.%m.%Y}")
            elif choice == "3":
                for c in service.search_clients(input("Текст (имя/email/город): ")):
                    print(f"  {c.id:3} {c.name:20} {c.city:15} {c.email}")
            elif choice == "4":
                c = service.create_client(input("Имя: "), input("Email: "), input("Город: "),
                                          input("Телефон: ") or None)
                print("  Создан:", c)
            elif choice == "5":
                c = service.update_client(ask("id клиента: ", int), city=input("Новый город: "),
                                          phone=input("Новый телефон: "))
                print("  Изменён:", c, c.phone)
            elif choice == "6":
                service.delete_client(ask("id клиента: ", int))
                print("  Клиент удалён (каскадно удалены его отправления)")
            elif choice == "7":
                cargo = service.register_cargo(input("Описание: "), input("Тип (обычный/хрупкий/опасный): "),
                                               ask("Вес, кг: ", float), ask("Объявленная стоимость: ", float))
                print("  Зарегистрирован:", cargo)
            elif choice == "8":
                s = service.create_shipment(ask("id клиента: ", int), input("Откуда: "),
                                            input("Куда: "), ask("Расстояние, км: ", int),
                                            [int(x) for x in input("id грузов через пробел: ").split()])
                print(f"  Создано {s.tracking_number}: {len(s.cargos)} груз(а), "
                      f"{s.total_weight} кг, стоимость {s.cost} руб.")
            elif choice == "9":
                status = ShipmentStatus[input("Статус (IN_TRANSIT/DELIVERED/CANCELLED): ").strip()]
                s = service.change_status(input("Трек-номер: "), status, input("Местоположение: "))
                print(f"  {s.tracking_number}: статус «{s.status.value}»")
            elif choice == "10":
                s = service.track(input("Трек-номер: "))
                print(f"  {s.tracking_number} | {s.client.name} | {s.origin} → {s.destination} | "
                      f"{s.status.value} | {s.cost} руб.")
                print("  Грузы:", "; ".join(f"{c.description} ({c.weight_kg} кг)" for c in s.cargos))
                for e in s.events:
                    print(f"    {e.created_at:%d.%m %H:%M:%S}  {e.status.value:11} {e.location:16} "
                          f"{e.comment or ''}")
            elif choice == "11":
                for s in service.client_shipments(ask("id клиента: ", int)):
                    print(f"  {s.tracking_number} {s.origin} → {s.destination}, {s.status.value}, "
                          f"грузов: {len(s.cargos)}")
            elif choice == "12":
                status = input("Статус (пусто/CREATED/IN_TRANSIT/DELIVERED/CANCELLED): ").strip()
                city = input("Город отправления или назначения (пусто — любой): ").strip()
                min_cost = input("Стоимость от (пусто — любая): ").strip()
                sort = input("Сортировка (created/cost/distance): ").strip() or "created"
                print_shipments(service.filter_shipments(
                    status=ShipmentStatus[status] if status else None, city=city or None,
                    min_cost=float(min_cost) if min_cost else None,
                    created_after=datetime(2026, 1, 1), sort=sort,
                    descending=input("По убыванию? (д/н): ").strip() == "д"))
            elif choice == "13":
                stats = service.statistics()
                print(f"  клиентов: {stats['clients']}, грузов: {stats['cargos']}, "
                      f"отправлений: {stats['count']}")
                print(f"  стоимость: сумма {stats['sum']}, средняя {stats['avg']:.2f}, "
                      f"мин {stats['min']}, макс {stats['max']}")
                print("  по статусам:", stats["by_status"])
                for name, count, total in stats["top_clients"]:
                    print(f"  топ клиент: {name} — {count} отпр., {total} руб.")
            elif choice == "14":
                stmt = (select(Shipment).where(Shipment.status == ShipmentStatus.IN_TRANSIT,
                                               Shipment.cost >= 1000)
                        .order_by(Shipment.cost.desc()))
                print(stmt.compile(dialect=postgresql.dialect(),
                                   compile_kwargs={"literal_binds": True}))
            elif choice == "15":
                before = service.statistics()["count"]
                try:
                    service.create_shipment(1, "Москва", "Тула", 180, [1, 999])
                except LogisticsError as error:
                    print("  Ошибка внутри транзакции:", error)
                print(f"  Отправлений до: {before}, после: {service.statistics()['count']} — "
                      "изменения отменены (ROLLBACK)")
            else:
                print("Неизвестный пункт меню.")
        except KeyError as error:
            print(f"Ошибка: неизвестное значение {error}")
        except LogisticsError as error:
            print(f"Ошибка ({type(error).__name__}): {error}")


if __name__ == "__main__":
    main()
