from __future__ import annotations

from dataclasses import asdict, dataclass

from exceptions import ValidationError

CATEGORIES = {"обезболивающие", "антибиотики", "витамины", "противовирусные",
              "сердечные", "антигистаминные"}


@dataclass
class Medicine:
    id: int
    name: str
    category: str
    manufacturer: str
    price: float
    quantity: int
    prescription: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Название препарата не может быть пустым")
        if self.category not in CATEGORIES:
            raise ValidationError(f"Неизвестная категория «{self.category}». "
                                  f"Допустимые: {', '.join(sorted(CATEGORIES))}")
        if not isinstance(self.price, (int, float)) or self.price <= 0:
            raise ValidationError("Цена должна быть положительным числом")
        if not isinstance(self.quantity, int) or self.quantity < 0:
            raise ValidationError("Количество должно быть неотрицательным целым числом")

    def to_dict(self) -> dict:
        return asdict(self)
