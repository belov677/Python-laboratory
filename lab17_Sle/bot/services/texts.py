"""Форматирование ответов бота (HTML)."""
from html import escape

from bot.database.models import Product, Stock, Warehouse


def product_card(p: Product) -> str:
    lines = [f"📦 <b>{escape(p.name)}</b>", f"Артикул: <code>{p.sku}</code>",
             f"Цена: {p.price:,.2f} руб.".replace(",", " "),
             f"Поставщик: {escape(p.supplier.name)}",
             f"Минимальный остаток: {p.min_stock}", "", "<b>Остатки:</b>"]
    for s in sorted(p.stocks, key=lambda s: s.warehouse_id):
        lines.append(f"  • {escape(s.warehouse.name)}: {s.quantity}")
    mark = " ⚠️ <b>критический</b>" if p.is_critical else ""
    lines.append(f"Всего: <b>{p.total}</b>{mark}")
    return "\n".join(lines)


def stock_table(warehouse: Warehouse, stocks: list[Stock]) -> str:
    lines = [f"🏬 <b>Склад «{escape(warehouse.name)}»</b> ({escape(warehouse.city)})", ""]
    for s in stocks:
        warn = " ⚠️" if s.quantity < s.product.min_stock else ""
        lines.append(f"{s.product.sku}  {escape(s.product.name)} — <b>{s.quantity}</b>{warn}")
    lines.append("\n⚠️ — ниже минимального остатка товара")
    return "\n".join(lines)


def critical_alert(p: Product) -> str:
    return (f"🚨 <b>Критический остаток!</b>\n{escape(p.name)} ({p.sku}): всего {p.total} "
            f"при минимуме {p.min_stock}.\nПоставщик: {escape(p.supplier.name)}, "
            f"{p.supplier.phone}")
