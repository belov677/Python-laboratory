class AppError(Exception):
    status_code = 400


class ValidationError(AppError):
    status_code = 400

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409
