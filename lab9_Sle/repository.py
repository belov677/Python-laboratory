from __future__ import annotations

import threading

from exceptions import MedicineNotFoundError
from models import Medicine


class MedicineRepository:
    """Хранение препаратов в памяти. Lock защищает данные от гонок между потоками."""

    def __init__(self) -> None:
        self._items: dict[int, Medicine] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def add(self, data: dict) -> Medicine:
        with self._lock:
            medicine = Medicine(id=self._next_id, **data)
            self._items[medicine.id] = medicine
            self._next_id += 1
            return medicine

    def get(self, medicine_id: int) -> Medicine:
        with self._lock:
            if medicine_id not in self._items:
                raise MedicineNotFoundError(f"Препарат с id={medicine_id} не найден")
            return self._items[medicine_id]

    def get_all(self) -> list[Medicine]:
        with self._lock:
            return list(self._items.values())

    def update(self, medicine_id: int, fields: dict) -> Medicine:
        with self._lock:
            if medicine_id not in self._items:
                raise MedicineNotFoundError(f"Препарат с id={medicine_id} не найден")
            current = self._items[medicine_id].to_dict()
            current.update(fields)
            updated = Medicine(**current)          # повторная валидация
            self._items[medicine_id] = updated
            return updated

    def delete(self, medicine_id: int) -> None:
        with self._lock:
            if self._items.pop(medicine_id, None) is None:
                raise MedicineNotFoundError(f"Препарат с id={medicine_id} не найден")
