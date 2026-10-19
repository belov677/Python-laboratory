"""Протоколы (интерфейсы) приложения."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class Reportable(Protocol):
    def get_report_data(self) -> str:
        ...


def print_report(items: list[Reportable]) -> None:
    """Работает с любыми объектами, у которых есть get_report_data()."""
    for item in items:
        print(" •", item.get_report_data())
