"""Этап 1. Наивная реализация без паттернов (вариант 17 «Склад»)."""
from datetime import date

batches = []          # хранение прямо в модуле
history = []


def create(kind, **data):
    # создание объектов — if/elif разбросан по коду
    if kind == "product":
        return {"type": "product", **data}
    elif kind == "batch":
        return {"type": "batch", **data}
    elif kind == "supply":
        return {"type": "supply", **data}
    raise ValueError(kind)


def ship(sku, quantity, mode):
    # выбор алгоритма — if/elif внутри бизнес-логики
    items = [b for b in batches if b["sku"] == sku and b["quantity"] > 0]
    if mode == "fifo":
        items.sort(key=lambda b: b["received"])
    elif mode == "priority":
        items.sort(key=lambda b: (-b["priority"], b["received"]))
    elif mode == "expiry":
        items.sort(key=lambda b: b["expiry"])
    taken = []
    for b in items:
        if quantity == 0:
            break
        q = min(quantity, b["quantity"])
        b["quantity"] -= q
        quantity -= q
        taken.append((b["id"], q))
    return taken


def run(command, *args):
    # операции — if/elif, отмена невозможна
    result = None
    if command == "receive":
        batches.append(create("batch", **args[0]))
    elif command == "ship":
        result = ship(*args)
    history.append(command)
    return result


if __name__ == "__main__":
    run("receive", {"id": 1, "sku": "MLK", "quantity": 50, "received": 1, "priority": 0,
                    "expiry": date(2026, 10, 25)})
    run("receive", {"id": 2, "sku": "MLK", "quantity": 30, "received": 2, "priority": 1,
                    "expiry": date(2026, 10, 18)})
    print("FIFO:", run("ship", "MLK", 40, "fifo"))
    print("По сроку годности:", run("ship", "MLK", 15, "expiry"))
    print("Остатки:", [(b["id"], b["quantity"]) for b in batches])
    print("История:", history, "— отменить последнюю операцию нельзя")
