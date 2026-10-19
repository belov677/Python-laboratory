"""Иерархия ошибок приложения. Каждая ошибка знает свой HTTP-код и машинный код для клиента."""

from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, entity: str, entity_id) -> None:
        super().__init__(f"{entity} с id={entity_id} не найден(а)", code=f"{entity.upper()}_NOT_FOUND")


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class BusinessRuleError(AppError):
    """Нарушение бизнес-правила (данные корректны, но операция недопустима)."""

    status_code = 409
    code = "BUSINESS_RULE_VIOLATION"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
