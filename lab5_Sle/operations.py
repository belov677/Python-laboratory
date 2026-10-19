"""Функции обработки коллекций (функции высшего порядка)."""
from functools import reduce


def filter_objects(objects, predicate):
    """Функция высшего порядка: отбор объектов по переданному условию."""
    return filter(predicate, objects)


def transform_objects(objects, operation):
    """Функция высшего порядка: преобразование каждого объекта."""
    return map(operation, objects)


def sort_objects(objects, key_function, reverse=False):
    return sorted(objects, key=key_function, reverse=reverse)


def average(values, key=lambda x: x):
    values = list(values)
    if not values:
        raise ValueError("Нельзя вычислить среднее пустой коллекции")
    return sum(map(key, values)) / len(values)


def total_duration(compositions):
    """Суммарная длительность через reduce."""
    return reduce(lambda acc, c: acc + c.play_time(), compositions, 0)


def has_artist(compositions, artist):
    return any(c.artist.lower() == artist.lower() for c in compositions)


def all_rated_above(compositions, threshold):
    return all(c.rating >= threshold for c in compositions)


def make_rating_filter(min_rating):
    """Функция, возвращающая функцию (замыкание)."""
    return lambda composition: composition.rating >= min_rating


def process(objects, predicate, transform, key_function, reverse=False):
    """Конвейер: filter → map → sorted → генератор.

    filter и map ленивые, поэтому промежуточные списки не создаются;
    sorted вынужден собрать данные, а результат выдаётся генератором по одному.
    """
    selected = filter(predicate, objects)
    ordered = sorted(selected, key=key_function, reverse=reverse)
    for item in map(transform, ordered):
        yield item
