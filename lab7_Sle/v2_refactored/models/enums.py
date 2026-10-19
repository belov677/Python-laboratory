from enum import Enum


class OperationType(Enum):
    RECEIPT = "поступление"
    WRITE_OFF = "списание"
    TRANSFER = "перемещение"
    INVENTORY = "инвентаризация"
    RETURN = "возврат поставщику"
