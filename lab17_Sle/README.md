# Складской Telegram-бот — лабораторная №17 (aiogram 3, вариант 17 «Склад»)

Сущности: товар, склад, поставщик, остаток (+ пользователь и журнал операций).
Функции: просмотр остатков, поиск товара, поступление, списание, уведомление о критическом остатке,
CRUD товаров, команды администратора.

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env     # указать BOT_TOKEN от @BotFather и свой Telegram id в ADMIN_IDS
export $(grep -v '^#' .env | xargs)
python -m bot.main
```
Docker: `docker compose up --build` (FSM хранится в Redis).

## Команды
/start, /help, /cancel, /stock, /search <текст>, /critical, /receive, /writeoff, /new;
администратор: /admin, /users, /statistics.

## Тесты и демонстрация без Telegram
```bash
python -m pytest -v               # 22 теста: сервисы + handlers через эмулятор
python demo_chat.py               # сценарии в эмуляторе → screenshots/chat_*.png
```
`emulator.py` подменяет HTTP-сессию aiogram (FakeSession): Update подаются в Dispatcher.feed_update(),
ответы Bot API перехватываются, поэтому handlers, фильтры, FSM и middleware работают как в реальном боте.
