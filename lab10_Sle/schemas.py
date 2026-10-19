"""Валидация входных данных API."""
from __future__ import annotations

from exceptions import ValidationError

FIELDS = {
    "sku": str, "name": str, "category": str, "quantity": int,
    "min_stock": int, "price": (int, float), "location": str,
}


def validate_item(data: object, partial: bool = False) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Тело запроса должно быть JSON-объектом")
    unknown = set(data) - set(FIELDS)
    if unknown:
        raise ValidationError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
    if not partial:
        missing = set(FIELDS) - set(data)
        if missing:
            raise ValidationError(f"Отсутствуют поля: {', '.join(sorted(missing))}")
    if partial and not data:
        raise ValidationError("Не передано ни одного поля для изменения")
    result = {}
    for key, value in data.items():
        expected = FIELDS[key]
        if isinstance(value, bool) or not isinstance(value, expected):
            raise ValidationError(f"Поле {key} имеет неверный тип")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValidationError(f"Поле {key} не может быть пустым")
        result[key] = value
    if result.get("price", 1) <= 0:
        raise ValidationError("price должна быть больше 0")
    for key in ("quantity", "min_stock"):
        if result.get(key, 0) < 0:
            raise ValidationError(f"{key} не может быть отрицательным")
    if "price" in result:
        result["price"] = float(result["price"])
    return result
