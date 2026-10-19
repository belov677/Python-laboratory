"""Просмотр остатков, поиск, карточка товара, критические остатки."""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.callbacks import ProductCb, WarehouseCb
from bot.keyboards.inline import product_actions_kb, products_kb, warehouses_kb
from bot.keyboards.reply import BTN_CRITICAL, BTN_SEARCH, BTN_STOCK, cancel_menu, main_menu
from bot.services.inventory import InventoryService
from bot.services.texts import product_card, stock_table
from bot.states.states import Search

router = Router(name="stock")


@router.message(Command("stock"), flags={"feature": "stock"})
@router.message(F.text == BTN_STOCK, flags={"feature": "stock"})
async def choose_warehouse(message: Message, service: InventoryService) -> None:
    await message.answer("Выберите склад:", reply_markup=warehouses_kb(await service.warehouses(), "stock"))


@router.callback_query(WarehouseCb.filter(F.action == "stock"), flags={"feature": "stock"})
async def show_stock(call: CallbackQuery, callback_data: WarehouseCb, service: InventoryService) -> None:
    warehouse, stocks = await service.stock_in_warehouse(callback_data.id)
    await call.message.edit_text(stock_table(warehouse, stocks))
    await call.answer()


async def send_results(message: Message, service: InventoryService, query: str) -> None:
    products = await service.search(query)
    if not products:
        await message.answer(f"По запросу «{query}» ничего не найдено.", reply_markup=main_menu())
        return
    await message.answer(f"Найдено товаров: {len(products)}. Выберите:", reply_markup=main_menu())
    await message.answer("Результаты поиска:", reply_markup=products_kb(products))


@router.message(Command("search"), flags={"feature": "search"})
async def cmd_search(message: Message, command: CommandObject, service: InventoryService,
                     state: FSMContext) -> None:
    if command.args:
        await send_results(message, service, command.args)
    else:
        await state.set_state(Search.query)
        await message.answer("Введите название, артикул или поставщика:", reply_markup=cancel_menu())


@router.message(F.text == BTN_SEARCH, flags={"feature": "search"})
async def ask_search(message: Message, state: FSMContext) -> None:
    await state.set_state(Search.query)
    await message.answer("Введите название, артикул или поставщика:", reply_markup=cancel_menu())


@router.message(Search.query, F.text, flags={"feature": "search"})
async def do_search(message: Message, state: FSMContext, service: InventoryService) -> None:
    await send_results(message, service, message.text)   # ValidationError → обработчик ошибок
    await state.clear()


@router.callback_query(ProductCb.filter(F.action == "view"), flags={"feature": "product_card"})
async def show_product(call: CallbackQuery, callback_data: ProductCb, service: InventoryService) -> None:
    product = await service.get_product(callback_data.id)
    await call.message.answer(product_card(product), reply_markup=product_actions_kb(product.id))
    await call.answer()


@router.message(Command("critical"), flags={"feature": "critical"})
@router.message(F.text == BTN_CRITICAL, flags={"feature": "critical"})
async def show_critical(message: Message, service: InventoryService) -> None:
    products = await service.critical()
    if not products:
        await message.answer("Критических остатков нет 👍")
        return
    lines = ["⚠️ <b>Товары с критическим остатком</b>", ""]
    lines += [f"{p.sku} {p.name}: {p.total} / мин. {p.min_stock}" for p in products]
    await message.answer("\n".join(lines), reply_markup=products_kb(products))
