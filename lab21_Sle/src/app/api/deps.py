"""Зависимости FastAPI: сессия, сервисы, текущий пользователь и роли."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.models.entities import User
from app.repositories.repositories import (
    DeliveryRepository,
    DriverRepository,
    NotificationRepository,
    OrderRepository,
    RouteRepository,
    UserRepository,
    VehicleRepository,
)
from app.services.auth import AuthService
from app.services.catalog import CatalogService
from app.services.deliveries import DeliveryService
from app.services.orders import OrderService

bearer = HTTPBearer(auto_error=False)


def container(request: Request) -> Container:
    return request.app.state.container


async def session(c: Container = Depends(container)) -> AsyncIterator[AsyncSession]:
    async with c.sessions() as s:
        yield s


async def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    s: AsyncSession = Depends(session),
    c: Container = Depends(container),
) -> User:
    if credentials is None:
        raise UnauthorizedError(
            "Требуется авторизация: заголовок Authorization: Bearer <токен>", code="NOT_AUTHENTICATED"
        )
    payload = decode_token(credentials.credentials, c.settings.jwt_secret)
    user = await UserRepository(s).get(int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("Пользователь не найден", code="INVALID_TOKEN")
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    AuthService.require_admin(user)
    return user


def auth_service(s: AsyncSession = Depends(session), c: Container = Depends(container)) -> AuthService:
    return AuthService(UserRepository(s), c.settings.jwt_secret, c.settings.jwt_ttl_minutes)


def catalog_service(s: AsyncSession = Depends(session), c: Container = Depends(container)) -> CatalogService:
    return CatalogService(RouteRepository(s), VehicleRepository(s), DriverRepository(s), DeliveryRepository(s), c.cache)


def order_service(s: AsyncSession = Depends(session)) -> OrderService:
    return OrderService(OrderRepository(s), RouteRepository(s), DeliveryRepository(s))


def delivery_service(s: AsyncSession = Depends(session)) -> DeliveryService:
    return DeliveryService(
        DeliveryRepository(s), OrderRepository(s), RouteRepository(s), VehicleRepository(s), DriverRepository(s)
    )


def notification_repo(s: AsyncSession = Depends(session)) -> NotificationRepository:
    return NotificationRepository(s)
