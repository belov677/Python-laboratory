"""CRUD товаров: создание (FSM), изменение, удаление с подтверждением."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.callbacks import ConfirmCb, EditCb, ProductCb, SupplierCb
from bot.keyboards.inline import (confirm_kb, delete_confirm_kb, edit_fields_kb,
                                  product_actions_kb, suppliers_kb)
from bot.keyboards.reply import BTN_NEW, cancel_menu, main_menu
from bot.services.exceptions import ValidationError
from bot.services.inventory import InventoryService
from bot.services.texts import product_card
from bot.services.validators import parse_name, parse_price, parse_quantity, parse_sku
from bot.states.states import EditProduct, NewProduct

router = Router(name="products")


@router.message(Command("new"), flags={"feature": "create_product"})
@router.message(F.text == BTN_NEW, flags={"feature": "create_product"})
async def new_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(NewProduct.name)
    await message.answer("🆕 Новый товар. Шаг 1/6. Введите название:", reply_markup=cancel_menu())


async def step(message: Message, state: FSMContext, parser, key: str, next_state, prompt: str):
    """Общий шаг FSM: проверить ввод, сохранить значение, перейти к следующему состоянию."""
    try:
        value = parser(message.text or "")
    except ValidationError as error:
        await message.answer(f"❗ {error}. Повторите ввод:")
        return
    await state.update_data({key: value})
    await state.set_state(next_state)
    await message.answer(prompt)


@router.message(NewProduct.name)
async def new_name(message: Message, state: FSMContext) -> None:
    await step(message, state, parse_name, "name", NewProduct.sku,
               "Шаг 2/6. Введите артикул (например, OF-5004):")


@router.message(NewProduct.sku)
async def new_sku(message: Message, state: FSMContext) -> None:
    await step(message, state, parse_sku, "sku", NewProduct.price, "Шаг 3/6. Введите цену, руб.:")


@router.message(NewProduct.price)
async def new_price(message: Message, state: FSMContext) -> None:
    await step(message, state, lambda t: str(parse_price(t)), "price", NewProduct.min_stock,
               "Шаг 4/6. Введите минимальный (критический) остаток:")


@router.message(NewProduct.min_stock)
async def new_min_stock(message: Message, state: FSMContext, service: InventoryService) -> None:
    try:
        value = parse_quantity(message.text or "")
    except ValidationError as error:
        await message.answer(f"❗ {error}. Повторите ввод:")
        return
    await state.update_data(min_stock=value)
    await state.set_state(NewProduct.supplier)
    await message.answer("Шаг 5/6. Выберите поставщика:",
                         reply_markup=suppliers_kb(await service.suppliers()))


@router.callback_query(NewProduct.supplier, SupplierCb.filter())
async def new_supplier(call: CallbackQuery, callback_data: SupplierCb, state: FSMContext,
                       service: InventoryService) -> None:
    supplier = next(s for s in await service.suppliers() if s.id == callback_data.id)
    await state.update_data(supplier_id=supplier.id)
    await state.set_state(NewProduct.confirm)
    d = await state.get_data()
    await call.message.edit_text(
        f"Шаг 6/6. Проверьте данные:\nНазвание: {d['name']}\nАртикул: {d['sku']}\n"
        f"Цена: {d['price']} руб.\nМин. остаток: {d['min_stock']}\nПоставщик: {supplier.name}",
        reply_markup=confirm_kb())
    await call.answer()


@router.callback_query(NewProduct.confirm, ConfirmCb.filter())
async def new_confirm(call: CallbackQuery, callback_data: ConfirmCb, state: FSMContext,
                      service: InventoryService) -> None:
    data = await state.get_data()
    await state.clear()
    await call.answer()
    if not callback_data.ok:
        await call.message.edit_text("Создание товара отменено.")
    else:
        product = await service.create_product(data["name"], data["sku"], data["price"],
                                               data["min_stock"], data["supplier_id"])
        await call.message.edit_text("✅ Товар создан:\n\n" + product_card(product),
                                     reply_markup=product_actions_kb(product.id))
    await call.message.answer("Главное меню:", reply_markup=main_menu())


# ---------- изменение ----------
@router.callback_query(ProductCb.filter(F.action == "edit"), flags={"feature": "edit_product"})
async def edit_choose(call: CallbackQuery, callback_data: ProductCb) -> None:
    await call.message.answer("Что изменить?", reply_markup=edit_fields_kb(callback_data.id))
    await call.answer()


@router.callback_query(EditCb.filter(), flags={"feature": "edit_product"})
async def edit_field(call: CallbackQuery, callback_data: EditCb, state: FSMContext) -> None:
    await state.set_state(EditProduct.value)
    await state.update_data(product_id=callback_data.id, field=callback_data.field)
    await call.message.edit_text("Введите новое значение:")
    await call.answer()


@router.message(EditProduct.value, F.text)
async def edit_value(message: Message, state: FSMContext, service: InventoryService) -> None:
    data = await state.get_data()
    try:
        product = await service.update_product(data["product_id"], data["field"], message.text)
    except ValidationError as error:
        await message.answer(f"❗ {error}. Повторите ввод или /cancel:")
        return
    await state.clear()
    await message.answer("✅ Сохранено.\n\n" + product_card(product),
                         reply_markup=product_actions_kb(product.id))


# ---------- удаление ----------
@router.callback_query(ProductCb.filter(F.action == "delete"), flags={"feature": "delete_product"})
async def delete_ask(call: CallbackQuery, callback_data: ProductCb, service: InventoryService) -> None:
    product = await service.get_product(callback_data.id)
    await call.message.answer(f"Удалить товар «{product.name}» и все его остатки?",
                              reply_markup=delete_confirm_kb(product.id))
    await call.answer()


@router.callback_query(ProductCb.filter(F.action == "del_ok"), flags={"feature": "delete_product"})
async def delete_ok(call: CallbackQuery, callback_data: ProductCb, service: InventoryService) -> None:
    name = await service.delete_product(callback_data.id)
    await call.message.edit_text(f"🗑 Товар «{name}» удалён.")
    await call.answer("Удалено")
