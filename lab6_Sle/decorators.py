"""Собственные декораторы."""
from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable

from exceptions import InvalidStatusTransitionError


def log_call(func: Callable) -> Callable:
    """Журналирование вызова: имя, аргументы и результат."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        skip = 1 if args and hasattr(args[0], func.__name__) else 0   # self у методов
        shown = [repr(a) for a in args[skip:]] + [f"{k}={v!r}" for k, v in kwargs.items()]
        print(f"[LOG] вызван метод {func.__name__}({', '.join(shown)})")
        result = func(*args, **kwargs)
        text = repr(result)
        print(f"[LOG] {func.__name__} вернул {text[:70] + '...' if len(text) > 70 else text}")
        return result
    return wrapper


def measure_time(func: Callable) -> Callable:
    """Измерение времени выполнения."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            print(f"[PERFORMANCE] {func.__name__}: {time.perf_counter() - start:.6f} sec")
    return wrapper


def require_status(*allowed: Any) -> Callable:
    """Декоратор с параметрами: метод разрешён только для поставок с указанными статусами.

    Декорируемый метод принимает идентификатор поставки вторым аргументом.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, delivery_id: int, *args: Any, **kwargs: Any) -> Any:
            delivery = self.get_delivery(delivery_id)
            if delivery.status not in allowed:
                names = ", ".join(s.value for s in allowed)
                raise InvalidStatusTransitionError(
                    f"{func.__name__}: поставка {delivery.name} в статусе "
                    f"«{delivery.status.value}», требуется: {names}")
            return func(self, delivery_id, *args, **kwargs)
        return wrapper
    return decorator


def repeat(count: int) -> Callable:
    """Декоратор с параметром: выполнить функцию count раз."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = None
            for _ in range(count):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


def command(name: str, order: int) -> Callable:
    """Регистрирует метод как пункт меню (обнаруживается через inspect)."""
    def decorator(func: Callable) -> Callable:
        func.menu_command = name
        func.menu_order = order
        return func
    return decorator
