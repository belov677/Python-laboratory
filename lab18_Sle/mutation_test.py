"""Простое мутационное тестирование сервисного слоя (дополнительное задание 4).

Скрипт по очереди вносит в src/services/inventory_service.py одну «ошибку» (мутант):
меняет операторы сравнения и арифметики, числовые константы, булевы условия — и запускает
unit- и интеграционные тесты. Если тесты упали — мутант «убит» (ошибка обнаружена), если
прошли — мутант «выжил»: такую ошибку текущий набор тестов не заметил бы.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).parent / "src" / "services" / "inventory_service.py"
SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Add: ast.Sub, ast.Sub: ast.Add,
        ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.And: ast.Or, ast.Or: ast.And}


class Collector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.points: list[tuple[str, int, int]] = []  # (вид, номер узла, строка)
        self.index = 0

    def generic_visit(self, node):
        self.index += 1
        if isinstance(node, ast.Compare) and type(node.ops[0]) in SWAP:
            self.points.append(("compare", self.index, node.lineno))
        elif isinstance(node, ast.BinOp) and type(node.op) in SWAP:
            self.points.append(("binop", self.index, node.lineno))
        elif isinstance(node, ast.BoolOp) and type(node.op) in SWAP:
            self.points.append(("boolop", self.index, node.lineno))
        elif isinstance(node, ast.Constant) and type(node.value) is int and node.value in (0, 1, 10_000):
            self.points.append(("const", self.index, node.lineno))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            self.points.append(("not", self.index, node.lineno))
        super().generic_visit(node)


class Mutator(ast.NodeTransformer):
    def __init__(self, target: int) -> None:
        self.target, self.index, self.description = target, 0, ""

    def generic_visit(self, node):
        self.index += 1
        if self.index == self.target:
            before = ast.unparse(node)
            if isinstance(node, ast.Compare):
                node.ops[0] = SWAP[type(node.ops[0])]()
            elif isinstance(node, ast.BinOp):
                node.op = SWAP[type(node.op)]()
            elif isinstance(node, ast.BoolOp):
                node.op = SWAP[type(node.op)]()
            elif isinstance(node, ast.Constant):
                node.value = node.value + 1
            elif isinstance(node, ast.UnaryOp):
                self.description = f"{before}  →  {ast.unparse(node.operand)}"
                return node.operand
            self.description = f"{before}  →  {ast.unparse(node)}"
        return super().generic_visit(node)


def main() -> int:
    original = TARGET.read_text(encoding="utf-8")
    collector = Collector()
    collector.visit(ast.parse(original))
    survived, killed = [], 0
    try:
        for number, (kind, index, line) in enumerate(collector.points, 1):
            mutator = Mutator(index)
            tree = mutator.visit(ast.parse(original))
            TARGET.write_text(ast.unparse(tree), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider",
                                     "tests/unit", "tests/integration"], capture_output=True)
            status = "убит " if result.returncode else "ВЫЖИЛ"
            if result.returncode:
                killed += 1
            else:
                survived.append((line, mutator.description))
            print(f"{number:3}. стр. {line:3} [{status}] {mutator.description[:90]}")
    finally:
        TARGET.write_text(original, encoding="utf-8")
    total = len(collector.points)
    print(f"\nМутантов: {total}, убито: {killed}, выжило: {len(survived)}, "
          f"mutation score: {killed / total:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
