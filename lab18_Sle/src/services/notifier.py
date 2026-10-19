"""Уведомления о критическом остатке (в реальной системе — e-mail/Telegram)."""
import logging

log = logging.getLogger("warehouse.notifier")


class LogNotifier:
    def notify_low_stock(self, product, total: int) -> None:
        log.warning("Критический остаток: %s %s — %s %s (минимум %s)",
                    product.sku, product.name, total, product.unit, product.min_stock)
