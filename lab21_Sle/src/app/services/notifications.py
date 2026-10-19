"""Обработка событий фоновым worker: уведомления клиентов (отправка e-mail/SMS имитируется журналом)."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from app.models.entities import Notification

log = logging.getLogger("app.worker")
STATUS_TEXT = {"IN_TRANSIT": "груз в пути", "DELIVERED": "груз доставлен", "CANCELLED": "рейс отменён"}


def render(event: dict) -> str | None:
    p = event["payload"]
    match event["name"]:
        case "OrderCreated":
            return f"Заказ №{p['order_id']} ({p['route']}) принят. Мы подберём транспорт и сообщим детали."
        case "DeliveryScheduled":
            start = datetime.fromisoformat(p["start"]).strftime("%d.%m.%Y %H:%M")
            return (
                f"Заказ №{p['order_id']}: назначен {p['vehicle']}, водитель {p['driver']}, подача "
                f"{start}. Стоимость {p['cost']:.2f} руб."
            )
        case "DeliveryStatusChanged":
            return f"Заказ №{p['order_id']}: {STATUS_TEXT.get(p['status'], p['status'])}."
        case "OrderCancelled":
            return f"Заказ №{p['order_id']} отменён."
    return None


async def handle_event(sessions, event: dict) -> Notification | None:
    """Идемпотентно: повторно доставленное событие не создаёт второе уведомление."""
    text = render(event)
    if text is None:
        return None
    async with sessions() as session:
        if await session.scalar(select(Notification.id).where(Notification.event_id == event["id"])):
            log.info("событие %s уже обработано", event["id"][:8])
            return None
        notification = Notification(user_id=event["payload"]["customer_id"], event_id=event["id"], text=text)
        session.add(notification)
        await session.commit()
    log.info("уведомление клиенту %s (e-mail, имитация отправки): %s", notification.user_id, text)
    return notification
