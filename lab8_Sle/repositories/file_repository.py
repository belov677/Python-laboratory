from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from factories.entity_factory import EntityFactory
from repositories.memory_repository import InMemoryRepository


def _encode(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.name
    raise TypeError(type(value))


class FileRepository(InMemoryRepository):
    """Хранение в JSON-файле. Для восстановления объектов используется фабрика."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            for item in json.loads(self.path.read_text(encoding="utf-8")):
                kind = item.pop("kind")
                super().add(EntityFactory.create(kind, **item))

    def add(self, entity: Any) -> Any:
        super().add(entity)
        self.save()
        return entity

    def delete(self, entity_id: int) -> None:
        super().delete(entity_id)
        self.save()

    def save(self) -> None:
        data = [{"kind": EntityFactory.kind_of(e), **asdict(e)} for e in self.get_all()]
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=_encode),
                             encoding="utf-8")
