from __future__ import annotations

from exceptions import ValidationError
from models import CATEGORIES, Medicine
from repository import MedicineRepository

ALLOWED_FIELDS = {"name", "category", "manufacturer", "price", "quantity", "prescription"}
REQUIRED_FIELDS = ALLOWED_FIELDS - {"prescription"}


class PharmacyService:
    def __init__(self, repository: MedicineRepository) -> None:
        self.repository = repository

    def list_medicines(self) -> list[Medicine]:
        return self.repository.get_all()

    def get_medicine(self, medicine_id: int) -> Medicine:
        return self.repository.get(self._id(medicine_id))

    def create_medicine(self, data: dict) -> Medicine:
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            raise ValidationError(f"Отсутствуют обязательные поля: {', '.join(sorted(missing))}")
        return self.repository.add(self._clean(data))

    def update_medicine(self, medicine_id: int, data: dict) -> Medicine:
        fields = self._clean(data)
        if not fields:
            raise ValidationError("Не переданы поля для изменения")
        return self.repository.update(self._id(medicine_id), fields)

    def delete_medicine(self, medicine_id: int) -> None:
        self.repository.delete(self._id(medicine_id))

    def search_by_category(self, category: str) -> list[Medicine]:
        """Специализированная операция варианта 17."""
        if category not in CATEGORIES:
            raise ValidationError(f"Неизвестная категория «{category}»")
        return sorted((m for m in self.repository.get_all() if m.category == category),
                      key=lambda m: m.price)

    def statistics(self) -> dict:
        items = self.repository.get_all()
        return {"medicines": len(items),
                "units": sum(m.quantity for m in items),
                "out_of_stock": sum(1 for m in items if m.quantity == 0),
                "categories": len({m.category for m in items})}

    @staticmethod
    def _id(value) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError("Идентификатор должен быть положительным целым числом")
        return value

    @staticmethod
    def _clean(data: dict) -> dict:
        unknown = data.keys() - ALLOWED_FIELDS
        if unknown:
            raise ValidationError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
        return dict(data)
