"""Демонстрация работы бота в эмуляторе Telegram и скриншоты переписки (Playwright).

Запуск: python demo_chat.py  → screenshots/chat_*.png, журнал bot_actions.log
"""
import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'demo.db'}")
os.environ.setdefault("ADMIN_IDS", "9001")
os.environ.setdefault("LOG_FILE", str(ROOT / "bot_actions.log"))

from bot.config import get_settings  # noqa: E402
from bot.main import build_dispatcher, setup_logging  # noqa: E402
from emulator import ChatEmulator, render_html  # noqa: E402

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
OUT = ROOT / "screenshots"


async def scenario(chat: ChatEmulator, steps: list[tuple[str, str]]) -> list:
    start = len(chat.timeline)
    for kind, value in steps:
        if kind == "send":
            await chat.send(value)
        else:
            await chat.press(value)
    return chat.timeline[start:]


async def main() -> None:
    settings = get_settings()
    Path(settings.log_file).unlink(missing_ok=True)
    setup_logging(settings)
    dp = await build_dispatcher(settings, reset=True)
    user = ChatEmulator(dp, user_id=5001, first_name="Семён", username="sle_user")
    admin = user.as_user(9001, "Анна", "warehouse_admin")
    S, P = "send", "press"
    scenarios = {
        "start": (user, "/start, главное меню, /help", [(S, "/start"), (S, "ℹ️ Помощь")]),
        "stock": (user, "Просмотр остатков (Inline + Callback)", [(S, "📦 Остатки"), (P, "🏬 Центральный")]),
        "search": (user, "Поиск товара и карточка", [(S, "🔍 Поиск товара"), (S, "м"), (S, "монитор"),
                                                     (P, "EL-1002")]),
        "receipt": (user, "FSM: поступление", [(S, "➕ Поступление"), (S, "гипсокартон"), (P, "BD-3002"),
                                              (P, "🏬 Северный"), (S, "сто"), (S, "-5"), (S, "120"),
                                              (P, "✅ Подтвердить")]),
        "writeoff": (user, "FSM: списание и уведомление", [(S, "➖ Списание"), (S, "монитор"), (P, "EL-1002"),
                                                          (P, "🏬 Северный"), (S, "10"), (P, "✅ Подтвердить"),
                                                          (S, "/writeoff"), (S, "EL-1002"), (P, "EL-1002"),
                                                          (P, "🏬 Центральный"), (S, "4"), (P, "✅ Подтвердить")]),
        "create": (user, "FSM: создание товара", [(S, "🆕 Новый товар"), (S, "Ма"), (S, "Маркер перманентный"),
                                                 (S, "маркер"), (S, "OF-5005"), (S, "0"), (S, "95"), (S, "50"),
                                                 (P, "ООО «Офис-Плюс»"), (P, "✅ Подтвердить")]),
        "edit": (user, "Изменение и удаление товара", [(S, "/search маркер"), (P, "OF-5005"), (P, "✏️ Изменить"),
                                                      (P, "Цена"), (S, "сто десять"), (S, "110"),
                                                      (P, "🗑 Удалить"), (P, "✅ Да, удалить")]),
        "cancel": (user, "/cancel и неизвестный ввод", [(S, "/receive"), (S, "/cancel"), (S, "привет")]),
        "critical": (user, "Критические остатки", [(S, "⚠️ Критические")]),
        "denied": (user, "Команды администратора недоступны", [(S, "/statistics"), (S, "/admin")]),
    }
    shots = {}
    for name, (chat, title, steps) in scenarios.items():
        messages = await scenario(chat, steps)
        shots[name] = render_html(messages, title, user.session.reply_keyboard.get(chat.user.id),
                                  chat.user.id)
    # ошибка: нажатие кнопки в карточке уже удалённого товара (из сценария edit)
    card = next(m for m in reversed(user.bot_messages()) if "OF-5005" in m.text and m.inline)
    start = len(user.timeline)
    await user.press("➕ Поступление", message=card)
    shots["error"] = render_html(user.timeline[start:], "Обработка ошибки", None, user.user.id)
    messages = await scenario(admin, [(S, "/start"), (S, "/admin"), (S, "/users"), (S, "/statistics")])
    shots["admin"] = render_html(messages, "Администратор", None, admin.user.id)
    # уведомление, пришедшее администратору при списании
    alerts = [m for m in user.timeline if m.chat_id == admin.user.id and "Критический" in m.text]
    shots["alert_admin"] = render_html(alerts, "Уведомление администратору", None, admin.user.id)

    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME)
        page = await browser.new_page(viewport={"width": 560, "height": 400}, device_scale_factor=1.5)
        for name, html in shots.items():
            await page.set_content(html)
            await page.screenshot(path=str(OUT / f"chat_{name}.png"), full_page=True)
            print("saved", name)
        await browser.close()
    await dp["engine"].dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
