"""Лабораторная работа №4. Вариант 17 — «Музыкальная библиотека».

Точка входа: консольное меню. Данные хранятся в data/library.json,
журнал операций — в data/app.log.
"""
import logging
from pathlib import Path

from exceptions import MusicLibraryError
from models import format_duration, parse_duration
from services import MusicLibraryService
from storage import JsonRepository, export_csv, import_csv

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
logging.basicConfig(filename=DATA_DIR / "app.log", level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

MENU = """
===== Музыкальная библиотека =====
1. Добавить композицию      6. Создать плейлист
2. Показать каталог         7. Показать плейлисты
3. Найти композицию         8. Изменить / удалить композицию
4. Фильтрация               9. Статистика
5. Сохранить JSON          10. Экспорт CSV   11. Импорт CSV
0. Выход (с сохранением)"""


def read_int(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Ошибка: необходимо ввести целое число.")


def print_tracks(tracks):
    if not tracks:
        print("Ничего не найдено.")
    for track in tracks:
        print(track)


def handle(choice, service):
    if choice == "1":
        track = service.add_track(input("Название: "), input("Исполнитель: "),
                                  input("Жанр: "), input("Длительность (м:сс): "))
        print("Добавлено:", track)
    elif choice == "2":
        print_tracks(service.tracks)
    elif choice == "3":
        print_tracks(service.search(input("Часть названия или исполнителя: ")))
    elif choice == "4":
        genre = input("Жанр (пусто — любой): ").strip()
        limit = input("Максимальная длительность м:сс (пусто — без ограничения): ").strip()
        print_tracks(service.filter(genre or None, parse_duration(limit) if limit else None))
    elif choice == "5":
        service.save()
        print("Каталог сохранён в", service.repository.path.name)
    elif choice == "6":
        name = input("Название плейлиста: ")
        ids = [int(x) for x in input("id композиций через пробел: ").split()]
        playlist = service.create_playlist(name, ids)
        print(f"Плейлист «{playlist.name}» создан, композиций: {len(playlist.track_ids)}")
    elif choice == "7":
        for playlist in service.playlists:
            tracks = service.playlist_tracks(playlist)
            total = format_duration(sum(t.duration for t in tracks))
            print(f"Плейлист «{playlist.name}» — {len(tracks)} шт., {total}")
            for t in tracks:
                print("   ", t)
    elif choice == "8":
        track_id = read_int("id композиции: ")
        action = input("1 — изменить, 2 — удалить: ").strip()
        if action == "1":
            track = service.update_track(track_id, genre=input("Новый жанр (пусто — без изменений): "),
                                         duration=input("Новая длительность (пусто — без изменений): "))
            print("Изменено:", track)
        elif action == "2":
            print("Удалено:", service.delete_track(track_id))
    elif choice == "9":
        for key, value in service.statistics().items():
            print(f"{key}: {value}")
    elif choice == "10":
        export_csv(service.tracks, DATA_DIR / "library.csv")
        print("Экспортировано в data/library.csv")
    elif choice == "11":
        added = service.import_tracks(import_csv(input("Путь к CSV: ")))
        print("Импортировано новых композиций:", added)
    else:
        print("Ошибка: неизвестный пункт меню.")


def main():
    data_file = DATA_DIR / "library.json"
    try:
        service = MusicLibraryService(JsonRepository(data_file))
    except MusicLibraryError as error:
        print("Ошибка загрузки:", error)
        corrupted = data_file.with_suffix(".corrupted.json")
        data_file.replace(corrupted)
        print(f"Повреждённый файл сохранён как {corrupted.name}")
        backup = data_file.with_suffix(".bak.json")
        try:
            tracks, playlists = JsonRepository(backup).load()
        except MusicLibraryError:
            tracks, playlists = [], []
        print(f"Восстановлено из резервной копии: {len(tracks)} композиций")
        repository = JsonRepository(data_file)
        repository.save(tracks, playlists)
        service = MusicLibraryService(repository)
    print(f"Загружено композиций: {len(service.tracks)}, плейлистов: {len(service.playlists)}")
    while True:
        print(MENU)
        choice = input("Выберите пункт: ").strip()
        if choice == "0":
            service.save()
            print("Данные сохранены. До свидания!")
            break
        try:
            handle(choice, service)
        except MusicLibraryError as error:
            print(f"Ошибка ({type(error).__name__}): {error}")
        except ValueError as error:
            print("Ошибка ввода:", error)


if __name__ == "__main__":
    main()
