"""Бизнес-логика: создание, изменение и отслеживание отправлений."""
from __future__ import annotations

import logging
import re
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.models import Cargo, Client, Shipment, Status, TrackingEvent
from repositories.repositories import SORTS, ClientRepository, ShipmentRepository
from services.exceptions import ConflictError, NotFoundError, ValidationError

log = logging.getLogger("logistics.service")
CARGO_TYPES = {"обычный": Decimal("1.0"), "хрупкий": Decimal("1.3"), "опасный": Decimal("1.5")}
TRANSITIONS = {Status.CREATED: {Status.IN_TRANSIT, Status.CANCELLED},
               Status.IN_TRANSIT: {Status.DELIVERED, Status.CANCELLED},
               Status.DELIVERED: set(), Status.CANCELLED: set()}
EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


def calc_cost(distance: int, cargos: list[dict]) -> Decimal:
    """500 руб. + вес × км × 0,02 × коэффициент типа груза."""
    total = Decimal(500)
    for c in cargos:
        total += Decimal(str(c["weight_kg"])) * distance * Decimal("0.02") * CARGO_TYPES[c["cargo_type"]]
    return total.quantize(Decimal("0.01"))


class ShipmentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.clients = ClientRepository(session)
        self.shipments = ShipmentRepository(session)

    # ---------- валидация ----------
    def _validate(self, data: dict) -> dict:
        errors: dict[str, str] = {}
        clean: dict = {}
        try:
            clean["client_id"] = int(data.get("client_id") or 0)
            if not self.clients.get(clean["client_id"]):
                errors["client_id"] = "Выберите существующего клиента"
        except (TypeError, ValueError):
            errors["client_id"] = "Клиент указан неверно"
        for field, title in (("origin", "Город отправления"), ("destination", "Город назначения")):
            value = str(data.get(field) or "").strip()
            if len(value) < 2:
                errors[field] = f"{title}: не менее 2 символов"
            clean[field] = value
        if clean["origin"] and clean["origin"].lower() == clean["destination"].lower():
            errors["destination"] = "Город назначения совпадает с городом отправления"
        try:
            clean["distance_km"] = int(data.get("distance_km"))
            if not 0 < clean["distance_km"] <= 10000:
                raise ValueError
        except (TypeError, ValueError):
            errors["distance_km"] = "Расстояние — целое число от 1 до 10000"
        cargos = []
        for i, c in enumerate(data.get("cargos") or [], 1):
            description = str(c.get("description") or "").strip()
            if not description:
                continue
            try:
                weight = Decimal(str(c.get("weight_kg")).replace(",", "."))
                if weight <= 0:
                    raise ValueError
            except Exception:
                errors[f"cargo{i}"] = f"Груз {i}: вес должен быть положительным числом"
                continue
            if c.get("cargo_type") not in CARGO_TYPES:
                errors[f"cargo{i}"] = f"Груз {i}: неизвестный тип"
                continue
            cargos.append({"description": description, "weight_kg": weight,
                           "cargo_type": c["cargo_type"]})
        if not cargos and not any(k.startswith("cargo") for k in errors):
            errors["cargos"] = "Добавьте хотя бы один груз"
        clean["cargos"] = cargos
        if errors:
            raise ValidationError(errors)
        return clean

    # ---------- CRUD ----------
    def list(self, search=None, status=None, client_id=None, sort="created", order="desc",
             page=1, page_size=5):
        if sort not in SORTS:
            sort = "created"
        status_obj = Status[status] if status in Status.__members__ else None
        items, total = self.shipments.query(search, status_obj, client_id, sort,
                                            "asc" if order == "asc" else "desc",
                                            max(page, 1), page_size)
        pages = max((total + page_size - 1) // page_size, 1)
        return items, total, pages

    def get(self, shipment_id: int) -> Shipment:
        shipment = self.shipments.get(shipment_id)
        if not shipment:
            raise NotFoundError(f"Отправление #{shipment_id} не найдено")
        return shipment

    def track(self, tracking: str) -> Shipment:
        found = self.shipments.by_tracking(tracking.strip().upper())
        if not found:
            raise NotFoundError(f"Трек-номер {tracking} не найден")
        return self.get(found.id)

    def create(self, data: dict) -> Shipment:
        clean = self._validate(data)
        number = (data.get("tracking_number") or "").strip().upper() or self.shipments.next_number()
        if self.shipments.by_tracking(number):
            raise ConflictError(f"Отправление с трек-номером {number} уже существует")
        shipment = Shipment(tracking_number=number, client_id=clean["client_id"],
                            origin=clean["origin"], destination=clean["destination"],
                            distance_km=clean["distance_km"],
                            cost=calc_cost(clean["distance_km"], clean["cargos"]))
        shipment.cargos = [Cargo(**c) for c in clean["cargos"]]
        shipment.events = [TrackingEvent(status=Status.CREATED, location=clean["origin"])]
        try:
            self.shipments.add(shipment)
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ConflictError("Нарушение ограничений БД") from error
        log.info("Создано отправление %s (стоимость %s)", number, shipment.cost)
        return self.get(shipment.id)

    def update(self, shipment_id: int, data: dict) -> Shipment:
        shipment = self.get(shipment_id)
        if shipment.status != Status.CREATED:
            raise ConflictError("Редактировать можно только отправление в статусе «создано»")
        clean = self._validate(data)
        shipment.client_id = clean["client_id"]
        shipment.origin, shipment.destination = clean["origin"], clean["destination"]
        shipment.distance_km = clean["distance_km"]
        shipment.cargos = [Cargo(**c) for c in clean["cargos"]]
        shipment.cost = calc_cost(clean["distance_km"], clean["cargos"])
        self.session.commit()
        log.info("Изменено отправление %s", shipment.tracking_number)
        return self.get(shipment_id)

    def change_status(self, shipment_id: int, status: str, location: str) -> Shipment:
        shipment = self.get(shipment_id)
        if status not in Status.__members__:
            raise ValidationError({"status": f"Неизвестный статус {status}"})
        new = Status[status]
        if new not in TRANSITIONS[shipment.status]:
            raise ConflictError(f"Переход «{shipment.status.value}» → «{new.value}» недопустим")
        if len((location or "").strip()) < 2:
            raise ValidationError({"location": "Укажите местоположение"})
        shipment.status = new
        shipment.events.append(TrackingEvent(status=new, location=location.strip()))
        self.session.commit()
        log.info("Отправление %s: статус %s (%s)", shipment.tracking_number, new.name, location)
        return self.get(shipment_id)

    def delete(self, shipment_id: int) -> None:
        shipment = self.get(shipment_id)
        if shipment.status == Status.IN_TRANSIT:
            raise ConflictError("Нельзя удалить отправление, находящееся в пути")
        self.shipments.delete(shipment)
        self.session.commit()
        log.info("Удалено отправление %s", shipment.tracking_number)

    # ---------- клиенты ----------
    def list_clients(self) -> list[Client]:
        return self.clients.all()

    def get_client(self, client_id: int) -> Client:
        client = self.clients.get(client_id)
        if not client:
            raise NotFoundError(f"Клиент #{client_id} не найден")
        return client

    def create_client(self, data: dict) -> Client:
        errors = {}
        name = str(data.get("name") or "").strip()
        email = str(data.get("email") or "").strip().lower()
        city = str(data.get("city") or "").strip()
        if len(name) < 2:
            errors["name"] = "Имя: не менее 2 символов"
        if not EMAIL.match(email):
            errors["email"] = "Некорректный email"
        if len(city) < 2:
            errors["city"] = "Укажите город"
        if errors:
            raise ValidationError(errors)
        if self.clients.by_email(email):
            raise ConflictError(f"Клиент с email {email} уже существует")
        client = self.clients.add(Client(name=name, email=email, city=city,
                                         phone=(data.get("phone") or "").strip() or None))
        self.session.commit()
        log.info("Создан клиент %s", email)
        return client

    def stats(self) -> dict:
        return {"clients": len(self.clients.all()), "by_status": self.shipments.counts()}
