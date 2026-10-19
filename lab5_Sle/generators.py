"""Генераторы и собственный итератор."""


def compositions_by_genre(compositions, genre):
    """Генератор композиций выбранного жанра."""
    for composition in compositions:
        if composition.genre == genre:
            yield composition


def playlist_until(compositions, limit_seconds):
    """Генератор плейлиста: выдаёт композиции, пока не превышен лимит времени."""
    used = 0
    for composition in compositions:
        if used + composition.play_time() > limit_seconds:
            return
        used += composition.play_time()
        yield composition


class CompositionIterator:
    """Итератор, перебирающий композиции по убыванию рейтинга."""

    def __init__(self, compositions):
        self._items = sorted(compositions, key=lambda c: c.rating, reverse=True)
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._items):
            raise StopIteration
        item = self._items[self._index]
        self._index += 1
        return item
