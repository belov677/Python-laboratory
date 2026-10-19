class LogisticsError(Exception):
    """Базовая ошибка бизнес-логики."""


class NotFoundError(LogisticsError):
    pass


class DuplicateError(LogisticsError):
    pass


class ValidationError(LogisticsError):
    pass


class InvalidStatusError(LogisticsError):
    pass
