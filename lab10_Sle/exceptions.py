class ApiError(Exception):
    status = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class ValidationError(ApiError):
    status, code = 400, "VALIDATION_ERROR"


class ItemNotFoundError(ApiError):
    status, code = 404, "ITEM_NOT_FOUND"


class ConflictError(ApiError):
    status, code = 409, "CONFLICT"
