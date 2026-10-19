"""Справочники: маршруты (с кэшем Redis), транспорт, водители."""

from __future__ import annotations

import logging

from app.core.cache import RedisCache
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.entities import Delivery, DeliveryStatus, Driver, Route, Vehicle, VehicleStatus
from app.repositories.repositories import DeliveryRepository, DriverRepository, RouteRepository, VehicleRepository
from app.schemas.dto import DriverIn, RouteIn, RouteOut, VehicleIn

log = logging.getLogger("app.catalog")
ACTIVE = (DeliveryStatus.PLANNED, DeliveryStatus.IN_TRANSIT)


class CatalogService:
    def __init__(
        self,
        routes: RouteRepository,
        vehicles: VehicleRepository,
        drivers: DriverRepository,
        deliveries: DeliveryRepository,
        cache: RedisCache,
    ) -> None:
        self.routes, self.vehicles, self.drivers, self.deliveries = routes, vehicles, drivers, deliveries
        self.cache = cache
        self.session = routes.session

    # ---------- маршруты: чтение через кэш ----------
    async def list_routes(self, origin: str | None = None) -> tuple[list[dict], str]:
        async def load():
            return [RouteOut.model_validate(r).model_dump() for r in await self.routes.search(origin)]

        return await self.cache.get_or_load(f"routes:list:{(origin or '*').lower()}", load)

    async def get_route(self, route_id: int) -> tuple[dict, str]:
        async def load():
            route = await self.routes.get(route_id)
            if route is None:
                raise NotFoundError("Маршрут", route_id)
            return RouteOut.model_validate(route).model_dump()

        return await self.cache.get_or_load(f"routes:item:{route_id}", load)

    async def create_route(self, data: RouteIn) -> Route:
        await self._route_unique(data)
        route = await self.routes.add(Route(**data.model_dump()))
        await self.session.commit()
        await self.cache.invalidate("routes:*")
        return route

    async def update_route(self, route_id: int, data: RouteIn) -> Route:
        route = await self._entity(self.routes, "Маршрут", route_id)
        await self._route_unique(data, route_id)
        for key, value in data.model_dump().items():
            setattr(route, key, value)
        await self.session.commit()
        await self.cache.invalidate("routes:*")  # кэш не должен отдавать устаревшие данные
        return route

    async def delete_route(self, route_id: int) -> None:
        route = await self._entity(self.routes, "Маршрут", route_id)
        if await self.deliveries.exists(Delivery.route_id == route_id):
            raise ConflictError("Маршрут используется в доставках", code="ROUTE_IN_USE")
        await self.routes.delete(route)
        await self.session.commit()
        await self.cache.invalidate("routes:*")

    async def _route_unique(self, data: RouteIn, exclude_id: int | None = None) -> None:
        same = await self.routes.find(data.origin, data.destination)
        if same and same.id != exclude_id:
            raise ConflictError(
                f"Маршрут {data.origin} → {data.destination} уже есть ({same.code})", code="ROUTE_EXISTS"
            )
        others = await self.routes.list()
        if any(r.code == data.code and r.id != exclude_id for r in others):
            raise ConflictError(f"Код маршрута {data.code} занят", code="ROUTE_CODE_TAKEN")

    # ---------- транспорт ----------
    async def list_vehicles(self, status: VehicleStatus | None, min_capacity: int | None, sort: str):
        return await self.vehicles.search(status, min_capacity, sort)

    async def create_vehicle(self, data: VehicleIn) -> Vehicle:
        if await self.vehicles.exists(Vehicle.plate == data.plate):
            raise ConflictError(f"Номер {data.plate} уже зарегистрирован", code="PLATE_TAKEN")
        vehicle = await self.vehicles.add(Vehicle(**data.model_dump()))
        await self.session.commit()
        return vehicle

    async def update_vehicle(self, vehicle_id: int, data: VehicleIn) -> Vehicle:
        vehicle = await self._entity(self.vehicles, "Транспорт", vehicle_id)
        if await self.vehicles.exists(Vehicle.plate == data.plate, Vehicle.id != vehicle_id):
            raise ConflictError(f"Номер {data.plate} уже зарегистрирован", code="PLATE_TAKEN")
        if data.status == VehicleStatus.MAINTENANCE and await self.deliveries.exists(
            Delivery.vehicle_id == vehicle_id, Delivery.status.in_(ACTIVE)
        ):
            raise BusinessRuleError(
                "Нельзя отправить на ремонт машину с запланированными рейсами", code="VEHICLE_HAS_DELIVERIES"
            )
        for key, value in data.model_dump().items():
            setattr(vehicle, key, value)
        await self.session.commit()
        return vehicle

    async def delete_vehicle(self, vehicle_id: int) -> None:
        vehicle = await self._entity(self.vehicles, "Транспорт", vehicle_id)
        if await self.deliveries.exists(Delivery.vehicle_id == vehicle_id):
            raise ConflictError("Транспорт участвует в доставках — переведите его в MAINTENANCE", code="VEHICLE_IN_USE")
        await self.vehicles.delete(vehicle)
        await self.session.commit()

    # ---------- водители ----------
    async def list_drivers(self):
        return await self.drivers.list()

    async def create_driver(self, data: DriverIn) -> Driver:
        if await self.drivers.exists(Driver.license_number == data.license_number):
            raise ConflictError("Водитель с таким удостоверением уже есть", code="LICENSE_TAKEN")
        driver = await self.drivers.add(
            Driver(**{**data.model_dump(), "license_categories": [c.value for c in data.license_categories]})
        )
        await self.session.commit()
        return driver

    async def update_driver(self, driver_id: int, data: DriverIn) -> Driver:
        driver = await self._entity(self.drivers, "Водитель", driver_id)
        for key, value in data.model_dump().items():
            setattr(driver, key, value)
        driver.license_categories = [c.value for c in data.license_categories]
        await self.session.commit()
        return driver

    async def delete_driver(self, driver_id: int) -> None:
        driver = await self._entity(self.drivers, "Водитель", driver_id)
        if await self.deliveries.exists(Delivery.driver_id == driver_id):
            raise ConflictError("Водитель участвует в доставках — сделайте его неактивным", code="DRIVER_IN_USE")
        await self.drivers.delete(driver)
        await self.session.commit()

    @staticmethod
    async def _entity(repo, title: str, entity_id: int):
        entity = await repo.get(entity_id)
        if entity is None:
            raise NotFoundError(title, entity_id)
        return entity
