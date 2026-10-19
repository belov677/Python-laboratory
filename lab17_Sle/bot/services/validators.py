"""Проверка пользовательского ввода (без зависимости от Telegram)."""
import re

from .exceptions import ValidationError

SKU = re.compile(r"^[A-Z]{2,4}-\d{3,6}$")


def parse_quantity(text: str, maximum: int = 100_000) -> int:
    text = (text or "").strip()
    if not text.lstrip("-").isdigit():
        raise ValidationError("Количество должно быть целым числом, например 15")
    value = int(text)
    if value <= 0:
        raise ValidationError("Количество должно быть больше нуля")
    if value > maximum:
        raise ValidationError(f"Слишком большое количество (максимум {maximum})")
    return value


def parse_price(text: str) -> float:
    try:
        value = float((text or "").replace(",", ".").replace(" ", ""))
    except ValueError:
        raise ValidationError("Цена должна быть числом, например 1290.50") from None
    if value <= 0:
        raise ValidationError("Цена должна быть больше нуля")
    return round(value, 2)


def parse_sku(text: str) -> str:
    sku = (text or "").strip().upper()
    if not SKU.match(sku):
        raise ValidationError("Артикул в формате ABC-123 (2–4 латинские буквы, дефис, 3–6 цифр)")
    return sku


def parse_name(text: str) -> str:
    name = (text or "").strip()
    if len(name) < 3:
        raise ValidationError("Название слишком короткое (минимум 3 символа)")
    if len(name) > 150:
        raise ValidationError("Название слишком длинное (максимум 150 символов)")
    return name


def parse_search(text: str) -> str:
    query = (text or "").strip()
    if len(query) < 2:
        raise ValidationError("Введите для поиска минимум 2 символа")
    return query
