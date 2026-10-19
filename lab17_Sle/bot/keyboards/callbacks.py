"""Фабрики callback data (компактные: префикс + действие + id, < 64 байт)."""
from aiogram.filters.callback_data import CallbackData


class WarehouseCb(CallbackData, prefix="wh"):
    action: str          # stock — показать остатки, pick — выбор в FSM
    id: int


class ProductCb(CallbackData, prefix="pr"):
    action: str          # view, pick, edit, delete, del_ok, receive, writeoff
    id: int


class EditCb(CallbackData, prefix="ed"):
    field: str
    id: int


class SupplierCb(CallbackData, prefix="sp"):
    id: int


class ConfirmCb(CallbackData, prefix="cf"):
    ok: bool
