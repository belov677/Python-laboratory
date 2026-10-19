"""Консольный интерфейс: ввод подменяется patch(), вывод перехватывается capsys."""
from unittest.mock import patch

from src import main as cli


def run_cli(capsys, answers):
    with patch("builtins.input", side_effect=answers), patch("sys.argv", ["main"]):
        cli.main()
    return capsys.readouterr().out


def test_cli_receive_and_balance(capsys):
    out = run_cli(capsys, ["1", "2", "1", "5", "4", "2", "0"])
    assert "остаток на складе: 15" in out             # 10 + 5
    assert "EL-1002" in out and "всего 15" in out


def test_cli_reports_errors_instead_of_crashing(capsys):
    out = run_cli(capsys, ["2", "1", "2", "100", "1", "abc", "3", "1", "1", "1", "1", "7", "0"])
    assert "InsufficientStockError" in out            # списание больше остатка
    assert "Ожидалось целое число" in out
    assert "должны различаться" in out
    assert "Неизвестный пункт" in out


def test_cli_search_transfer_history(capsys):
    out = run_cli(capsys, ["5", "ноут", "3", "1", "1", "2", "2", "6", "1", "0"])
    assert "EL-1001 Ноутбук Lenovo" in out
    assert "источник 4, получатель 5" in out
    assert "transfer" in out
