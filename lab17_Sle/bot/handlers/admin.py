"""Команды администратора: /admin, /users, /statistics."""
from aiogram import F, Router
from aiogram.filters import Command, Filter
from aiogram.types import Message

from bot.config import get_settings
from bot.middlewares.middlewares import ActivityMiddleware
from bot.services.inventory import InventoryService

router = Router(name="admin")


class IsAdmin(Filter):
    """Пропускает только пользователей из ADMIN_IDS (переменная окружения)."""

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id in get_settings().admin_ids


@router.message(Command("admin", "users", "statistics"), ~IsAdmin(),
                flags={"feature": "admin_denied"})
async def denied(message: Message) -> None:
    await message.answer("⛔ Команда доступна только администратору.")


@router.message(Command("admin"), IsAdmin(), flags={"feature": "admin"})
async def admin_panel(message: Message, service: InventoryService) -> None:
    ops = await service.last_operations()
    lines = ["🛠 <b>Панель администратора</b>", "/users — пользователи", "/statistics — статистика",
             "", "<b>Последние операции:</b>"]
    for op in ops:
        sign = "+" if op.kind == "receipt" else "−"
        lines.append(f"{op.created_at:%d.%m %H:%M} {op.product.sku} {sign}{op.quantity} "
                     f"({op.warehouse.name}) user {op.user_id}")
    await message.answer("\n".join(lines))


@router.message(Command("users"), IsAdmin(), flags={"feature": "admin"})
async def users(message: Message, service: InventoryService) -> None:
    lines = ["👥 <b>Пользователи</b>"]
    for u in await service.users_list():
        lines.append(f"{u.telegram_id} {u.full_name} (@{u.username or '—'}) — сообщений: {u.messages}")
    await message.answer("\n".join(lines))


@router.message(Command("statistics"), IsAdmin(), flags={"feature": "admin"})
async def statistics(message: Message, service: InventoryService,
                     activity: ActivityMiddleware) -> None:
    s = await service.statistics()
    popular = [(f, n) for f, n in activity.features.most_common() if f not in ("other", "admin")]
    top = f"{popular[0][0]} ({popular[0][1]})" if popular else "—"
    await message.answer(
        "📊 <b>Статистика</b>\n"
        f"Пользователей: {s['users']}\nСообщений и нажатий: {s['messages']}\n"
        f"Операций: {s['receipts'] + s['writeoffs']} (поступлений {s['receipts']}, "
        f"списаний {s['writeoffs']})\n"
        f"Объектов в БД: товаров {s['products']}, складов {s['warehouses']}, поставщиков "
        f"{s['suppliers']}, остатков {s['stocks']}\n"
        f"Критических остатков: {s['critical']}\nПопулярная функция: {top}")
