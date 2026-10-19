"""Repository-слой: запросы к БД через SQLAlchemy ORM (без ручного SQL)."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from models import Cargo, Client, Shipment, ShipmentStatus

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **fields) -> T:
        obj = self.model(**fields)
        self.session.add(obj)
        self.session.flush()            # получить id до commit
        return obj

    def get_by_id(self, obj_id: int) -> T | None:
        return self.session.get(self.model, obj_id)

    def get_all(self, order_by=None, page: int | None = None, page_size: int = 10) -> list[T]:
        stmt = select(self.model).order_by(order_by if order_by is not None else self.model.id)
        if page is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(stmt))

    def update(self, obj: T, **fields) -> T:
        for key, value in fields.items():
            setattr(obj, key, value)
        self.session.flush()
        return obj

    def delete(self, obj: T) -> None:
        self.session.delete(obj)
        self.session.flush()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model))


class ClientRepository(BaseRepository[Client]):
    model = Client

    def search(self, text: str) -> list[Client]:
        pattern = f"%{text}%"
        stmt = select(Client).where(or_(Client.name.ilike(pattern), Client.email.ilike(pattern),
                                        Client.city.ilike(pattern))).order_by(Client.name)
        return list(self.session.scalars(stmt))

    def get_by_email(self, email: str) -> Client | None:
        return self.session.scalar(select(Client).where(Client.email == email))


class CargoRepository(BaseRepository[Cargo]):
    model = Cargo

    def get_many(self, ids: list[int]) -> list[Cargo]:
        return list(self.session.scalars(select(Cargo).where(Cargo.id.in_(ids))))


class ShipmentRepository(BaseRepository[Shipment]):
    model = Shipment

    def get_by_tracking(self, tracking: str) -> Shipment | None:
        stmt = (select(Shipment).where(Shipment.tracking_number == tracking)
                .options(selectinload(Shipment.events), selectinload(Shipment.cargos),
                         selectinload(Shipment.client)))
        return self.session.scalar(stmt)

    def filter(self, status: ShipmentStatus | None = None, city: str | None = None,
               min_cost: float | None = None, created_after: datetime | None = None,
               sort: str = "created", descending: bool = True) -> list[Shipment]:
        conditions = []
        if status is not None:
            conditions.append(Shipment.status == status)
        if city:
            conditions.append(or_(Shipment.origin.ilike(city), Shipment.destination.ilike(city)))
        if min_cost is not None:
            conditions.append(Shipment.cost >= min_cost)
        if created_after is not None:
            conditions.append(Shipment.created_at >= created_after)
        column = {"created": Shipment.created_at, "cost": Shipment.cost,
                  "distance": Shipment.distance_km}[sort]
        stmt = (select(Shipment).where(and_(*conditions))
                .order_by(column.desc() if descending else column.asc(), Shipment.id)
                .options(selectinload(Shipment.client)))     # без проблемы N+1
        return list(self.session.scalars(stmt))

    def by_client(self, client_id: int) -> list[Shipment]:
        stmt = (select(Shipment).where(Shipment.client_id == client_id)
                .order_by(Shipment.created_at).options(selectinload(Shipment.cargos)))
        return list(self.session.scalars(stmt))

    def aggregates(self) -> dict:
        row = self.session.execute(select(
            func.count(Shipment.id), func.sum(Shipment.cost), func.avg(Shipment.cost),
            func.min(Shipment.cost), func.max(Shipment.cost))).one()
        by_status = dict(self.session.execute(
            select(Shipment.status, func.count()).group_by(Shipment.status)).all())
        top = self.session.execute(
            select(Client.name, func.count(Shipment.id).label("n"), func.sum(Shipment.cost))
            .join(Shipment).group_by(Client.name).order_by(func.sum(Shipment.cost).desc())
            .limit(3)).all()
        return {"count": row[0], "sum": row[1], "avg": row[2], "min": row[3], "max": row[4],
                "by_status": {s.value: n for s, n in by_status.items()}, "top_clients": top}
