from __future__ import annotations

from typing import Protocol

from models.entities import Batch


class PickingStrategy(Protocol):
    """Стратегия отбора партий при отгрузке."""
    name: str

    def order(self, batches: list[Batch]) -> list[Batch]: ...
