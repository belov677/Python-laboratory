"""Бизнес-логика музыкальной библиотеки."""
import logging

from exceptions import DuplicateTrackError, PlaylistError, TrackNotFoundError
from models import Playlist, Track, format_duration

logger = logging.getLogger("music.service")


class MusicLibraryService:
    def __init__(self, repository):
        self.repository = repository
        self.tracks, self.playlists = repository.load()

    def _next_id(self):
        return max((t.id for t in self.tracks), default=0) + 1

    # --- каталог ---
    def add_track(self, title, artist, genre, duration):
        track = Track(title, artist, genre, duration)
        for existing in self.tracks:
            if (existing.title.lower(), existing.artist.lower()) == (track.title.lower(),
                                                                     track.artist.lower()):
                raise DuplicateTrackError(f"«{track.title}» ({track.artist}) уже есть в каталоге")
        track.id = self._next_id()
        self.tracks.append(track)
        logger.info("Добавлена композиция %s", track)
        return track

    def get_track(self, track_id):
        for track in self.tracks:
            if track.id == track_id:
                return track
        raise TrackNotFoundError(f"Композиция с id={track_id} не найдена")

    def update_track(self, track_id, **fields):
        track = self.get_track(track_id)
        for name, value in fields.items():
            if value not in (None, ""):
                setattr(track, name, value)
        logger.info("Изменена композиция %s", track)
        return track

    def delete_track(self, track_id):
        track = self.get_track(track_id)
        self.tracks.remove(track)
        for playlist in self.playlists:
            if track_id in playlist.track_ids:
                playlist.track_ids.remove(track_id)
        logger.info("Удалена композиция %s", track)
        return track

    def search(self, text):
        text = text.lower()
        return [t for t in self.tracks if text in t.title.lower() or text in t.artist.lower()]

    def filter(self, genre=None, max_duration=None):
        result = self.tracks
        if genre:
            result = [t for t in result if t.genre == genre.lower()]
        if max_duration:
            result = [t for t in result if t.duration <= max_duration]
        return result

    def statistics(self):
        if not self.tracks:
            return {}
        total = sum(t.duration for t in self.tracks)
        genres = {}
        for t in self.tracks:
            genres[t.genre] = genres.get(t.genre, 0) + 1
        return {"композиций": len(self.tracks),
                "исполнителей": len({t.artist for t in self.tracks}),
                "общая длительность": format_duration(total),
                "средняя длительность": format_duration(total // len(self.tracks)),
                "жанры": genres}

    # --- плейлисты ---
    def create_playlist(self, name, track_ids):
        if any(p.name.lower() == name.lower() for p in self.playlists):
            raise PlaylistError(f"Плейлист «{name}» уже существует")
        playlist = Playlist(name)
        for track_id in track_ids:
            self.get_track(track_id)          # проверка существования
            playlist.add(track_id)
        self.playlists.append(playlist)
        logger.info("Создан плейлист %s (%d композиций)", name, len(track_ids))
        return playlist

    def playlist_tracks(self, playlist):
        return [self.get_track(i) for i in playlist.track_ids]

    def save(self):
        self.repository.save(self.tracks, self.playlists)

    def import_tracks(self, tracks):
        added = 0
        for track in tracks:
            try:
                self.add_track(track.title, track.artist, track.genre, track.duration)
                added += 1
            except DuplicateTrackError:
                continue
        return added
