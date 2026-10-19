"""Бизнес-логика складской системы (без ввода-вывода с консоли)."""
from __future__ import annotations

from decorators import log_call, measure_time, require_status
from exceptions import CapacityExceededError, EntityNotFoundError, InvalidStatusTransitionError
from models import Delivery, DeliveryStatus, Entity, Product, Warehouse


class WarehouseService:
    def __init__(self) -> None:
        self.entities: list[Entity] = []

    # ---------- общие операции ----------
    def next_id(self) -> int:
        return max((e.id for e in self.entities), default=0) + 1

    @log_call
    def add(self, entity: Entity) -> Entity:
        if any(e.id == entity.id for e in self.entities):
            raise ValueError(f"Объект с id={entity.id} уже существует")
        if isinstance(entity, Product) and entity.warehouse_id is not None:
            warehouse = self.get(entity.warehouse_id, Warehouse)
            self._check_capacity(warehouse, entity.quantity)
            warehouse.product_ids.append(entity.id)
        self.entities.append(entity)
        return entity

    def get(self, entity_id: int, kind: type[Entity] = Entity) -> Entity:
        for entity in self.entities:
            if entity.id == entity_id and isinstance(entity, kind):
                return entity
        raise EntityNotFoundError(f"{kind.__name__} с id={entity_id} не найден")

    def get_delivery(self, delivery_id: int) -> Delivery:
        return self.get(delivery_id, Delivery)

    @log_call
    def remove(self, entity_id: int) -> Entity:
        entity = self.get(entity_id)
        self.entities.remove(entity)
        for w in self.of_type(Warehouse):
            if entity_id in w.product_ids:
                w.product_ids.remove(entity_id)
        return entity

    def find(self, text: str) -> list[Entity]:
        text = text.lower()
        return [e for e in self.entities
                if text in e.name.lower() or text in getattr(e, "sku", "").lower()]

    def of_type(self, kind: type[Entity]) -> list:
        return [e for e in self.entities if isinstance(e, kind)]

    # ---------- поставки ----------
    def change_status(self, delivery_id: int, new_status: DeliveryStatus) -> Delivery:
        delivery = self.get_delivery(delivery_id)
        if not delivery.can_change_to(new_status):
            raise InvalidStatusTransitionError(
                f"Переход «{delivery.status.value}» → «{new_status.value}» недопустим")
        delivery.status = new_status
        return delivery

    @log_call
    @require_status(DeliveryStatus.EXPECTED)
    def accept_delivery(self, delivery_id: int) -> Delivery:
        return self.change_status(delivery_id, DeliveryStatus.ACCEPTED)

    @log_call
    @require_status(DeliveryStatus.ACCEPTED)
    def place_delivery(self, delivery_id: int) -> Delivery:
        """Размещение поставки на складе — увеличивает остаток товара."""
        delivery = self.get_delivery(delivery_id)
        product = self.get(delivery.product_id, Product)
        if product.warehouse_id is not None:
            self._check_capacity(self.get(product.warehouse_id, Warehouse), delivery.quantity)
        product.quantity += delivery.quantity
        return self.change_status(delivery_id, DeliveryStatus.PLACED)

    @log_call
    @require_status(DeliveryStatus.EXPECTED, DeliveryStatus.ACCEPTED)
    def cancel_delivery(self, delivery_id: int) -> Delivery:
        return self.change_status(delivery_id, DeliveryStatus.CANCELLED)

    def write_off(self, product_id: int, quantity: int) -> Product:
        product = self.get(product_id, Product)
        if quantity <= 0 or quantity > product.quantity:
            raise ValueError(f"Нельзя списать {quantity} шт.: на складе {product.quantity}")
        product.quantity -= quantity
        return product

    def _check_capacity(self, warehouse: Warehouse, extra: int) -> None:
        used = sum(p.quantity for p in self.of_type(Product) if p.warehouse_id == warehouse.id)
        if used + extra > warehouse.capacity:
            raise CapacityExceededError(
                f"Склад «{warehouse.name}»: занято {used}, добавляется {extra}, "
                f"вместимость {warehouse.capacity}")

    # ---------- специализированные операции варианта ----------
    @measure_time
    def stock_value(self) -> float:
        """Расчёт стоимости запасов."""
        return round(sum(map(lambda p: p.stock_value(), self.of_type(Product))), 2)

    def low_stock_products(self) -> list[Product]:
        """Поиск товаров с минимальным остатком (не выше порога min_stock)."""
        return sorted((p for p in self.of_type(Product) if p.is_low()),
                      key=lambda p: p.quantity)

    @measure_time
    def statistics(self) -> dict[str, object]:
        products = self.of_type(Product)
        deliveries = self.of_type(Delivery)
        prices = [p.price for p in products]
        by_status = {s.value: sum(1 for d in deliveries if d.status is s) for s in DeliveryStatus}
        return {
            "товаров": len(products),
            "складов": len(self.of_type(Warehouse)),
            "поставок": len(deliveries),
            "поставки по статусам": by_status,
            "единиц товара на складах": sum(p.quantity for p in products),
            "средняя цена": round(sum(prices) / len(prices), 2) if prices else 0,
            "минимальная / максимальная цена": (min(prices), max(prices)) if prices else None,
            "стоимость запасов": self.stock_value(),
            "товаров с минимальным остатком": len(self.low_stock_products()),
        }
