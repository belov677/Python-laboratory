"""Фоновый worker уведомлений: python -m app.worker"""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.core.database import make_engine, make_sessions
from app.core.events import consume
from app.core.observability import setup_logging
from app.services.notifications import handle_event

EVENTS = ["OrderCreated", "OrderCancelled", "DeliveryScheduled", "DeliveryStatusChanged"]


async def main() -> None:
    settings = Settings()
    setup_logging(settings.log_level)
    log = logging.getLogger("app.worker")
    sessions = make_sessions(make_engine(settings.database_url))
    while True:
        try:
            connection = await consume(
                settings.broker_url, "notifications", EVENTS, lambda event: handle_event(sessions, event)
            )
            break
        except Exception as error:  # noqa: BLE001 — брокер ещё не готов
            log.warning("брокер недоступен (%s), повтор через 3 с", error)
            await asyncio.sleep(3)
    log.info("worker уведомлений запущен, события: %s", ", ".join(EVENTS))
    try:
        await asyncio.Future()  # работаем до остановки контейнера
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
