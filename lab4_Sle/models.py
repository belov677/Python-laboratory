"""Классы предметной области: композиция и плейлист."""
from exceptions import InvalidDurationError, PlaylistError


def parse_duration(text):
    """Преобразует строку «м:сс» или число секунд в секунды."""
    text = str(text).strip()
    try:
        if ":" in text:
            minutes, seconds = text.split(":")
            minutes, seconds = int(minutes), int(seconds)
            if not 0 <= seconds < 60:
                raise InvalidDurationError("Секунды должны быть в диапазоне 0–59")
            total = minutes * 60 + seconds
        else:
            total = int(text)
    except ValueError:
        raise InvalidDurationError(f"Некорректная продолжительность: «{text}»") from None
    return total


def format_duration(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


class Track:
    MAX_DURATION = 60 * 60  # не более часа

    def __init__(self, title, artist, genre, duration, track_id=None):
        if not title.strip() or not artist.strip():
            raise ValueError("Название и исполнитель не могут быть пустыми")
        self.id = track_id
        self.title = title.strip()
        self.artist = artist.strip()
        self.genre = genre.strip().lower()
        self.duration = duration

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, value):
        if not isinstance(value, int):
            value = parse_duration(value)
        if not 1 <= value <= self.MAX_DURATION:
            raise InvalidDurationError("Продолжительность должна быть от 1 секунды до 60 минут")
        self._duration = value

    def to_dict(self):
        return {"id": self.id, "title": self.title, "artist": self.artist,
                "genre": self.genre, "duration": self.duration}

    @classmethod
    def from_dict(cls, data):
        return cls(data["title"], data["artist"], data["genre"], int(data["duration"]),
                   track_id=int(data["id"]))

    def __str__(self):
        return (f"[{self.id:>3}] {self.artist} — {self.title} "
                f"({self.genre}, {format_duration(self.duration)})")


class Playlist:
    """Плейлист хранит идентификаторы композиций каталога."""

    def __init__(self, name, track_ids=None):
        if not name.strip():
            raise PlaylistError("Название плейлиста не может быть пустым")
        self.name = name.strip()
        self.track_ids = list(track_ids or [])

    def add(self, track_id):
        if track_id in self.track_ids:
            raise PlaylistError(f"Композиция {track_id} уже есть в плейлисте «{self.name}»")
        self.track_ids.append(track_id)

    def to_dict(self):
        return {"name": self.name, "track_ids": self.track_ids}

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], [int(i) for i in data["track_ids"]])
