"""Эмулятор Telegram для демонстрации и тестов без сети и токена.

FakeSession подменяет HTTP-сессию aiogram: все вызовы Bot API (sendMessage, editMessageText,
answerCallbackQuery…) не уходят в Telegram, а записываются в журнал чата. ChatEmulator создаёт
объекты Update (сообщения и нажатия inline-кнопок) и передаёт их в Dispatcher.feed_update() —
обработчики, фильтры, FSM и middleware работают точно так же, как при long polling.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import (AnswerCallbackQuery, EditMessageReplyMarkup, EditMessageText,
                             SendMessage, TelegramMethod)
from aiogram.types import (CallbackQuery, Chat, InlineKeyboardMarkup, Message,
                           ReplyKeyboardMarkup, Update, User)

BOT_USER = User(id=1, is_bot=True, first_name="Склад-бот", username="warehouse_sle_bot")


@dataclass
class ChatMessage:
    id: int
    chat_id: int
    sender: str                    # user / bot / service
    text: str
    inline: list[list[tuple[str, str]]] = field(default_factory=list)  # (текст, callback_data)
    time: str = ""
    edited: bool = False


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.ids = itertools.count(100)
        self.messages: dict[int, ChatMessage] = {}
        self.timeline: list[ChatMessage] = []
        self.reply_keyboard: dict[int, list[list[str]]] = {}
        self.calls: list[str] = []

    @staticmethod
    def _inline(markup: Any) -> list[list[tuple[str, str]]]:
        if isinstance(markup, InlineKeyboardMarkup):
            return [[(b.text, b.callback_data) for b in row] for row in markup.inline_keyboard]
        return []

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None):
        self.calls.append(type(method).__name__)
        now = datetime.now()
        if isinstance(method, SendMessage):
            msg = ChatMessage(next(self.ids), int(method.chat_id), "bot", method.text,
                              self._inline(method.reply_markup), now.strftime("%H:%M"))
            if isinstance(method.reply_markup, ReplyKeyboardMarkup):
                self.reply_keyboard[msg.chat_id] = [[b.text for b in row]
                                                    for row in method.reply_markup.keyboard]
            self.messages[msg.id] = msg
            self.timeline.append(msg)
            return Message(message_id=msg.id, date=now, text=method.text, from_user=BOT_USER,
                           chat=Chat(id=msg.chat_id, type="private"))
        if isinstance(method, (EditMessageText, EditMessageReplyMarkup)):
            old = self.messages[method.message_id]
            # исходное сообщение остаётся в истории, изменённая версия добавляется после нажатия
            msg = ChatMessage(old.id, old.chat_id, "bot",
                              method.text if isinstance(method, EditMessageText) else old.text,
                              self._inline(method.reply_markup), now.strftime("%H:%M"), edited=True)
            self.messages[msg.id] = msg
            self.timeline.append(msg)
            return Message(message_id=msg.id, date=now, text=msg.text, from_user=BOT_USER,
                           chat=Chat(id=msg.chat_id, type="private"))
        if isinstance(method, AnswerCallbackQuery):
            if method.text:
                self.timeline.append(ChatMessage(0, 0, "service", f"всплывающее уведомление: {method.text}"))
            return True
        return True

    async def close(self) -> None:
        pass

    async def stream_content(self, *args, **kwargs):  # pragma: no cover - не используется
        yield b""


class ChatEmulator:
    def __init__(self, dp: Dispatcher, user_id: int = 5001, first_name: str = "Семён",
                 username: str = "sle_user") -> None:
        self.dp = dp
        self.session = FakeSession()
        self.bot = Bot("123456:EMULATOR", session=self.session,
                       default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.user = User(id=user_id, is_bot=False, first_name=first_name, username=username)
        self.update_ids = itertools.count(1)
        self.user_msg_ids = itertools.count(1)

    def as_user(self, user_id: int, first_name: str, username: str) -> "ChatEmulator":
        """Второй пользователь в том же диспетчере (общая сессия-журнал)."""
        other = ChatEmulator.__new__(ChatEmulator)
        other.__dict__.update(self.__dict__)
        other.user = User(id=user_id, is_bot=False, first_name=first_name, username=username)
        return other

    @property
    def timeline(self) -> list[ChatMessage]:
        return self.session.timeline

    def bot_messages(self) -> list[ChatMessage]:
        return [m for m in self.timeline if m.sender == "bot" and m.chat_id == self.user.id]

    def last(self) -> ChatMessage:
        return self.bot_messages()[-1]

    async def send(self, text: str) -> list[ChatMessage]:
        start = len(self.timeline)
        msg_id = next(self.user_msg_ids)
        self.timeline.append(ChatMessage(-msg_id, self.user.id, "user", text,
                                         time=datetime.now().strftime("%H:%M")))
        message = Message(message_id=msg_id, date=datetime.now(), text=text, from_user=self.user,
                          chat=Chat(id=self.user.id, type="private"))
        await self.dp.feed_update(self.bot, Update(update_id=next(self.update_ids), message=message))
        return [m for m in self.timeline[start:] if m.sender == "bot"]

    async def press(self, button_text: str, message: ChatMessage | None = None) -> list[ChatMessage]:
        """Нажать inline-кнопку (по началу текста) в последнем подходящем сообщении бота."""
        candidates = [message] if message else reversed(self.bot_messages())
        for msg in candidates:
            for row in msg.inline:
                for text, data in row:
                    if text.startswith(button_text) or button_text in text:
                        start = len(self.timeline)
                        self.timeline.append(ChatMessage(0, self.user.id, "service",
                                                         f"нажата кнопка «{text}»"))
                        bot_msg = Message(message_id=msg.id, date=datetime.now(), text=msg.text,
                                          from_user=BOT_USER, chat=Chat(id=self.user.id, type="private"))
                        call = CallbackQuery(id=str(next(self.update_ids)), from_user=self.user,
                                             chat_instance="emu", data=data, message=bot_msg)
                        await self.dp.feed_update(self.bot, Update(update_id=next(self.update_ids),
                                                                   callback_query=call))
                        return [m for m in self.timeline[start:] if m.sender == "bot"]
        raise LookupError(f"Кнопка «{button_text}» не найдена")


def render_html(messages: list[ChatMessage], title: str, keyboard: list[list[str]] | None,
                user_id: int | None = None) -> str:
    """HTML-страница в стиле Telegram для скриншота."""
    from html import escape
    parts = []
    for m in messages:
        if user_id is not None and m.chat_id not in (0, user_id):
            continue
        if m.sender == "service":
            parts.append(f'<div class="service">{escape(m.text)}</div>')
            continue
        body = m.text.replace("\n", "<br>") if m.sender == "bot" else escape(m.text)
        buttons = "".join(
            '<div class="row">' + "".join(f'<span class="ibtn">{escape(t)}</span>' for t, _ in row) + "</div>"
            for row in m.inline)
        parts.append(f'<div class="msg {m.sender}"><div class="bubble">{body}'
                     f'<span class="time">{"изменено " if m.edited else ""}{m.time}</span></div>'
                     f'{"<div class=inline>" + buttons + "</div>" if buttons else ""}</div>')
    kb = ""
    if keyboard:
        kb = '<div class="kb">' + "".join(
            '<div class="row">' + "".join(f'<span class="kbtn">{escape(t)}</span>' for t in row) + "</div>"
            for row in keyboard) + "</div>"
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>
body {{ margin:0; font-family: 'Segoe UI', Arial, sans-serif; background:#cfe3c2; width:560px; }}
.head {{ background:#517da2; color:#fff; padding:10px 16px; display:flex; gap:12px; align-items:center; }}
.avatar {{ width:40px; height:40px; border-radius:50%; background:#f2a541; display:flex; align-items:center;
  justify-content:center; font-size:22px; }}
.head b {{ display:block; }} .head small {{ opacity:.8; }}
.chat {{ padding:10px 12px; background: #d7e9c9; }}
.msg {{ display:flex; flex-direction:column; margin:6px 0; }}
.msg.user {{ align-items:flex-end; }} .msg.bot {{ align-items:flex-start; }}
.bubble {{ max-width:430px; padding:7px 10px 16px; border-radius:12px; font-size:14.5px; line-height:1.35;
  position:relative; box-shadow:0 1px 1px rgba(0,0,0,.15); min-width:60px; }}
.user .bubble {{ background:#effdde; border-bottom-right-radius:4px; }}
.bot .bubble {{ background:#fff; border-bottom-left-radius:4px; }}
.time {{ position:absolute; right:8px; bottom:2px; font-size:11px; color:#8a9a85; }}
code {{ background:#eef1f4; padding:0 3px; border-radius:3px; }}
.inline {{ max-width:452px; width:100%; margin-top:3px; }}
.row {{ display:flex; gap:3px; margin-top:3px; }}
.ibtn {{ flex:1; background:rgba(80,110,90,.45); color:#fff; text-align:center; padding:7px 6px; border-radius:8px;
  font-size:13.5px; }}
.service {{ text-align:center; margin:6px auto; font-size:12.5px; color:#fff; background:rgba(60,90,60,.45);
  border-radius:10px; padding:3px 10px; width:fit-content; }}
.kb {{ background:#f0f2f5; padding:6px; border-top:1px solid #ccd; }}
.kbtn {{ flex:1; background:#fff; text-align:center; padding:9px 4px; border-radius:6px; font-size:14px;
  box-shadow:0 1px 1px rgba(0,0,0,.15); }}
</style></head><body>
<div class="head"><div class="avatar">📦</div><div><b>Склад-бот</b><small>{escape(title)}</small></div></div>
<div class="chat">{''.join(parts)}</div>{kb}</body></html>"""
