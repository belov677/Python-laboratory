from enum import Enum


class SupplyStatus(Enum):
    EXPECTED = "ожидается"
    RECEIVED = "принята"
    CANCELLED = "отменена"
