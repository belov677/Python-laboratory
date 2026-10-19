from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from models.models import Client, Shipment, Status

SORTS = {"created": Shipment.created_at, "cost": Shipment.cost,
         "distance": Shipment.distance_km, "tracking": Shipment.tracking_number}


class ClientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def all(self) -> list[Client]:
        return list(self.session.scalars(select(Client).order_by(Client.name)))

    def get(self, client_id: int) -> Client | None:
        return self.session.get(Client, client_id)

    def by_email(self, email: str) -> Client | None:
        return self.session.scalar(select(Client).where(Client.email == email))

    def add(self, client: Client) -> Client:
        self.session.add(client)
        self.session.flush()
        return client


class ShipmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def query(self, search: str | None, status: Status | None, client_id: int | None,
              sort: str, order: str, page: int, page_size: int) -> tuple[list[Shipment], int]:
        stmt = select(Shipment).options(selectinload(Shipment.client),
                                        selectinload(Shipment.cargos))
        if search:
            p = f"%{search}%"
            stmt = stmt.where(or_(Shipment.tracking_number.ilike(p), Shipment.origin.ilike(p),
                                  Shipment.destination.ilike(p)))
        if status:
            stmt = stmt.where(Shipment.status == status)
        if client_id:
            stmt = stmt.where(Shipment.client_id == client_id)
        total = self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        column = SORTS[sort]
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Shipment.id)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(stmt)), total

    def get(self, shipment_id: int) -> Shipment | None:
        return self.session.scalar(
            select(Shipment).where(Shipment.id == shipment_id)
            .options(selectinload(Shipment.client), selectinload(Shipment.cargos),
                     selectinload(Shipment.events)))

    def by_tracking(self, tracking: str) -> Shipment | None:
        return self.session.scalar(select(Shipment).where(Shipment.tracking_number == tracking))

    def add(self, shipment: Shipment) -> Shipment:
        self.session.add(shipment)
        self.session.flush()
        return shipment

    def delete(self, shipment: Shipment) -> None:
        self.session.delete(shipment)

    def next_number(self) -> str:
        last = self.session.scalar(select(func.max(Shipment.id))) or 0
        return f"LG-{last + 1:05d}"

    def counts(self) -> dict:
        rows = self.session.execute(select(Shipment.status, func.count()).group_by(Shipment.status))
        return {s.value: n for s, n in rows}
