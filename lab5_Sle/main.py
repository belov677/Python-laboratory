"""Лабораторная работа №5. Вариант 17 — «Музыкальные композиции».

Демонстрация функциональных возможностей Python: map, filter, reduce,
sorted с ключом, lambda, comprehensions, any/all, генераторы и итераторы.
"""
import sys

from generators import CompositionIterator, compositions_by_genre, playlist_until
from models import Composition, LiveTrack, load_compositions
from operations import (all_rated_above, average, filter_objects, has_artist,
                        make_rating_filter, process, sort_objects, total_duration,
                        transform_objects)


def mmss(seconds):
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def section(title):
    print(f"\n===== {title} =====")


def main():
    compositions = load_compositions()

    section("1. Все композиции (полиморфный __str__)")
    for c in compositions:
        print(c)

    section("2. filter(): рейтинг не ниже 9.0")
    for c in filter_objects(compositions, make_rating_filter(9.0)):
        print(f"{c.rating:4}  {c.title}")

    section("3. map(): получение названий")
    titles = list(transform_objects(compositions, lambda c: c.title))
    print(titles)

    section("4. sorted(key=...): по длительности")
    for c in sort_objects(compositions, key_function=lambda c: c.play_time()):
        print(f"{mmss(c.play_time()):>5}  {c.title}")

    section("5. Средняя и суммарная длительность (average + reduce)")
    print("Средняя длительность:", mmss(average(compositions, key=lambda c: c.play_time())))
    print("Суммарная длительность (reduce):", mmss(total_duration(compositions)))

    section("6. any() / all(): проверка наличия исполнителя")
    for artist in ("Queen", "Beatles"):
        print(f"Есть композиции исполнителя {artist}: {has_artist(compositions, artist)}")
    print("Все композиции с рейтингом ≥ 6:", all_rated_above(compositions, 6))
    print("Все композиции с рейтингом ≥ 8:", all_rated_above(compositions, 8))

    section("7. Comprehensions")
    genres = {c.genre for c in compositions}
    by_genre = {g: [c.title for c in compositions if c.genre == g] for g in sorted(genres)}
    live = [c.title for c in compositions if isinstance(c, LiveTrack)]
    print("Жанры (set):", sorted(genres))
    print("Концертные (list):", live)
    for genre, items in by_genre.items():
        print(f"  {genre:7}: {items}")

    section("8. Генератор композиций выбранного жанра и next()")
    jazz = compositions_by_genre(compositions, "jazz")
    print("Объект генератора:", type(jazz).__name__)
    print("next() →", next(jazz).title)
    print("next() →", next(jazz).title)
    print("next() →", next(jazz).title)
    try:
        next(jazz)
    except StopIteration:
        print("next() → StopIteration: элементы закончились")

    section("9. Генератор плейлиста длительностью до 20 минут")
    best_first = sorted(compositions, key=lambda c: c.rating, reverse=True)
    playlist = list(playlist_until(best_first, 20 * 60))
    for c in playlist:
        print(f"  {mmss(c.play_time())}  {c.title}")
    print("Итого:", mmss(sum(c.play_time() for c in playlist)))

    section("10. Собственный итератор (по убыванию рейтинга)")
    iterator = CompositionIterator(compositions)
    print("iter(iterator) is iterator:", iter(iterator) is iterator)
    for _ in range(3):
        c = next(iterator)
        print(f"  ★{c.rating}  {c.title}")
    print("Остальные:", [c.title for c in iterator])

    section("11. Ленивость: список и генератор")
    list_result = [x * x for x in range(1_000_000)]
    generator_result = (x * x for x in range(1_000_000))
    print(f"Список из 1 000 000 элементов: {sys.getsizeof(list_result):>10,} байт")
    print(f"Генератор того же выражения:   {sys.getsizeof(generator_result):>10,} байт")
    print("Первые значения генератора:", [next(generator_result) for _ in range(5)])
    del list_result

    section("12. Конвейер process(predicate, transform, key)")
    print("а) рок, отсортированный по рейтингу, в виде строки:")
    for line in process(compositions, lambda c: c.genre == "rock",
                        lambda c: f"{c.rating} {c.artist} — {c.title}",
                        key_function=lambda c: c.rating, reverse=True):
        print("  ", line)
    print("б) короче 5 минут, по длительности, только название и время:")
    for line in process(compositions, lambda c: c.play_time() < 300,
                        lambda c: (c.title, mmss(c.play_time())),
                        key_function=lambda c: c.play_time()):
        print("  ", line)

    section("13. Обработка некорректных данных")
    for args in (("Тишина", "Тест", "ambient", 0, 5), ("Шум", "Тест", "noise", 120, 15)):
        try:
            Composition(*args)
        except ValueError as error:
            print("ValueError:", error)
    try:
        average([])
    except ValueError as error:
        print("ValueError:", error)


if __name__ == "__main__":
    main()
