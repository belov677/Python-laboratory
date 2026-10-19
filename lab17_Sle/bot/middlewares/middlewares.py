"""Собственные middleware: внедрение сервиса (DI) и журнал действий пользователей."""
from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.repositories.repositories import UserRepository
from bot.services.inventory import InventoryService

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]
actions_log = logging.getLogger("bot.actions")


class DbSessionMiddleware(BaseMiddleware):
    """Открывает сессию БД на время обработки события и передаёт в handler InventoryService."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self.session_factory() as session:
            data["service"] = InventoryService(session)
            return await handler(event, data)


class ActivityMiddleware(BaseMiddleware):
    """Регистрирует пользователя, считает сообщения и использование функций (флаг handler-а
    feature), пишет журнал действий с временем обработки. Подключается как inner middleware."""

    def __init__(self, session_factory: async_sessionmaker, admin_ids: frozenset[int]) -> None:
        self.session_factory = session_factory
        self.admin_ids = admin_ids
        self.features: Counter[str] = Counter()

    @staticmethod
    def describe(event: TelegramObject) -> str:
        if isinstance(event, Message):
            return (event.text or f"<{event.content_type}>")[:40]
        if isinstance(event, CallbackQuery):
            return f"callback:{event.data}"
        return type(event).__name__

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        action = self.describe(event)
        if user:
            async with self.session_factory() as session:
                await UserRepository(session).touch(user.id, user.full_name, user.username)
        data["is_admin"] = bool(user and user.id in self.admin_ids)
        data["activity"] = self
        started = time.perf_counter()
        try:
            return await handler(event, data)
        finally:
            self.features[get_flag(data, "feature") or "other"] += 1
            role = "ADMIN" if data["is_admin"] else "USER"
            actions_log.info("%s %s %s (%.0f мс)", role, user.id if user else "-", action,
                             (time.perf_counter() - started) * 1000)
