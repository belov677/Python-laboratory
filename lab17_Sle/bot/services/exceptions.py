class InventoryError(Exception):
    """Базовая ошибка бизнес-логики (сообщение показывается пользователю)."""


class ValidationError(InventoryError):
    pass


class NotFoundError(InventoryError):
    pass


class NotEnoughStockError(InventoryError):
    pass
