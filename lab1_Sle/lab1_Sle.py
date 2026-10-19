# Лабораторная работа №1. Вариант 17 — «Посещаемость занятий».
# Программа анализирует посещаемость учебной группы: для каждого занятия
# вводится количество присутствующих студентов.

import random

LOW_ATTENDANCE_PERCENT = 60
HIGH_ATTENDANCE_PERCENT = 90


def read_int(prompt, minimum, maximum=None):
    """Запрашивает целое число, пока пользователь не введёт корректное значение."""
    while True:
        text = input(prompt).strip()
        if not text.lstrip("-").isdigit():
            print("Ошибка: необходимо ввести целое число.")
            continue
        value = int(text)
        if value < minimum:
            print(f"Ошибка: значение не может быть меньше {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Ошибка: значение не может быть больше {maximum}.")
            continue
        return value


def input_attendance(group_size):
    """Ввод посещаемости вручную или генератором случайных чисел."""
    lessons_count = read_int("Введите количество занятий: ", 1)
    mode = input("Заполнить случайно? (д/н): ").strip().lower()
    attendance = []
    if mode == "д":
        for _ in range(lessons_count):
            attendance.append(random.randint(group_size // 3, group_size))
        print("Сгенерированы значения:", attendance)
    else:
        for i in range(lessons_count):
            present = read_int(f"Присутствовало на занятии {i + 1}: ", 0, group_size)
            attendance.append(present)
    return attendance


def calculate_average(values):
    total = 0
    for value in values:
        total += value
    return total / len(values)


def find_min_max(values):
    minimum = values[0]
    maximum = values[0]
    for value in values:
        if value < minimum:
            minimum = value
        if value > maximum:
            maximum = value
    return minimum, maximum


def calculate_percent(present, group_size):
    return present / group_size * 100


def count_lessons_by_percent(values, group_size):
    """Возвращает количество занятий с посещаемостью < 60% и > 90%."""
    low = 0
    high = 0
    for present in values:
        percent = calculate_percent(present, group_size)
        if percent < LOW_ATTENDANCE_PERCENT:
            low += 1
        elif percent > HIGH_ATTENDANCE_PERCENT:
            high += 1
    return low, high


def longest_full_attendance_series(values, group_size, threshold=HIGH_ATTENDANCE_PERCENT):
    """Наибольшее число подряд идущих занятий с посещаемостью выше порога."""
    best = 0
    current = 0
    for present in values:
        if calculate_percent(present, group_size) > threshold:
            current += 1
            if current > best:
                best = current
        else:
            current = 0
    return best


def describe_group(average_percent):
    if average_percent >= 90:
        return "отличная посещаемость"
    elif average_percent >= 75:
        return "хорошая посещаемость"
    elif average_percent >= 60:
        return "удовлетворительная посещаемость"
    return "низкая посещаемость — требуется работа с группой"


def show_statistics(group_size, attendance):
    average = calculate_average(attendance)
    minimum, maximum = find_min_max(attendance)
    average_percent = calculate_percent(average, group_size)
    low, high = count_lessons_by_percent(attendance, group_size)

    print("\n===== Результаты анализа =====")
    print(f"Студентов в группе:            {group_size}")
    print(f"Проведено занятий:             {len(attendance)}")
    print(f"Средняя посещаемость:          {average:.2f} чел.")
    print(f"Максимальная посещаемость:     {maximum} чел.")
    print(f"Минимальная посещаемость:      {minimum} чел.")
    print(f"Средний процент присутствующих: {average_percent:.1f}%")
    print(f"Занятий с посещаемостью < {LOW_ATTENDANCE_PERCENT}%: {low}")
    print(f"Занятий с посещаемостью > {HIGH_ATTENDANCE_PERCENT}%: {high}")
    print(f"Характеристика группы: {describe_group(average_percent)}")


def show_additional_analysis(group_size, attendance):
    print("\n===== Дополнительный анализ =====")
    for number, present in enumerate(attendance, start=1):
        percent = calculate_percent(present, group_size)
        bar = "#" * round(percent / 5)
        print(f"Занятие {number:2}: {present:3} чел. {percent:5.1f}% {bar}")
    absent_total = group_size * len(attendance) - sum(attendance)
    series = longest_full_attendance_series(attendance, group_size)
    print(f"Всего пропусков (студенто-занятий): {absent_total}")
    print(f"Самая длинная серия занятий с посещаемостью > 90%: {series}")


def main():
    groups = {}
    current_group = None
    while True:
        print("\n===== Анализ посещаемости =====")
        print("1. Ввести данные группы")
        print("2. Показать статистику")
        print("3. Выполнить дополнительный анализ")
        print("4. Сравнить группы")
        print("5. Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            name = input("Название группы: ").strip() or f"Группа {len(groups) + 1}"
            group_size = read_int("Количество студентов в группе: ", 1)
            groups[name] = (group_size, input_attendance(group_size))
            current_group = name
            print(f"Данные группы «{name}» сохранены.")
        elif choice in ("2", "3"):
            if current_group is None:
                print("Сначала введите данные (пункт 1).")
                continue
            group_size, attendance = groups[current_group]
            print(f"Группа: {current_group}")
            if choice == "2":
                show_statistics(group_size, attendance)
            else:
                show_additional_analysis(group_size, attendance)
        elif choice == "4":
            if len(groups) < 2:
                print("Для сравнения нужно минимум две группы.")
                continue
            print("\n===== Сравнение групп =====")
            best_name = None
            best_percent = -1
            for name, (group_size, attendance) in groups.items():
                percent = calculate_percent(calculate_average(attendance), group_size)
                print(f"{name:15} {percent:5.1f}%")
                if percent > best_percent:
                    best_percent = percent
                    best_name = name
            print(f"Лучшая посещаемость у группы «{best_name}».")
        elif choice == "5":
            print("Работа программы завершена.")
            break
        else:
            print("Ошибка: неизвестный пункт меню.")


if __name__ == "__main__":
    main()
