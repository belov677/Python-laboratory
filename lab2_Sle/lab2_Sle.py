# Лабораторная работа №2. Вариант 17 — «Посетители мероприятия».
# Для каждого посетителя хранятся: имя, возраст, город, категория билета.

TICKET_CATEGORIES = ("standard", "vip", "student", "child")

DEMO_VISITORS = [
    {"name": "Иван Петров", "age": 34, "city": "Москва", "ticket": "vip"},
    {"name": "Анна Смирнова", "age": 19, "city": "Казань", "ticket": "student"},
    {"name": "Пётр Иванов", "age": 45, "city": "Москва", "ticket": "standard"},
    {"name": "Мария Кузнецова", "age": 27, "city": "Самара", "ticket": "standard"},
    {"name": "Олег Соколов", "age": 12, "city": "Казань", "ticket": "child"},
    {"name": "Елена Попова", "age": 27, "city": "Москва", "ticket": "vip"},
]


# ---------- ввод ----------
def read_int(prompt, minimum, maximum):
    while True:
        text = input(prompt).strip()
        if not text.isdigit():
            print("Ошибка: введите целое неотрицательное число.")
            continue
        value = int(text)
        if minimum <= value <= maximum:
            return value
        print(f"Ошибка: значение должно быть от {minimum} до {maximum}.")


def read_text(prompt):
    while True:
        text = input(prompt).strip()
        if text:
            return text
        print("Ошибка: строка не может быть пустой.")


def read_visitor():
    name = read_text("Имя: ")
    age = read_int("Возраст: ", 0, 120)
    city = read_text("Город: ").title()
    print("Категории билета:", ", ".join(TICKET_CATEGORIES))
    while True:
        ticket = input("Категория билета: ").strip().lower()
        if ticket in TICKET_CATEGORIES:
            break
        print("Ошибка: неизвестная категория.")
    return {"name": name, "age": age, "city": city, "ticket": ticket}


# ---------- обработка ----------
def find_by_city(visitors, city):
    return [v for v in visitors if v["city"].lower() == city.lower()]


def filter_by_age(visitors, min_age, max_age):
    return [v for v in visitors if min_age <= v["age"] <= max_age]


def filter_by_age_and_ticket(visitors, min_age, max_age, ticket):
    """Фильтрация по нескольким критериям."""
    return [v for v in filter_by_age(visitors, min_age, max_age) if v["ticket"] == ticket]


def sort_by_age(visitors, reverse=False):
    return sorted(visitors, key=lambda v: v["age"], reverse=reverse)


def sort_by_city_and_age(visitors):
    """Сортировка по двум параметрам: город, затем возраст."""
    return sorted(visitors, key=lambda v: (v["city"], v["age"]))


def calculate_average_age(visitors):
    total = 0
    for v in visitors:
        total += v["age"]
    return total / len(visitors)


def find_youngest_and_oldest(visitors):
    youngest = oldest = visitors[0]
    for v in visitors:
        if v["age"] < youngest["age"]:
            youngest = v
        if v["age"] > oldest["age"]:
            oldest = v
    return youngest, oldest


def count_by_ticket(visitors):
    counts = {}
    for v in visitors:
        counts[v["ticket"]] = counts.get(v["ticket"], 0) + 1
    return counts


def unique_cities(visitors):
    return {v["city"] for v in visitors}


def group_by_city(visitors):
    groups = {}
    for v in visitors:
        groups.setdefault(v["city"], []).append(v["name"])
    return groups


# ---------- вывод ----------
def print_visitors(visitors, title="Посетители"):
    print(f"\n--- {title} ({len(visitors)}) ---")
    if not visitors:
        print("Нет подходящих посетителей.")
        return
    print(f"{'№':>2}  {'Имя':18} {'Возраст':>7}  {'Город':10} Билет")
    for i, v in enumerate(visitors, start=1):
        print(f"{i:>2}  {v['name']:18} {v['age']:>7}  {v['city']:10} {v['ticket']}")


def print_statistics(visitors):
    if not visitors:
        print("Нет данных для статистики.")
        return
    youngest, oldest = find_youngest_and_oldest(visitors)
    ages = [v["age"] for v in visitors]
    adults = [v for v in visitors if v["age"] >= 18]
    print("\n--- Статистика ---")
    print(f"Количество посетителей: {len(visitors)}")
    print(f"Средний возраст: {calculate_average_age(visitors):.1f}")
    print(f"Минимальный / максимальный возраст: {min(ages)} / {max(ages)}")
    print(f"Самый молодой: {youngest['name']} ({youngest['age']})")
    print(f"Самый взрослый: {oldest['name']} ({oldest['age']})")
    print(f"Совершеннолетних: {len(adults)} ({len(adults) / len(visitors) * 100:.0f}%)")
    print("По категориям билетов:")
    for ticket, count in sorted(count_by_ticket(visitors).items()):
        print(f"  {ticket:9} {count}")


def main():
    visitors = []
    while True:
        print("\n===== МЕНЮ =====")
        print("1. Добавить посетителя")
        print("2. Показать посетителей")
        print("3. Найти посетителей из города")
        print("4. Фильтрация по возрасту")
        print("5. Сортировка по возрасту")
        print("6. Статистика")
        print("7. Список городов (уникальные значения)")
        print("8. Удалить посетителя")
        print("9. Фильтр по возрасту и категории билета")
        print("10. Группировка по городам")
        print("11. Загрузить демонстрационные данные")
        print("0. Выход")
        choice = input("Выберите пункт: ").strip()

        if choice == "1":
            visitors.append(read_visitor())
            print("Посетитель добавлен.")
        elif choice == "2":
            print_visitors(visitors)
        elif choice == "3":
            city = read_text("Город для поиска: ")
            print_visitors(find_by_city(visitors, city), f"Посетители из города {city}")
        elif choice == "4":
            low = read_int("Минимальный возраст: ", 0, 120)
            high = read_int("Максимальный возраст: ", low, 120)
            print_visitors(filter_by_age(visitors, low, high), f"Возраст {low}–{high}")
        elif choice == "5":
            order = input("По убыванию? (д/н): ").strip().lower() == "д"
            print_visitors(sort_by_age(visitors, order), "Сортировка по возрасту")
        elif choice == "6":
            print_statistics(visitors)
        elif choice == "7":
            cities = unique_cities(visitors)
            print(f"Уникальных городов: {len(cities)}: {', '.join(sorted(cities))}")
        elif choice == "8":
            print_visitors(visitors)
            if visitors:
                index = read_int("Номер посетителя для удаления: ", 1, len(visitors))
                removed = visitors.pop(index - 1)
                print(f"Удалён: {removed['name']}")
        elif choice == "9":
            low = read_int("Минимальный возраст: ", 0, 120)
            high = read_int("Максимальный возраст: ", low, 120)
            ticket = input("Категория билета: ").strip().lower()
            print_visitors(filter_by_age_and_ticket(visitors, low, high, ticket),
                           f"Возраст {low}–{high}, билет {ticket}")
        elif choice == "10":
            for city, names in sorted(group_by_city(visitors).items()):
                print(f"{city}: {', '.join(names)}")
        elif choice == "11":
            visitors.extend(dict(v) for v in DEMO_VISITORS)
            print(f"Загружено {len(DEMO_VISITORS)} посетителей.")
        elif choice == "0":
            print("До свидания!")
            break
        else:
            print("Ошибка: неизвестный пункт меню.")


if __name__ == "__main__":
    main()
