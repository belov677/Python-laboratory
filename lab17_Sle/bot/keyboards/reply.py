from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_STOCK = "📦 Остатки"
BTN_SEARCH = "🔍 Поиск товара"
BTN_RECEIVE = "➕ Поступление"
BTN_WRITEOFF = "➖ Списание"
BTN_CRITICAL = "⚠️ Критические"
BTN_NEW = "🆕 Новый товар"
BTN_HELP = "ℹ️ Помощь"
BTN_CANCEL = "❌ Отмена"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_STOCK), KeyboardButton(text=BTN_SEARCH)],
        [KeyboardButton(text=BTN_RECEIVE), KeyboardButton(text=BTN_WRITEOFF)],
        [KeyboardButton(text=BTN_CRITICAL), KeyboardButton(text=BTN_NEW)],
        [KeyboardButton(text=BTN_HELP)],
    ], resize_keyboard=True, input_field_placeholder="Выберите действие")


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)
