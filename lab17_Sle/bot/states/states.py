from aiogram.fsm.state import State, StatesGroup


class Movement(StatesGroup):
    """Поступление / списание: товар → склад → количество → подтверждение."""
    product = State()
    warehouse = State()
    quantity = State()
    confirm = State()


class NewProduct(StatesGroup):
    name = State()
    sku = State()
    price = State()
    min_stock = State()
    supplier = State()
    confirm = State()


class EditProduct(StatesGroup):
    value = State()


class Search(StatesGroup):
    query = State()
