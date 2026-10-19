"""Простой контейнер зависимостей (дополнительное задание высокого уровня)."""
from __future__ import annotations

from typing import Any, Callable


class Container:
    def __init__(self) -> None:
        self._factories: dict[Any, Callable[["Container"], Any]] = {}
        self._instances: dict[Any, Any] = {}

    def register(self, interface: Any, factory: Callable[["Container"], Any]) -> None:
        self._factories[interface] = factory
        self._instances.pop(interface, None)

    def resolve(self, interface: Any) -> Any:
        if interface not in self._instances:          # singleton в пределах контейнера
            if interface not in self._factories:
                raise KeyError(f"Зависимость {getattr(interface, '__name__', interface)} "
                               "не зарегистрирована")
            self._instances[interface] = self._factories[interface](self)
        return self._instances[interface]
