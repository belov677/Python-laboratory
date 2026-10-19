"""Пользовательские исключения музыкальной библиотеки."""


class MusicLibraryError(Exception):
    """Базовое исключение приложения."""


class TrackNotFoundError(MusicLibraryError):
    """Композиция не найдена."""


class DuplicateTrackError(MusicLibraryError):
    """Композиция уже есть в каталоге."""


class InvalidDurationError(MusicLibraryError):
    """Некорректная продолжительность композиции."""


class PlaylistError(MusicLibraryError):
    """Ошибка работы с плейлистом."""


class StorageError(MusicLibraryError):
    """Ошибка чтения или записи файла данных."""
