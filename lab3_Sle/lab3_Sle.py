# Лабораторная работа №3. Вариант 17 — «Платёжная система».
# Базовый класс Payment, производные CardPayment и CashPayment,
# класс PaymentSystem, содержащий платежи (композиция).

from abc import ABC, abstractmethod


class Customer:
    """Плательщик. Объект Customer входит в состав платежа (композиция)."""

    def __init__(self, name, email):
        self.name = name
        self.email = email

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Payment(ABC):
    """Базовый абстрактный класс платежа."""

    currency = "RUB"          # атрибут класса — общий для всех платежей
    _next_id = 1

    def __init__(self, customer, amount, purpose):
        self.id = Payment._next_id
        Payment._next_id += 1
        self.customer = customer          # композиция: Payment HAS-A Customer
        self.amount = amount              # проходит проверку через setter
        self.purpose = purpose
        self._status = "created"

    # --- инкапсуляция: сумма и статус меняются только контролируемо ---
    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if value <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        if getattr(self, "_status", "created") != "created":
            raise ValueError("Нельзя изменить сумму проведённого платежа")
        self._amount = round(float(value), 2)

    @property
    def status(self):
        return self._status

    # --- общий интерфейс ---
    @abstractmethod
    def commission(self):
        """Комиссия за платёж."""

    @abstractmethod
    def payment_type(self):
        """Название способа оплаты."""

    def total(self):
        return round(self.amount + self.commission(), 2)

    def process(self):
        """Обработка платежа — общий (полиморфный) метод."""
        if self._status != "created":
            raise ValueError(f"Платёж №{self.id} уже обработан (статус {self._status})")
        self._status = "completed"
        return (f"Платёж №{self.id} ({self.payment_type()}) проведён: "
                f"{self.amount:.2f} + комиссия {self.commission():.2f} = "
                f"{self.total():.2f} {self.currency}")

    def refund(self):
        if self._status != "completed":
            raise ValueError("Вернуть можно только проведённый платёж")
        self._status = "refunded"
        return f"Платёж №{self.id}: возвращено {self.amount:.2f} {self.currency}"

    def get_info(self):
        return (f"№{self.id} | {self.payment_type():20} | {self.customer.name:15} | "
                f"{self.amount:9.2f} | комиссия {self.commission():6.2f} | {self._status}")

    # --- специальные методы ---
    def __str__(self):
        return self.get_info()

    def __repr__(self):
        return f"{type(self).__name__}(id={self.id}, amount={self.amount})"

    def __eq__(self, other):
        return isinstance(other, Payment) and self.total() == other.total()

    def __lt__(self, other):
        return self.total() < other.total()

    def __add__(self, other):
        """Сумма двух платежей (или числа и платежа) — для sum()."""
        if isinstance(other, Payment):
            return self.total() + other.total()
        return self.total() + other

    def __radd__(self, other):
        return self.__add__(other)


class CardPayment(Payment):
    """Оплата картой — учитывается комиссия."""

    COMMISSION_PERCENT = 1.5
    MIN_COMMISSION = 10.0

    def __init__(self, customer, amount, purpose, card_number):
        super().__init__(customer, amount, purpose)
        digits = card_number.replace(" ", "")
        if len(digits) != 16 or not digits.isdigit():
            raise ValueError("Номер карты должен содержать 16 цифр")
        self._card_number = digits

    @property
    def masked_card(self):
        return "**** **** **** " + self._card_number[-4:]

    def commission(self):
        return round(max(self.amount * self.COMMISSION_PERCENT / 100, self.MIN_COMMISSION), 2)

    def payment_type(self):
        return "Карта " + self.masked_card[-4:]


class CreditCardPayment(CardPayment):
    """Ещё один уровень наследования: кредитная карта с повышенной комиссией."""

    COMMISSION_PERCENT = 3.0

    def payment_type(self):
        return "Кредитная карта " + self.masked_card[-4:]


class CashPayment(Payment):
    """Оплата наличными — комиссия отсутствует, рассчитывается сдача."""

    def __init__(self, customer, amount, purpose, cash_received):
        super().__init__(customer, amount, purpose)
        if cash_received < amount:
            raise ValueError("Полученных наличных недостаточно для оплаты")
        self.cash_received = cash_received

    def commission(self):
        return 0.0

    def change(self):
        return round(self.cash_received - self.amount, 2)

    def payment_type(self):
        return "Наличные"

    def process(self):
        result = super().process()
        return result + f"; сдача {self.change():.2f}"


class PaymentSystem:
    """Платёжная система — содержит коллекцию платежей (композиция)."""

    def __init__(self, name):
        self.name = name
        self._payments = []

    def add(self, payment):
        self._payments.append(payment)

    def remove(self, payment_id):
        payment = self.find_by_id(payment_id)
        self._payments.remove(payment)
        return payment

    def find_by_id(self, payment_id):
        for payment in self._payments:
            if payment.id == payment_id:
                return payment
        raise KeyError(f"Платёж №{payment_id} не найден")

    def find(self, customer_name=None, status=None):
        """Поиск по нескольким параметрам."""
        return [p for p in self._payments
                if (customer_name is None or p.customer.name == customer_name)
                and (status is None or p.status == status)]

    def process_all(self):
        results = []
        for payment in self._payments:       # полиморфизм: process() у каждого свой
            if payment.status == "created":
                results.append(payment.process())
        return results

    def turnover(self):
        return round(sum(p for p in self._payments if p.status == "completed"), 2)

    def total_commission(self):
        return round(sum(p.commission() for p in self._payments if p.status == "completed"), 2)

    def statistics(self):
        completed = self.find(status="completed")
        return {
            "всего платежей": len(self._payments),
            "проведено": len(completed),
            "возвращено": len(self.find(status="refunded")),
            "оборот, руб.": self.turnover(),
            "комиссия, руб.": self.total_commission(),
            "средний платёж, руб.": round(self.turnover() / len(completed), 2) if completed else 0,
        }

    def __len__(self):
        return len(self._payments)

    def __iter__(self):
        return PaymentIterator(self._payments)


class PaymentIterator:
    """Собственный итератор по платежам системы."""

    def __init__(self, payments):
        self._payments = payments
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._payments):
            raise StopIteration
        payment = self._payments[self._index]
        self._index += 1
        return payment


def section(title):
    print(f"\n===== {title} =====")


def main():
    system = PaymentSystem("PaySle")
    ivan = Customer("Иван Петров", "ivan@mail.ru")
    anna = Customer("Анна Смирнова", "anna@mail.ru")
    oleg = Customer("Олег Соколов", "oleg@mail.ru")

    section("Тест 1. Создание объектов каждого типа")
    payments = [
        CardPayment(ivan, 2500, "Интернет", "1234 5678 9012 3456"),
        CashPayment(anna, 780, "Продукты", cash_received=1000),
        CreditCardPayment(oleg, 12000, "Ноутбук", "4111111111111111"),
        CardPayment(anna, 300, "Такси", "5555 4444 3333 2222"),
        CashPayment(ivan, 150, "Кофе", cash_received=150),
    ]
    for p in payments:
        system.add(p)
        print(repr(p), "-", p.customer)

    section("Тест 2–3. Общий метод process() и переопределённые методы")
    for line in system.process_all():
        print(line)

    section("Тест 4. Изменение состояния объекта")
    taxi = system.find_by_id(4)
    print("Статус до возврата:", taxi.status)
    print(taxi.refund())
    print("Статус после возврата:", taxi.status)

    section("Тест 5. Обработка некорректного значения свойства")
    checks = [
        ("отрицательная сумма", lambda: CardPayment(ivan, -100, "Ошибка", "1234567812345678")),
        ("сумма-строка", lambda: CashPayment(ivan, "сто", "Ошибка", 200)),
        ("короткий номер карты", lambda: CardPayment(ivan, 100, "Ошибка", "1234")),
        ("недостаточно наличных", lambda: CashPayment(ivan, 500, "Ошибка", 100)),
        ("изменение суммы проведённого платежа", lambda: setattr(payments[0], "amount", 1)),
        ("повторная обработка", lambda: payments[1].process()),
        ("создание абстрактного Payment", lambda: Payment(ivan, 100, "Ошибка")),
    ]
    for name, action in checks:
        try:
            action()
            print(f"{name}: ошибка НЕ обнаружена")
        except (ValueError, TypeError) as error:
            print(f"{name}: {type(error).__name__}: {error}")

    section("Тест 6. Полиморфная коллекция (через собственный итератор)")
    for payment in system:
        print(payment)

    section("Тест 7. Композиция: статистика платёжной системы " + system.name)
    for key, value in system.statistics().items():
        print(f"{key:22} {value}")

    section("Дополнительно: сортировка, поиск, перегрузка операторов")
    for p in sorted(system):
        print(f"{p.total():10.2f}  {p.payment_type()}")
    print("Платежи Ивана Петрова:", [repr(p) for p in system.find(customer_name="Иван Петров")])
    print("Сумма двух первых платежей (оператор +):", payments[0] + payments[1])
    print("Платежи 2 и 5 равны по итоговой сумме:", payments[1] == payments[4])


if __name__ == "__main__":
    main()
