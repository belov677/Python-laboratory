"""Хранение данных: JSON-репозиторий, экспорт и импорт CSV."""
import csv
import json
import logging
import shutil
from pathlib import Path

from exceptions import StorageError
from models import Playlist, Track

logger = logging.getLogger("music.storage")


class Repository:
    """Интерфейс хранилища."""

    def save(self, tracks, playlists):
        raise NotImplementedError

    def load(self):
        raise NotImplementedError


class JsonRepository(Repository):
    def __init__(self, path):
        self.path = Path(path)

    def save(self, tracks, playlists):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():                       # резервная копия перед записью
            shutil.copy(self.path, self.path.with_suffix(".bak.json"))
        data = {"tracks": [t.to_dict() for t in tracks],
                "playlists": [p.to_dict() for p in playlists]}
        try:
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except OSError as error:
            raise StorageError(f"Не удалось сохранить файл: {error}") from error
        logger.info("Сохранено %d композиций в %s", len(tracks), self.path)

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)
            tracks = [Track.from_dict(item) for item in data.get("tracks", [])]
            playlists = [Playlist.from_dict(item) for item in data.get("playlists", [])]
        except FileNotFoundError:
            logger.info("Файл %s не найден — начинаем с пустого каталога", self.path)
            return [], []
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
            raise StorageError(f"Файл {self.path} содержит некорректные данные: {error}") from error
        logger.info("Загружено %d композиций из %s", len(tracks), self.path)
        return tracks, playlists


FIELDS = ["id", "title", "artist", "genre", "duration"]


def export_csv(tracks, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for track in tracks:
            writer.writerow(track.to_dict())
    logger.info("Экспортировано %d строк в %s", len(tracks), path)


def import_csv(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
    except FileNotFoundError as error:
        raise StorageError(f"CSV-файл {path} не найден") from error
    result = []
    for row in rows:
        result.append(Track(row["title"], row["artist"], row["genre"], row["duration"]))
    return result
