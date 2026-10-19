"""Регистрация, вход и проверка прав."""

from __future__ import annotations

import logging

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_token, hash_password, verify_password
from app.models.entities import Role, User
from app.repositories.repositories import UserRepository
from app.schemas.dto import LoginIn, RegisterIn

log = logging.getLogger("app.auth")


class AuthService:
    def __init__(self, users: UserRepository, jwt_secret: str, ttl_minutes: int = 60) -> None:
        self.users = users
        self.jwt_secret = jwt_secret
        self.ttl = ttl_minutes

    async def register(self, data: RegisterIn, role: Role = Role.USER) -> User:
        if await self.users.by_email(data.email):
            raise ConflictError(f"Пользователь {data.email} уже зарегистрирован", code="EMAIL_TAKEN")
        user = await self.users.add(
            User(
                email=data.email.lower(),
                full_name=data.full_name.strip(),
                password_hash=hash_password(data.password),
                role=role,
            )
        )
        await self.users.session.commit()
        log.info("зарегистрирован пользователь %s (%s)", user.email, role.value)
        return user

    async def login(self, data: LoginIn) -> tuple[str, User]:
        user = await self.users.by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            # одинаковый ответ для неизвестного email и неверного пароля — не раскрываем, кто зарегистрирован
            raise UnauthorizedError("Неверный email или пароль", code="INVALID_CREDENTIALS")
        return create_token(user.id, user.role.value, self.jwt_secret, self.ttl), user

    @staticmethod
    def require_admin(user: User) -> None:
        if user.role != Role.ADMIN:
            raise ForbiddenError("Операция доступна только диспетчеру (ADMIN)", code="ADMIN_ONLY")
