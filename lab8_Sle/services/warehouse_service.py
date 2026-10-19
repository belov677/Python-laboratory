"""Бизнес-логика склада. Зависит только от абстракций Repository и PickingStrategy."""
from __future__ import annotations

from datetime import date

from factories.entity_factory import EntityFactory
from interfaces.repository import Repository
from interfaces.strategies import PickingStrategy
from models.entities import Batch, InsufficientStockError, Product, Supply
from models.enums import SupplyStatus


class WarehouseService:
    def __init__(self, repository: Repository, strategy: PickingStrategy) -> None:
        self.repository = repository
        self.strategy = strategy

    def set_strategy(self, strategy: PickingStrategy) -> None:
        self.strategy = strategy

    # ----- выборки -----
    def products(self) -> list[Product]:
        return [e for e in self.repository.get_all() if isinstance(e, Product)]

    def batches(self, sku: str | None = None) -> list[Batch]:
        return [e for e in self.repository.get_all()
                if isinstance(e, Batch) and (sku is None or e.sku == sku)]

    def stock(self, sku: str) -> int:
        return sum(b.quantity for b in self.batches(sku))

    def find_product(self, sku: str) -> Product:
        for p in self.products():
            if p.sku == sku:
                return p
        raise ValueError(f"Товар {sku} не зарегистрирован")

    # ----- операции -----
    def add_product(self, sku: str, name: str, price: float) -> Product:
        if any(p.sku == sku for p in self.products()):
            raise ValueError(f"Товар {sku} уже существует")
        return self.repository.add(EntityFactory.create(
            "product", id=self.repository.next_id(), sku=sku, name=name, price=price))

    def receive_batch(self, sku: str, quantity: int, expiry: date, priority: int = 0,
                      supplier: str = "—") -> Batch:
        self.find_product(sku)
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным")
        order = max((b.received_order for b in self.batches()), default=0) + 1
        batch = self.repository.add(EntityFactory.create(
            "batch", id=self.repository.next_id(), sku=sku, quantity=quantity,
            received_order=order, expiry_date=expiry, priority=priority))
        self.repository.add(EntityFactory.create(
            "supply", id=self.repository.next_id(), supplier=supplier,
            batch_ids=[batch.id], status=SupplyStatus.RECEIVED))
        return batch

    def remove_batch(self, batch_id: int) -> None:
        self.repository.delete(batch_id)
        for supply in [e for e in self.repository.get_all() if isinstance(e, Supply)]:
            if batch_id in supply.batch_ids:
                supply.status = SupplyStatus.CANCELLED
        self.repository.save()

    def ship(self, sku: str, quantity: int) -> list[tuple[int, int]]:
        """Отгрузка: партии отбираются в порядке, заданном текущей стратегией."""
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным")
        if self.stock(sku) < quantity:
            raise InsufficientStockError(f"Недостаточно {sku}: есть {self.stock(sku)}, "
                                         f"требуется {quantity}")
        taken = []
        for batch in self.strategy.order([b for b in self.batches(sku) if b.quantity > 0]):
            if quantity == 0:
                break
            part = min(quantity, batch.quantity)
            batch.quantity -= part
            quantity -= part
            taken.append((batch.id, part))
        self.repository.save()
        return taken

    def restore(self, taken: list[tuple[int, int]]) -> None:
        for batch_id, part in taken:
            self.repository.get(batch_id).quantity += part
        self.repository.save()

    def expiring(self, today: date, days: int) -> list[Batch]:
        return sorted((b for b in self.batches()
                       if b.quantity > 0 and (b.expiry_date - today).days <= days),
                      key=lambda b: b.expiry_date)
