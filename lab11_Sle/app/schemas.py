from __future__ import annotations

from exceptions import ValidationError

FIELDS = {"sku": str, "name": str, "category": str, "quantity": int, "min_stock": int,
          "price": (int, float), "location": str, "image_url": (str, type(None))}
REQUIRED = set(FIELDS) - {"image_url"}


def validate_item(data: object, partial: bool = False) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Тело запроса должно быть JSON-объектом")
    unknown = set(data) - set(FIELDS)
    if unknown:
        raise ValidationError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
    missing = REQUIRED - set(data)
    if not partial and missing:
        raise ValidationError(f"Отсутствуют поля: {', '.join(sorted(missing))}")
    if partial and not data:
        raise ValidationError("Не передано ни одного поля")
    clean = {}
    for key, value in data.items():
        if isinstance(value, bool) or not isinstance(value, FIELDS[key]):
            raise ValidationError(f"Поле {key} имеет неверный тип")
        if isinstance(value, str):
            value = value.strip()
            if not value and key != "image_url":
                raise ValidationError(f"Поле {key} не может быть пустым")
        clean[key] = value
    if clean.get("price", 1) <= 0:
        raise ValidationError("price должна быть больше 0")
    if clean.get("quantity", 0) < 0 or clean.get("min_stock", 0) < 0:
        raise ValidationError("Количество и минимальный остаток не могут быть отрицательными")
    return clean


def validate_movement(data: object) -> tuple[int, int | None]:
    if not isinstance(data, dict) or not isinstance(data.get("quantity"), int) \
            or isinstance(data.get("quantity"), bool) or data["quantity"] <= 0:
        raise ValidationError("quantity должно быть положительным целым числом")
    supplier = data.get("supplier_id")
    if supplier is not None and (not isinstance(supplier, int) or supplier <= 0):
        raise ValidationError("supplier_id должен быть положительным целым числом")
    return data["quantity"], supplier
