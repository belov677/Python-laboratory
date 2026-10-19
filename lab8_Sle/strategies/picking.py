"""Стратегии отбора партий (Strategy)."""
from __future__ import annotations

from models.entities import Batch


class FifoStrategy:
    name = "FIFO"

    def order(self, batches: list[Batch]) -> list[Batch]:
        return sorted(batches, key=lambda b: b.received_order)


class PriorityStrategy:
    name = "приоритетная обработка"

    def order(self, batches: list[Batch]) -> list[Batch]:
        return sorted(batches, key=lambda b: (-b.priority, b.received_order))


class ExpiryStrategy:
    """FEFO: первым отгружается товар с ближайшим сроком годности."""
    name = "по сроку годности"

    def order(self, batches: list[Batch]) -> list[Batch]:
        return sorted(batches, key=lambda b: (b.expiry_date, b.received_order))
