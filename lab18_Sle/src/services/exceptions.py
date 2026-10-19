class WarehouseError(Exception):
    """Базовая ошибка предметной области."""


class NotFoundError(WarehouseError):
    """Объект (товар, склад) не найден."""


class ValidationError(WarehouseError):
    """Некорректные входные данные."""


class DuplicateError(WarehouseError):
    """Повторное создание объекта с тем же уникальным ключом."""


class InsufficientStockError(WarehouseError):
    """Недопустимая операция: остаток стал бы отрицательным."""
