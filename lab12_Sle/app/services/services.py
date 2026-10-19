"""Сервисный слой: бизнес-логика и границы транзакций."""
from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from models import Client, Shipment, ShipmentStatus, TrackingEvent
from repositories.repositories import CargoRepository, ClientRepository, ShipmentRepository
from services.exceptions import (DuplicateError, InvalidStatusError, NotFoundError,
                                 ValidationError)

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
TRANSITIONS = {
    ShipmentStatus.CREATED: {ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED},
    ShipmentStatus.IN_TRANSIT: {ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED},
    ShipmentStatus.DELIVERED: set(),
    ShipmentStatus.CANCELLED: set(),
}
BASE_PRICE = Decimal("500")
RATE_PER_KG_KM = Decimal("0.02")
SURCHARGE = {"хрупкий": Decimal("1.3"), "опасный": Decimal("1.5")}


class LogisticsService:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    @contextmanager
    def transaction(self):
        """Одна транзакция: commit при успехе, rollback при любой ошибке."""
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except IntegrityError as error:
                session.rollback()
                text = str(error.orig)
                if "unique" in text.lower() or "duplicate" in text.lower():
                    raise DuplicateError("Нарушено ограничение уникальности: " +
                                         text.splitlines()[0]) from None
                raise ValidationError("Нарушено ограничение целостности: " +
                                      text.splitlines()[0]) from None
            except Exception:
                session.rollback()
                raise

    # ---------- клиенты ----------
    @staticmethod
    def _validate_client(name: str, email: str, city: str) -> None:
        if not name.strip() or not city.strip():
            raise ValidationError("Имя и город обязательны")
        if not EMAIL.match(email):
            raise ValidationError(f"Некорректный email: {email}")

    def create_client(self, name: str, email: str, city: str, phone: str | None = None) -> Client:
        self._validate_client(name, email, city)
        with self.transaction() as session:
            return ClientRepository(session).create(name=name.strip(), email=email.lower(),
                                                    city=city.strip(), phone=phone)

    def get_client(self, client_id: int) -> Client:
        with self.session_factory() as session:
            client = ClientRepository(session).get_by_id(client_id)
            if client is None:
                raise NotFoundError(f"Клиент id={client_id} не найден")
            return client

    def list_clients(self, sort: str = "name", page: int | None = None, page_size: int = 5):
        column = {"name": Client.name, "city": Client.city, "id": Client.id}[sort]
        with self.session_factory() as session:
            return ClientRepository(session).get_all(order_by=column, page=page,
                                                     page_size=page_size)

    def search_clients(self, text: str) -> list[Client]:
        with self.session_factory() as session:
            return ClientRepository(session).search(text)

    def update_client(self, client_id: int, **fields) -> Client:
        fields = {k: v for k, v in fields.items() if v}
        if "email" in fields and not EMAIL.match(fields["email"]):
            raise ValidationError(f"Некорректный email: {fields['email']}")
        with self.transaction() as session:
            repo = ClientRepository(session)
            client = repo.get_by_id(client_id)
            if client is None:
                raise NotFoundError(f"Клиент id={client_id} не найден")
            return repo.update(client, **fields)

    def delete_client(self, client_id: int) -> None:
        with self.transaction() as session:
            repo = ClientRepository(session)
            client = repo.get_by_id(client_id)
            if client is None:
                raise NotFoundError(f"Клиент id={client_id} не найден")
            repo.delete(client)

    # ---------- грузы ----------
    def register_cargo(self, description: str, cargo_type: str, weight_kg: float,
                       declared_value: float = 0):
        if weight_kg <= 0:
            raise ValidationError("Вес груза должен быть положительным")
        with self.transaction() as session:
            return CargoRepository(session).create(
                description=description, cargo_type=cargo_type,
                weight_kg=Decimal(str(weight_kg)), declared_value=Decimal(str(declared_value)))

    # ---------- отправления ----------
    @staticmethod
    def calculate_cost(cargos, distance_km: int) -> Decimal:
        cost = BASE_PRICE
        for cargo in cargos:
            cost += cargo.weight_kg * distance_km * RATE_PER_KG_KM * \
                SURCHARGE.get(cargo.cargo_type, Decimal("1"))
        return cost.quantize(Decimal("0.01"))

    def create_shipment(self, client_id: int, origin: str, destination: str, distance_km: int,
                        cargo_ids: list[int]) -> Shipment:
        """Транзакция: отправление + привязка грузов + расчёт стоимости + первое событие."""
        if distance_km <= 0:
            raise ValidationError("Расстояние должно быть положительным")
        if not cargo_ids:
            raise ValidationError("Отправление должно содержать хотя бы один груз")
        with self.transaction() as session:
            if ClientRepository(session).get_by_id(client_id) is None:
                raise NotFoundError(f"Клиент id={client_id} не найден")
            shipments = ShipmentRepository(session)
            number = f"LG-2026-{shipments.count() + 1:04d}"
            shipment = shipments.create(tracking_number=number, client_id=client_id,
                                        origin=origin, destination=destination,
                                        distance_km=distance_km)
            cargos = CargoRepository(session).get_many(cargo_ids)
            missing = set(cargo_ids) - {c.id for c in cargos}
            if missing:                                    # → rollback всей операции
                raise NotFoundError(f"Грузы не найдены: {sorted(missing)}")
            shipment.cargos.extend(cargos)
            shipment.cost = self.calculate_cost(cargos, distance_km)
            session.add(TrackingEvent(shipment=shipment, status=ShipmentStatus.CREATED,
                                      location=origin, comment="Отправление оформлено"))
            session.flush()
            return shipment

    def change_status(self, tracking: str, new_status: ShipmentStatus, location: str,
                      comment: str = "") -> Shipment:
        with self.transaction() as session:
            shipment = ShipmentRepository(session).get_by_tracking(tracking)
            if shipment is None:
                raise NotFoundError(f"Отправление {tracking} не найдено")
            if new_status not in TRANSITIONS[shipment.status]:
                raise InvalidStatusError(
                    f"Переход «{shipment.status.value}» → «{new_status.value}» недопустим")
            shipment.status = new_status
            if new_status is ShipmentStatus.DELIVERED:
                shipment.delivered_at = datetime.now()
            session.add(TrackingEvent(shipment=shipment, status=new_status, location=location,
                                      comment=comment or None))
            return shipment

    def track(self, tracking: str) -> Shipment:
        with self.session_factory() as session:
            shipment = ShipmentRepository(session).get_by_tracking(tracking)
            if shipment is None:
                raise NotFoundError(f"Отправление {tracking} не найдено")
            return shipment

    def client_shipments(self, client_id: int) -> list[Shipment]:
        self.get_client(client_id)
        with self.session_factory() as session:
            return ShipmentRepository(session).by_client(client_id)

    def filter_shipments(self, **criteria) -> list[Shipment]:
        with self.session_factory() as session:
            return ShipmentRepository(session).filter(**criteria)

    def statistics(self) -> dict:
        with self.session_factory() as session:
            stats = ShipmentRepository(session).aggregates()
            stats["clients"] = ClientRepository(session).count()
            stats["cargos"] = CargoRepository(session).count()
            return stats
