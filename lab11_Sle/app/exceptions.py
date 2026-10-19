class ApiError(Exception):
    status, code = 400, "BAD_REQUEST"


class ValidationError(ApiError):
    status, code = 400, "VALIDATION_ERROR"


class ItemNotFoundError(ApiError):
    status, code = 404, "ITEM_NOT_FOUND"


class ConflictError(ApiError):
    status, code = 409, "CONFLICT"


class InsufficientStockError(ApiError):
    status, code = 409, "INSUFFICIENT_STOCK"
