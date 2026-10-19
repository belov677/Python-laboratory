"""Модели: музыкальные композиции."""


class Composition:
    """Базовый класс музыкальной композиции."""

    def __init__(self, title, artist, genre, duration, rating):
        if duration <= 0:
            raise ValueError(f"Длительность «{title}» должна быть положительной")
        if not 0 <= rating <= 10:
            raise ValueError(f"Рейтинг «{title}» должен быть от 0 до 10")
        self.title = title
        self.artist = artist
        self.genre = genre
        self.duration = duration      # секунды
        self.rating = rating

    def kind(self):
        return "композиция"

    def play_time(self):
        """Время звучания при воспроизведении."""
        return self.duration

    def __str__(self):
        m, s = divmod(self.play_time(), 60)
        return (f"{self.artist} — {self.title} [{self.genre}, {m}:{s:02d}, "
                f"★{self.rating}] ({self.kind()})")


class StudioTrack(Composition):
    """Студийная запись — входит в альбом."""

    def __init__(self, title, artist, genre, duration, rating, album):
        super().__init__(title, artist, genre, duration, rating)
        self.album = album

    def kind(self):
        return f"студийная, альбом «{self.album}»"


class LiveTrack(Composition):
    """Концертная запись — добавляется время на аплодисменты."""

    APPLAUSE = 20

    def __init__(self, title, artist, genre, duration, rating, venue):
        super().__init__(title, artist, genre, duration, rating)
        self.venue = venue

    def kind(self):
        return f"концертная, {self.venue}"

    def play_time(self):
        return self.duration + self.APPLAUSE


def load_compositions():
    return [
        StudioTrack("Bohemian Rhapsody", "Queen", "rock", 355, 9.8, "A Night at the Opera"),
        StudioTrack("So What", "Miles Davis", "jazz", 562, 9.5, "Kind of Blue"),
        LiveTrack("Hotel California", "Eagles", "rock", 412, 9.1, "Hell Freezes Over"),
        StudioTrack("Группа крови", "Кино", "rock", 286, 9.0, "Группа крови"),
        StudioTrack("Take Five", "Dave Brubeck", "jazz", 324, 8.7, "Time Out"),
        LiveTrack("Nothing Else Matters", "Metallica", "metal", 388, 8.9, "S&M"),
        StudioTrack("Shape of You", "Ed Sheeran", "pop", 233, 6.4, "÷"),
        StudioTrack("Billie Jean", "Michael Jackson", "pop", 294, 8.8, "Thriller"),
        LiveTrack("Feeling Good", "Nina Simone", "jazz", 175, 7.9, "Montreux"),
        StudioTrack("Smells Like Teen Spirit", "Nirvana", "grunge", 301, 9.2, "Nevermind"),
    ]
