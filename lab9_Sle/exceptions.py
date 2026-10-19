class PharmacyError(Exception):
    """Базовая ошибка приложения."""


class MedicineNotFoundError(PharmacyError):
    pass


class ValidationError(PharmacyError):
    pass


class ProtocolError(PharmacyError):
    """Нарушение формата сообщений протокола."""
