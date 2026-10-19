"""Лабораторная №7, вариант 17 «Склад». ВЕРСИЯ 1 — намеренно проблемная архитектура.

Нарушения SOLID отмечены комментариями «НАРУШЕНИЕ».
"""
import json


class Product:
    def __init__(self, sku, name, price):
        self.sku = sku
        self.name = name
        self.price = price

    def days_to_expire(self):
        return 30


class NonPerishableProduct(Product):
    # НАРУШЕНИЕ LSP: наследник не может выполнить контракт базового класса
    def days_to_expire(self):
        raise NotImplementedError("У непортящегося товара нет срока годности")


class IWarehouseManager:
    # НАРУШЕНИЕ ISP: один огромный интерфейс для всех клиентов
    def receive(self, sku, qty, warehouse): ...
    def write_off(self, sku, qty, warehouse): ...
    def move(self, sku, qty, src, dst): ...
    def inventory(self, warehouse): ...
    def save(self): ...
    def load(self): ...
    def send_email(self, text): ...
    def print_report(self): ...


class WarehouseManager(IWarehouseManager):
    """НАРУШЕНИЕ SRP: хранение, бизнес-логика, уведомления, отчёты и консоль в одном классе."""

    def __init__(self):
        self.products = {}
        self.stock = {}          # (warehouse, sku) -> qty
        # НАРУШЕНИЕ DIP: жёстко заданная реализация хранения
        self.filename = "stock.json"

    def add_product(self, product):
        self.products[product.sku] = product

    def process(self, operation, sku, qty, warehouse, target=None):
        # НАРУШЕНИЕ OCP: новая операция требует изменения этого метода
        if operation == "receive":
            self.stock[(warehouse, sku)] = self.stock.get((warehouse, sku), 0) + qty
            self.send_email(f"Поступление {sku}: {qty}")
        elif operation == "write_off":
            if self.stock.get((warehouse, sku), 0) < qty:
                print("Недостаточно товара!")          # консоль внутри бизнес-логики
                return
            self.stock[(warehouse, sku)] -= qty
            self.send_email(f"Списание {sku}: {qty}")
        elif operation == "move":
            if self.stock.get((warehouse, sku), 0) < qty:
                print("Недостаточно товара для перемещения!")
                return
            self.stock[(warehouse, sku)] -= qty
            self.stock[(target, sku)] = self.stock.get((target, sku), 0) + qty
            self.send_email(f"Перемещение {sku}: {qty} {warehouse}->{target}")
        elif operation == "inventory":
            counted = int(input(f"Фактическое количество {sku} на {warehouse}: "))
            diff = counted - self.stock.get((warehouse, sku), 0)
            self.stock[(warehouse, sku)] = counted
            print(f"Расхождение: {diff:+}")
        else:
            print("Неизвестная операция")

    def send_email(self, text):
        # уведомление «зашито» в класс
        print(f"[EMAIL to manager@sklad.ru] {text}")

    def save(self):
        data = {f"{w}|{s}": q for (w, s), q in self.stock.items()}
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self):
        with open(self.filename, encoding="utf-8") as f:
            self.stock = {tuple(k.split("|")): v for k, v in json.load(f).items()}

    def print_report(self):
        print("=== Остатки ===")
        for (w, s), q in sorted(self.stock.items()):
            print(f"{w:10} {s:8} {q:5}")
        expiring = []
        for p in self.products.values():
            expiring.append((p.sku, p.days_to_expire()))   # упадёт на NonPerishableProduct
        print("Сроки годности:", expiring)

    def inventory(self, warehouse):
        for (w, s) in list(self.stock):
            if w == warehouse:
                self.process("inventory", s, 0, w)


def main():
    m = WarehouseManager()
    m.add_product(Product("MLK-1", "Молоко", 89))
    m.add_product(NonPerishableProduct("NB-1", "Ноутбук", 54990))
    m.process("receive", "MLK-1", 100, "Центральный")
    m.process("receive", "NB-1", 10, "Центральный")
    m.process("move", "NB-1", 4, "Центральный", "Северный")
    m.process("write_off", "MLK-1", 500, "Центральный")
    m.process("return", "MLK-1", 1, "Центральный")
    m.inventory("Северный")
    m.save()
    try:
        m.print_report()
    except NotImplementedError as error:
        print("Отчёт не построен:", error)


if __name__ == "__main__":
    main()
