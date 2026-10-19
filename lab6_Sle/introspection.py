"""Интроспекция объектов."""
from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass

from models import Entity
from protocols import Reportable


def inspect_object(obj: object) -> None:
    cls = type(obj)
    print("=== ИНФОРМАЦИЯ ОБ ОБЪЕКТЕ ===")
    print("Тип:", cls.__name__)
    print("Модуль:", cls.__module__)
    print("Иерархия:", " → ".join(c.__name__ for c in cls.__mro__))
    print("Наследник Entity:", issubclass(cls, Entity))
    print("Соответствует протоколу Reportable:", isinstance(obj, Reportable))
    if hasattr(obj, "id"):
        print("ID:", getattr(obj, "id"))
    print("Атрибуты:")
    names = [f.name for f in fields(obj)] if is_dataclass(obj) else list(vars(obj))
    for name in names:
        print(f"   {name} = {getattr(obj, name)!r}")
    print("Методы:")
    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_"):
            print(f"   {name}{inspect.signature(member)}")
    public = [n for n in dir(obj) if not n.startswith("_")]
    print(f"Всего публичных имён (dir): {len(public)}")
