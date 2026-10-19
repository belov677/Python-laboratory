"""HTTP-эндпоинты. Обработчики только принимают запрос, вызывают сервис и формируют ответ."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from app.api.deps import (
    admin_user,
    auth_service,
    catalog_service,
    current_user,
    delivery_service,
    notification_repo,
    order_service,
)
from app.models.entities import DeliveryStatus, OrderStatus, User, VehicleStatus
from app.schemas.dto import (
    DeliveryAction,
    DeliveryIn,
    DeliveryOut,
    DriverIn,
    DriverOut,
    LoginIn,
    NotificationOut,
    OrderIn,
    OrderOut,
    Page,
    RegisterIn,
    RouteIn,
    RouteOut,
    TokenOut,
    UserOut,
    VehicleIn,
    VehicleOut,
)

ERRORS = {
    400: {"description": "Некорректный запрос"},
    401: {"description": "Нет или неверный токен"},
    403: {"description": "Недостаточно прав"},
    404: {"description": "Объект не найден"},
    409: {"description": "Конфликт или нарушение бизнес-правила"},
    422: {"description": "Ошибка валидации данных"},
}
User_ = Annotated[User, Depends(current_user)]
Admin = Annotated[User, Depends(admin_user)]

auth = APIRouter(prefix="/auth", tags=["Авторизация"])
routes = APIRouter(prefix="/routes", tags=["Маршруты"], responses=ERRORS)
fleet = APIRouter(tags=["Транспорт и водители"], responses=ERRORS)
orders = APIRouter(prefix="/orders", tags=["Заказы"], responses=ERRORS)
deliveries = APIRouter(prefix="/deliveries", tags=["Доставки"], responses=ERRORS)


# ---------- авторизация ----------
@auth.post("/register", response_model=UserOut, status_code=201, responses={409: ERRORS[409], 422: ERRORS[422]})
async def register(data: RegisterIn, service=Depends(auth_service)):
    """Регистрация клиента (роль USER)."""
    return await service.register(data)


@auth.post("/login", response_model=TokenOut, responses={401: ERRORS[401]})
async def login(data: LoginIn, service=Depends(auth_service)):
    """Вход по email и паролю; возвращает JWT для заголовка Authorization: Bearer."""
    token, user = await service.login(data)
    return TokenOut(access_token=token, role=user.role)


@auth.get("/me", response_model=UserOut, responses={401: ERRORS[401]})
async def me(user: User_):
    return user


@auth.get("/me/notifications", response_model=list[NotificationOut])
async def my_notifications(user: User_, repo=Depends(notification_repo)):
    """Уведомления клиента, созданные фоновым worker по событиям."""
    return await repo.for_user(user.id)


# ---------- маршруты (чтение — любой пользователь, через кэш Redis) ----------
def cached(data, source: str) -> JSONResponse:
    return JSONResponse(data, headers={"X-Cache": source})


@routes.get("", response_model=list[RouteOut])
async def list_routes(user: User_, origin: str | None = None, service=Depends(catalog_service)):
    """Список маршрутов (фильтр по городу отправления). Заголовок X-Cache: HIT / MISS / BYPASS."""
    data, source = await service.list_routes(origin)
    return cached(data, source)


@routes.get("/{route_id}", response_model=RouteOut)
async def get_route(route_id: int, user: User_, service=Depends(catalog_service)):
    data, source = await service.get_route(route_id)
    return cached(data, source)


@routes.post("", response_model=RouteOut, status_code=201)
async def create_route(data: RouteIn, admin: Admin, service=Depends(catalog_service)):
    return await service.create_route(data)


@routes.put("/{route_id}", response_model=RouteOut)
async def update_route(route_id: int, data: RouteIn, admin: Admin, service=Depends(catalog_service)):
    return await service.update_route(route_id, data)


@routes.delete("/{route_id}", status_code=204)
async def delete_route(route_id: int, admin: Admin, service=Depends(catalog_service)):
    await service.delete_route(route_id)
    return Response(status_code=204)


# ---------- транспорт и водители (ADMIN) ----------
@fleet.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    admin: Admin,
    status: VehicleStatus | None = None,
    min_capacity: Annotated[int | None, Query(gt=0)] = None,
    sort: Annotated[str, Query(pattern="^(id|plate|capacity|-capacity)$")] = "id",
    service=Depends(catalog_service),
):
    """Фильтры: статус, минимальная грузоподъёмность; сортировка: plate, capacity, -capacity."""
    return await service.list_vehicles(status, min_capacity, sort)


@fleet.post("/vehicles", response_model=VehicleOut, status_code=201)
async def create_vehicle(data: VehicleIn, admin: Admin, service=Depends(catalog_service)):
    return await service.create_vehicle(data)


@fleet.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(vehicle_id: int, data: VehicleIn, admin: Admin, service=Depends(catalog_service)):
    return await service.update_vehicle(vehicle_id, data)


@fleet.delete("/vehicles/{vehicle_id}", status_code=204)
async def delete_vehicle(vehicle_id: int, admin: Admin, service=Depends(catalog_service)):
    await service.delete_vehicle(vehicle_id)
    return Response(status_code=204)


@fleet.get("/drivers", response_model=list[DriverOut])
async def list_drivers(admin: Admin, service=Depends(catalog_service)):
    return await service.list_drivers()


@fleet.post("/drivers", response_model=DriverOut, status_code=201)
async def create_driver(data: DriverIn, admin: Admin, service=Depends(catalog_service)):
    return await service.create_driver(data)


@fleet.put("/drivers/{driver_id}", response_model=DriverOut)
async def update_driver(driver_id: int, data: DriverIn, admin: Admin, service=Depends(catalog_service)):
    return await service.update_driver(driver_id, data)


@fleet.delete("/drivers/{driver_id}", status_code=204)
async def delete_driver(driver_id: int, admin: Admin, service=Depends(catalog_service)):
    await service.delete_driver(driver_id)
    return Response(status_code=204)


# ---------- заказы ----------
@orders.post("", response_model=OrderOut, status_code=201)
async def create_order(data: OrderIn, user: User_, service=Depends(order_service)):
    """Создание заказа. Правила: подача в будущем, есть маршрут, срок достижим."""
    return await service.create(data, user)


@orders.get("", response_model=Page[OrderOut])
async def search_orders(
    user: User_,
    status: OrderStatus | None = None,
    city: str | None = None,
    sort: Annotated[str, Query(pattern="^-?(created_at|pickup_at|weight)$")] = "-created_at",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    service=Depends(order_service),
):
    """Поиск заказов: USER видит только свои. Фильтры status, city; сортировка; пагинация."""
    items, total = await service.search(user, status, city, sort, page, size)
    return Page[OrderOut](items=[OrderOut.model_validate(o) for o in items], total=total, page=page, size=size)


@orders.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, user: User_, service=Depends(order_service)):
    return await service.get(order_id, user)


@orders.put("/{order_id}", response_model=OrderOut)
async def update_order(order_id: int, data: OrderIn, user: User_, service=Depends(order_service)):
    return await service.update(order_id, data, user)


@orders.delete("/{order_id}", response_model=OrderOut)
async def cancel_order(order_id: int, user: User_, service=Depends(order_service)):
    """Отмена заказа (возможна до начала перевозки); назначенный рейс отменяется."""
    return await service.cancel(order_id, user)


@orders.get("/{order_id}/tracking")
async def tracking(order_id: int, user: User_, service=Depends(order_service), deliveries_=Depends(delivery_service)):
    """Отслеживание: заказ, рейс, маршрут, машина и водитель."""
    order = await service.get(order_id, user)
    delivery = await deliveries_.deliveries.last_for_order(order.id)
    return {
        "order": OrderOut.model_validate(order).model_dump(mode="json"),
        "delivery": DeliveryOut.model_validate(delivery).model_dump(mode="json") if delivery else None,
    }


# ---------- доставки (ADMIN) ----------
@deliveries.get("/available", tags=["Доставки"])
async def available(order_id: int, admin: Admin, service=Depends(delivery_service)):
    """Подбор ресурсов для заказа: свободные подходящие машины и водители в окне рейса."""
    result = await service.available_resources(order_id)
    return {
        "order_id": result["order_id"],
        "route": RouteOut.model_validate(result["route"]),
        "window": result["window"],
        "vehicles": [VehicleOut.model_validate(v) for v in result["vehicles"]],
        "drivers": [DriverOut.model_validate(d) for d in result["drivers"]],
    }


@deliveries.post("", response_model=DeliveryOut, status_code=201)
async def create_delivery(data: DeliveryIn, admin: Admin, service=Depends(delivery_service)):
    """Назначение рейса: проверяются заказ, маршрут, машина, водитель и их занятость."""
    return await service.create(data.order_id, data.vehicle_id, data.driver_id, admin)


@deliveries.get("", response_model=list[DeliveryOut])
async def list_deliveries(admin: Admin, status: DeliveryStatus | None = None, service=Depends(delivery_service)):
    return await service.search(status)


@deliveries.get("/{delivery_id}", response_model=DeliveryOut)
async def get_delivery(delivery_id: int, admin: Admin, service=Depends(delivery_service)):
    return await service.get(delivery_id)


@deliveries.patch("/{delivery_id}/status", response_model=DeliveryOut)
async def change_status(delivery_id: int, data: DeliveryAction, admin: Admin, service=Depends(delivery_service)):
    """Переходы: start (PLANNED→IN_TRANSIT), complete (IN_TRANSIT→DELIVERED), cancel (PLANNED→CANCELLED)."""
    return await service.change_status(delivery_id, data.action)
