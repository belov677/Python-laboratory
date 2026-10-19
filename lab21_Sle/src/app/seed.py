"""Начальные данные: администратор (из переменных окружения) и демонстрационные справочники."""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.entities import Driver, Role, Route, User, Vehicle, VehicleCategory, VehicleStatus

log = logging.getLogger("app.seed")
ROUTES = [
    ("R-101", "Москва", "Санкт-Петербург", 710, 9.5, ["Тверь", "Великий Новгород"]),
    ("R-102", "Москва", "Казань", 820, 11.0, ["Владимир", "Нижний Новгород"]),
    ("R-103", "Москва", "Екатеринбург", 1790, 24.0, ["Казань", "Пермь"]),
    ("R-104", "Санкт-Петербург", "Мурманск", 1350, 19.0, ["Петрозаводск"]),
    ("R-105", "Екатеринбург", "Челябинск", 210, 3.0, []),
    ("R-106", "Краснодар", "Ростов-на-Дону", 280, 3.8, []),
    ("R-107", "Казань", "Самара", 360, 5.0, ["Ульяновск"]),
]
VEHICLES = [
    ("А101АА77", "ГАЗель Next", VehicleCategory.B, 1500),
    ("В202ВВ77", "Ford Transit", VehicleCategory.B, 2000),
    ("Е303ЕЕ78", "КАМАЗ 65115", VehicleCategory.C, 15000),
    ("К404КК16", "ГАЗон Next", VehicleCategory.C, 5000),
    ("М505ММ66", "Volvo FH + полуприцеп", VehicleCategory.CE, 40000),
]
DRIVERS = [
    ("Иванов Пётр Сергеевич", "77 01 100001", ["B"], "+79160000001"),
    ("Смирнов Олег Игоревич", "77 01 100002", ["B", "C"], "+79160000002"),
    ("Кузнецова Анна Викторовна", "78 02 200003", ["B", "C", "CE"], "+79210000003"),
    ("Попов Илья Андреевич", "16 03 300004", ["C"], "+79270000004"),
]


async def seed(container) -> None:
    settings = container.settings
    async with container.sessions() as session:
        if (
            settings.admin_email
            and settings.admin_password
            and not await session.scalar(select(User.id).where(User.role == Role.ADMIN))
        ):
            session.add(
                User(
                    email=settings.admin_email.lower(),
                    full_name="Диспетчер",
                    role=Role.ADMIN,
                    password_hash=hash_password(settings.admin_password),
                )
            )
            log.info("создан администратор %s", settings.admin_email)
        if settings.seed_demo_data and not await session.scalar(select(func.count(Route.id))):
            session.add_all(
                Route(code=c, origin=o, destination=d, distance_km=km, duration_h=h, waypoints=w)
                for c, o, d, km, h, w in ROUTES
            )
            session.add_all(Vehicle(plate=p, model=m, category=c, capacity_kg=kg) for p, m, c, kg in VEHICLES)
            session.add(
                Vehicle(
                    plate="Н606НН23",
                    model="Isuzu NQR",
                    category=VehicleCategory.C,
                    capacity_kg=5000,
                    status=VehicleStatus.MAINTENANCE,
                )
            )
            session.add_all(
                Driver(full_name=n, license_number=num, license_categories=cat, phone=ph) for n, num, cat, ph in DRIVERS
            )
            log.info("загружены демонстрационные справочники")
        await session.commit()
