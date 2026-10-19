"""Тесты Telegram-интерфейса через эмулятор (Update → Dispatcher → перехват Bot API)."""
import pytest

from tests.conftest import ADMIN_ID

pytestmark = pytest.mark.asyncio


async def test_start_shows_main_menu(chat):
    out = await chat.send("/start")
    assert "Здравствуйте" in out[0].text
    keyboard = chat.session.reply_keyboard[chat.user.id]
    assert sum(len(row) for row in keyboard) >= 4


async def test_stock_inline_callback(chat):
    out = await chat.send("📦 Остатки")
    assert [row[0][1] for row in out[0].inline] == ["wh:stock:1", "wh:stock:2", "wh:stock:3"]
    await chat.press("🏬 Восточный")
    assert "Склад «Восточный»" in chat.last().text      # сообщение отредактировано


async def test_fsm_writeoff_with_validation_and_critical_alert(chat):
    await chat.send("/writeoff")
    await chat.send("монитор")
    await chat.press("EL-1002")
    await chat.press("🏬 Центральный")
    out = await chat.send("много")
    assert "целым числом" in out[0].text                 # ошибка ввода, состояние сохраняется
    out = await chat.send("0")
    assert "больше нуля" in out[0].text
    await chat.send("4")                                 # 11 → 7 при минимуме 8
    assert "Количество: 4" in chat.last().text
    out = await chat.press("✅ Подтвердить")
    texts = [m.text for m in chat.timeline if m.sender == "bot"]
    assert any("Списание выполнено" in t for t in texts)
    assert any("Критический остаток" in m.text for m in out)   # уведомление
    assert ADMIN_ID in {m.chat_id for m in out}                 # и администратору


async def test_cancel_resets_fsm(chat):
    await chat.send("/receive")
    out = await chat.send("/cancel")
    assert out[0].text == "Действие отменено."
    out = await chat.send("5")
    assert "Не понимаю" in out[0].text


async def test_create_product_fsm(chat):
    await chat.send("🆕 Новый товар")
    for text in ("Маркер", "OF-5005", "95", "50"):
        await chat.send(text)
    await chat.press("ООО «Офис-Плюс»")
    await chat.press("✅ Подтвердить")
    assert "Товар создан" in chat.last().text or any(
        "Товар создан" in m.text for m in chat.bot_messages())
    out = await chat.send("/search OF-5005")
    assert "Найдено товаров: 1" in out[0].text


async def test_edit_and_delete_product(chat):
    await chat.send("/search ноутбук")
    await chat.press("EL-1001")
    await chat.press("✏️ Изменить")
    await chat.press("Мин. остаток")
    out = await chat.send("2")
    assert "Минимальный остаток: 2" in out[0].text
    await chat.press("🗑 Удалить")
    await chat.press("✅ Да, удалить")
    assert "удалён" in chat.last().text
    out = await chat.send("/search ноутбук")
    assert "ничего не найдено" in out[0].text


async def test_admin_rights(chat):
    out = await chat.send("/statistics")
    assert "только администратору" in out[0].text
    admin = chat.as_user(ADMIN_ID, "Админ", "boss")
    out = await admin.send("/statistics")
    assert "Пользователей: 2" in out[0].text and "товаров 12" in out[0].text
    out = await admin.send("/users")
    assert str(chat.user.id) in out[0].text


async def test_error_handler_for_deleted_object(chat):
    await chat.send("/search монитор")
    msg = chat.last()
    admin = chat.as_user(ADMIN_ID, "Админ", "boss")
    await admin.send("/search монитор")
    await admin.press("EL-1002")
    await admin.press("🗑 Удалить")
    await admin.press("✅ Да, удалить")
    out = await chat.press("EL-1002", message=msg)       # нажатие на кнопку удалённого товара
    assert "Товар не найден" in out[0].text
