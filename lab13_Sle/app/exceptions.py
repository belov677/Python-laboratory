class WarehouseError(Exception):
    pass


class ItemNotFoundError(WarehouseError):
    pass


class ValidationError(WarehouseError):
    pass


class StorageUnavailableError(WarehouseError):
    pass
