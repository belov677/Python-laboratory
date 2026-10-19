"""Пользовательские исключения складской системы."""


class WarehouseError(Exception):
    """Базовое исключение приложения."""


class EntityNotFoundError(WarehouseError):
    """Объект с указанным идентификатором отсутствует."""


class InvalidStatusTransitionError(WarehouseError):
    """Недопустимое изменение статуса поставки."""


class CapacityExceededError(WarehouseError):
    """Превышена вместимость склада."""
