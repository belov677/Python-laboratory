from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Product, Supplier, Warehouse

from .callbacks import ConfirmCb, EditCb, ProductCb, SupplierCb, WarehouseCb


def warehouses_kb(warehouses: list[Warehouse], action: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for w in warehouses:
        kb.button(text=f"🏬 {w.name}", callback_data=WarehouseCb(action=action, id=w.id))
    return kb.adjust(1).as_markup()


def products_kb(products: list[Product], action: str = "view") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products[:10]:
        mark = "⚠️ " if p.is_critical else ""
        kb.button(text=f"{mark}{p.sku} {p.name}"[:60], callback_data=ProductCb(action=action, id=p.id))
    return kb.adjust(1).as_markup()


def product_actions_kb(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Поступление", callback_data=ProductCb(action="receive", id=product_id))
    kb.button(text="➖ Списание", callback_data=ProductCb(action="writeoff", id=product_id))
    kb.button(text="✏️ Изменить", callback_data=ProductCb(action="edit", id=product_id))
    kb.button(text="🗑 Удалить", callback_data=ProductCb(action="delete", id=product_id))
    return kb.adjust(2).as_markup()


def edit_fields_kb(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for field, title in (("name", "Название"), ("price", "Цена"), ("min_stock", "Мин. остаток")):
        kb.button(text=title, callback_data=EditCb(field=field, id=product_id))
    return kb.adjust(3).as_markup()


def delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=ProductCb(action="del_ok", id=product_id))
    kb.button(text="↩️ Нет", callback_data=ProductCb(action="view", id=product_id))
    return kb.adjust(2).as_markup()


def suppliers_kb(suppliers: list[Supplier]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in suppliers:
        kb.button(text=s.name, callback_data=SupplierCb(id=s.id))
    return kb.adjust(1).as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=ConfirmCb(ok=True))
    kb.button(text="✖️ Отменить", callback_data=ConfirmCb(ok=False))
    return kb.adjust(2).as_markup()
