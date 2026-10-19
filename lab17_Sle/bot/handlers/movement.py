"""FSM поступления и списания: товар → склад → количество → подтверждение."""
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards.callbacks import ConfirmCb, ProductCb, WarehouseCb
from bot.keyboards.inline import confirm_kb, products_kb, warehouses_kb
from bot.keyboards.reply import BTN_RECEIVE, BTN_WRITEOFF, cancel_menu, main_menu
from bot.services.exceptions import ValidationError
from bot.services.inventory import InventoryService, MovementResult
from bot.services.texts import critical_alert
from bot.services.validators import parse_quantity
from bot.states.states import Movement

router = Router(name="movement")
TITLES = {"receipt": ("Поступление", "➕"), "writeoff": ("Списание", "➖")}


async def start_movement(message: Message, state: FSMContext, kind: str) -> None:
    await state.clear()
    await state.set_state(Movement.product)
    await state.update_data(kind=kind)
    title, icon = TITLES[kind]
    await message.answer(f"{icon} <b>{title}</b>. Шаг 1/4.\nВведите название или артикул товара:",
                         reply_markup=cancel_menu())


@router.message(Command("receive"), flags={"feature": "receipt"})
@router.message(F.text == BTN_RECEIVE, flags={"feature": "receipt"})
async def receive_start(message: Message, state: FSMContext) -> None:
    await start_movement(message, state, "receipt")


@router.message(Command("writeoff"), flags={"feature": "writeoff"})
@router.message(F.text == BTN_WRITEOFF, flags={"feature": "writeoff"})
async def writeoff_start(message: Message, state: FSMContext) -> None:
    await start_movement(message, state, "writeoff")


@router.message(Movement.product, F.text)
async def movement_product(message: Message, service: InventoryService) -> None:
    products = await service.search(message.text)
    if not products:
        await message.answer("Товар не найден. Попробуйте другой запрос или /cancel.")
        return
    await message.answer("Выберите товар:", reply_markup=products_kb(products, action="pick"))


async def ask_warehouse(message: Message, state: FSMContext, service: InventoryService,
                        product_id: int) -> None:
    product = await service.get_product(product_id)
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(Movement.warehouse)
    stocks = ", ".join(f"{s.warehouse.name}: {s.quantity}" for s in product.stocks)
    await message.answer(f"Товар: <b>{product.name}</b> ({stocks}).\nШаг 2/4. Выберите склад:",
                         reply_markup=warehouses_kb(await service.warehouses(), "pick"))


@router.callback_query(Movement.product, ProductCb.filter(F.action == "pick"))
async def movement_pick_product(call: CallbackQuery, callback_data: ProductCb, state: FSMContext,
                                service: InventoryService) -> None:
    await ask_warehouse(call.message, state, service, callback_data.id)
    await call.answer()


@router.callback_query(ProductCb.filter(F.action.in_({"receive", "writeoff"})),
                       flags={"feature": "receipt"})
async def movement_from_card(call: CallbackQuery, callback_data: ProductCb, state: FSMContext,
                             service: InventoryService) -> None:
    """Быстрый запуск сценария из карточки товара — шаг выбора товара пропускается."""
    await state.clear()
    await state.update_data(kind="receipt" if callback_data.action == "receive" else "writeoff")
    await ask_warehouse(call.message, state, service, callback_data.id)
    await call.answer()


@router.callback_query(Movement.warehouse, WarehouseCb.filter(F.action == "pick"))
async def movement_warehouse(call: CallbackQuery, callback_data: WarehouseCb, state: FSMContext,
                             service: InventoryService) -> None:
    warehouse = await service.get_warehouse(callback_data.id)
    await state.update_data(warehouse_id=warehouse.id, warehouse_name=warehouse.name)
    await state.set_state(Movement.quantity)
    await call.message.edit_text(f"Склад: <b>{warehouse.name}</b>.\nШаг 3/4. Введите количество:")
    await call.answer()


@router.message(Movement.warehouse)
async def movement_warehouse_text(message: Message) -> None:
    await message.answer("Выберите склад кнопкой под предыдущим сообщением или нажмите /cancel.")


@router.message(Movement.quantity, F.text)
async def movement_quantity(message: Message, state: FSMContext) -> None:
    try:
        quantity = parse_quantity(message.text)
    except ValidationError as error:
        await message.answer(f"❗ {error}. Повторите ввод:")
        return
    await state.update_data(quantity=quantity)
    await state.set_state(Movement.confirm)
    data = await state.get_data()
    title, icon = TITLES[data["kind"]]
    await message.answer(f"Шаг 4/4. Проверьте данные:\n{icon} {title}\nТовар: {data['product_name']}\n"
                         f"Склад: {data['warehouse_name']}\nКоличество: {quantity}",
                         reply_markup=confirm_kb())


@router.callback_query(Movement.confirm, ConfirmCb.filter())
async def movement_confirm(call: CallbackQuery, callback_data: ConfirmCb, state: FSMContext,
                           service: InventoryService, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    await call.answer()
    if not callback_data.ok:
        await call.message.edit_text("Операция отменена.")
        await call.message.answer("Главное меню:", reply_markup=main_menu())
        return
    operation = service.receive if data["kind"] == "receipt" else service.write_off
    result: MovementResult = await operation(data["product_id"], data["warehouse_id"],
                                             data["quantity"], call.from_user.id)
    title, icon = TITLES[data["kind"]]
    await call.message.edit_text(f"✅ {title} выполнено: {result.product.name} {icon}{result.quantity} "
                                 f"на складе «{result.warehouse.name}».\nОстаток на складе: "
                                 f"{result.left}, всего: {result.product.total}.")
    await call.message.answer("Главное меню:", reply_markup=main_menu())
    if result.critical:
        await notify_critical(bot, call.from_user.id, result)


async def notify_critical(bot: Bot, user_id: int, result: MovementResult) -> None:
    """Уведомление о критическом остатке пользователю и всем администраторам."""
    recipients = {user_id, *get_settings().admin_ids}
    for chat_id in recipients:
        await bot.send_message(chat_id, critical_alert(result.product))
