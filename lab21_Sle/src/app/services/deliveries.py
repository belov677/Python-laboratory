"""Планирование и выполнение доставок — операции, затрагивающие несколько сущностей."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.core.events import add_event
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.entities import (
    Delivery,
    DeliveryStatus,
    Driver,
    Order,
    OrderStatus,
    Route,
    User,
    Vehicle,
    VehicleCategory,
    VehicleStatus,
)
from app.repositories.repositories import (
    DeliveryRepository,
    DriverRepository,
    OrderRepository,
    RouteRepository,
    VehicleRepository,
)
from app.services.orders import utcnow

log = logging.getLogger("app.deliveries")
RATE_PER_KM = {VehicleCategory.B: 30, VehicleCategory.C: 45, VehicleCategory.CE: 60}
BASE_COST = 1500
LOADING_BUFFER = timedelta(hours=1)  # погрузка и разгрузка
TRANSITIONS = {
    "start": (DeliveryStatus.PLANNED, DeliveryStatus.IN_TRANSIT, OrderStatus.IN_TRANSIT),
    "complete": (DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELIVERED, OrderStatus.DELIVERED),
    "cancel": (DeliveryStatus.PLANNED, DeliveryStatus.CANCELLED, OrderStatus.NEW),
}


def calculate_cost(route: Route, vehicle: Vehicle) -> float:
    """1500 руб. + ставка за км по категории транспорта (B — 30, C — 45, CE — 60 руб./км)."""
    return float(BASE_COST + route.distance_km * RATE_PER_KM[vehicle.category])


def plan_window(order: Order, route: Route) -> tuple[datetime, datetime]:
    start = order.pickup_at
    return start, start + timedelta(hours=route.duration_h) + LOADING_BUFFER


class DeliveryService:
    def __init__(
        self,
        deliveries: DeliveryRepository,
        orders: OrderRepository,
        routes: RouteRepository,
        vehicles: VehicleRepository,
        drivers: DriverRepository,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.deliveries, self.orders, self.routes = deliveries, orders, routes
        self.vehicles, self.drivers = vehicles, drivers
        self.session = deliveries.session
        self.now = now

    async def _get(self, repo, title: str, entity_id: int):
        entity = await repo.get(entity_id)
        if entity is None:
            raise NotFoundError(title, entity_id)
        return entity

    async def _order_and_route(self, order_id: int) -> tuple[Order, Route]:
        order = await self._get(self.orders, "Заказ", order_id)
        if order.status != OrderStatus.NEW:
            raise BusinessRuleError(f"Заказ уже в статусе {order.status.value}", code="ORDER_NOT_NEW")
        route = await self.routes.find(order.origin, order.destination)
        if route is None:
            raise BusinessRuleError("Для направления заказа нет маршрута", code="NO_ROUTE")
        return order, route

    @staticmethod
    def check_vehicle(vehicle: Vehicle, order: Order) -> None:
        if vehicle.status != VehicleStatus.ACTIVE:
            raise BusinessRuleError(f"Транспорт {vehicle.plate} на обслуживании", code="VEHICLE_INACTIVE")
        if vehicle.capacity_kg < order.weight_kg:
            raise BusinessRuleError(
                f"Грузоподъёмность {vehicle.plate} — {vehicle.capacity_kg} кг, а груз {order.weight_kg} кг",
                code="VEHICLE_CAPACITY",
            )

    @staticmethod
    def check_driver(driver: Driver, vehicle: Vehicle) -> None:
        if not driver.active:
            raise BusinessRuleError(f"Водитель {driver.full_name} неактивен", code="DRIVER_INACTIVE")
        if vehicle.category.value not in driver.license_categories:
            raise BusinessRuleError(
                f"У водителя нет категории {vehicle.category.value} для {vehicle.plate}", code="DRIVER_LICENSE"
            )

    async def create(self, order_id: int, vehicle_id: int, driver_id: int, dispatcher: User) -> Delivery:
        order, route = await self._order_and_route(order_id)
        vehicle = await self._get(self.vehicles, "Транспорт", vehicle_id)
        driver = await self._get(self.drivers, "Водитель", driver_id)
        self.check_vehicle(vehicle, order)
        self.check_driver(driver, vehicle)
        start, end = plan_window(order, route)
        if end > order.deadline_at:
            raise BusinessRuleError("Рейс не успевает к сроку доставки заказа", code="DEADLINE_UNREACHABLE")
        if await self.deliveries.vehicle_busy(vehicle.id, start, end):
            raise BusinessRuleError(f"Транспорт {vehicle.plate} занят в это время", code="VEHICLE_BUSY")
        if await self.deliveries.driver_busy(driver.id, start, end):
            raise BusinessRuleError(f"Водитель {driver.full_name} занят в это время", code="DRIVER_BUSY")
        delivery = Delivery(
            order=order,
            route=route,
            vehicle=vehicle,
            driver=driver,
            planned_start=start,
            planned_end=end,
            cost=calculate_cost(route, vehicle),
        )
        order.status = OrderStatus.SCHEDULED
        try:
            await self.deliveries.add(delivery)
        except IntegrityError as error:  # параллельный запрос успел занять ресурс — сработал EXCLUDE в БД
            await self.session.rollback()
            raise ConflictError(
                "Транспорт или водитель только что назначен на другой рейс", code="RESOURCE_CONFLICT"
            ) from error
        add_event(
            self.session,
            "DeliveryScheduled",
            {
                "delivery_id": delivery.id,
                "order_id": order.id,
                "customer_id": order.customer_id,
                "vehicle": f"{vehicle.model} {vehicle.plate}",
                "driver": driver.full_name,
                "start": start.isoformat(),
                "cost": delivery.cost,
            },
        )
        await self.session.commit()
        log.info(
            "рейс %s: заказ %s, %s, водитель %s, %s руб. (диспетчер %s)",
            delivery.id,
            order.id,
            vehicle.plate,
            driver.full_name,
            delivery.cost,
            dispatcher.email,
        )
        return delivery

    async def available_resources(self, order_id: int) -> dict:
        """Подбор: свободные в окне заказа машины подходящей грузоподъёмности и водители с нужной категорией."""
        order, route = await self._order_and_route(order_id)
        start, end = plan_window(order, route)
        busy_vehicles, busy_drivers = await self.deliveries.busy_ids(start, end)
        vehicles = [
            v
            for v in await self.vehicles.search(VehicleStatus.ACTIVE, order.weight_kg, "capacity")
            if v.id not in busy_vehicles
        ]
        drivers = [d for d in await self.drivers.list() if d.active and d.id not in busy_drivers]
        categories = {v.category.value for v in vehicles}
        return {
            "order_id": order.id,
            "route": route,
            "window": {"start": start, "end": end},
            "vehicles": vehicles,
            "drivers": [d for d in drivers if categories & set(d.license_categories)],
        }

    async def change_status(self, delivery_id: int, action: str) -> Delivery:
        delivery = await self._get(self.deliveries, "Доставка", delivery_id)
        expected, new_status, order_status = TRANSITIONS[action]
        if delivery.status != expected:
            raise BusinessRuleError(
                f"Действие {action} недопустимо для рейса в статусе {delivery.status.value}", code="INVALID_TRANSITION"
            )
        delivery.status = new_status
        delivery.order.status = order_status
        if new_status == DeliveryStatus.DELIVERED:
            delivery.finished_at = self.now()
        add_event(
            self.session,
            "DeliveryStatusChanged",
            {
                "delivery_id": delivery.id,
                "order_id": delivery.order_id,
                "customer_id": delivery.order.customer_id,
                "status": new_status.value,
            },
        )
        await self.session.commit()
        log.info("рейс %s: %s → %s", delivery.id, expected.value, new_status.value)
        return delivery

    async def get(self, delivery_id: int) -> Delivery:
        return await self._get(self.deliveries, "Доставка", delivery_id)

    async def search(self, status: DeliveryStatus | None):
        return await self.deliveries.search(status)
