"""Точка входа: python -m bot.main (нужна переменная окружения BOT_TOKEN)."""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import Settings, get_settings
from bot.database.db import create_tables, make_engine, make_session_factory
from bot.database.models import Product
from bot.database.seed import seed
from bot.handlers import admin, common, movement, products, stock
from bot.middlewares.middlewares import ActivityMiddleware, DbSessionMiddleware


def setup_logging(settings: Settings) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    journal = logging.FileHandler(settings.log_file, encoding="utf-8")   # журнал действий
    journal.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logging.getLogger("bot.actions").addHandler(journal)


def make_storage(settings: Settings) -> BaseStorage:
    if settings.redis_url:  # дополнительное задание: FSM в Redis
        from aiogram.fsm.storage.redis import RedisStorage
        return RedisStorage.from_url(settings.redis_url)
    return MemoryStorage()


async def build_dispatcher(settings: Settings, reset: bool = False) -> Dispatcher:
    engine = make_engine(settings.database_url)
    await create_tables(engine, drop=reset)
    session_factory = make_session_factory(engine)
    async with session_factory() as session:
        if not await session.get(Product, 1):
            await seed(session)
    dp = Dispatcher(storage=make_storage(settings))
    activity = ActivityMiddleware(session_factory, settings.admin_ids)
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(DbSessionMiddleware(session_factory))
        observer.middleware(activity)
    dp.include_routers(common.router, admin.router, movement.router, products.router,
                       stock.router, common.fallback)
    dp["engine"] = engine
    return dp


COMMANDS = [BotCommand(command=c, description=d) for c, d in [
    ("start", "Главное меню"), ("stock", "Остатки по складам"), ("search", "Поиск товара"),
    ("receive", "Поступление"), ("writeoff", "Списание"), ("critical", "Критические остатки"),
    ("new", "Новый товар"), ("help", "Справка"), ("cancel", "Отмена")]]


async def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    if not settings.bot_token:
        sys.exit("Не задана переменная окружения BOT_TOKEN (см. .env.example)")
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = await build_dispatcher(settings)
    await bot.set_my_commands(COMMANDS)
    logging.info("Бот запущен (long polling)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
