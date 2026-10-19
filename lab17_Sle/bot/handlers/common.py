"""/start, /help, /cancel и обработчик ошибок."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent, Message

from bot.keyboards.reply import BTN_CANCEL, BTN_HELP, main_menu
from bot.services.exceptions import InventoryError

router = Router(name="common")
fallback = Router(name="fallback")  # подключается последним
log = logging.getLogger("bot.errors")

HELP = """<b>Складской бот</b> — учёт остатков товаров.

<b>Команды</b>
/start — главное меню
/help — справка
/stock — остатки по складам
/search &lt;текст&gt; — поиск товара по названию, артикулу или поставщику
/critical — товары с критическим остатком
/receive — поступление товара
/writeoff — списание товара
/new — добавить товар
/cancel — отменить текущее действие

Администратор: /admin, /users, /statistics

При списании, после которого остаток становится ниже минимального, бот присылает уведомление
о критическом остатке."""


@router.message(CommandStart(), flags={"feature": "start"})
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(f"Здравствуйте, {message.from_user.first_name}! 👋\n"
                         "Я помогу вести учёт товаров на складах.\nВыберите действие в меню ниже.",
                         reply_markup=main_menu())


@router.message(Command("help"), flags={"feature": "help"})
@router.message(F.text == BTN_HELP, flags={"feature": "help"})
async def cmd_help(message: Message) -> None:
    await message.answer(HELP, reply_markup=main_menu())


@router.message(Command("cancel"), flags={"feature": "cancel"})
@router.message(F.text == BTN_CANCEL, flags={"feature": "cancel"})
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    text = "Действие отменено." if current else "Нечего отменять."
    await message.answer(text, reply_markup=main_menu())


@fallback.message(StateFilter(None), F.text, flags={"feature": "unknown"})
async def unknown(message: Message) -> None:
    await message.answer("Не понимаю команду 🤔 Воспользуйтесь меню или /help.")


@router.error()
async def on_error(event: ErrorEvent) -> bool:
    """Глобальная обработка ошибок: бизнес-ошибки показываются пользователю, прочие — логируются."""
    update = event.update
    target = update.message or (update.callback_query.message if update.callback_query else None)
    if isinstance(event.exception, InventoryError):
        text = f"⚠️ {event.exception}"
    else:
        log.exception("Ошибка при обработке update %s", update.update_id, exc_info=event.exception)
        text = "😔 Произошла внутренняя ошибка. Попробуйте ещё раз или нажмите /cancel."
    if update.callback_query:
        await update.callback_query.answer()
    if target:
        await target.answer(text)
    return True
