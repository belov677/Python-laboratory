"""Начальные данные для демонстрации."""
from services.services import ShipmentService

CLIENTS = [("ООО «ТехноМир»", "orders@technomir.ru", "Москва", "+7 495 100-10-10"),
           ("ИП Смирнова А.В.", "smirnova@mail.ru", "Казань", "+7 843 200-20-20"),
           ("АО «СтройДеталь»", "logistic@stroydetal.ru", "Екатеринбург", ""),
           ("ООО «Фермер»", "farm@fermer.ru", "Краснодар", "+7 861 300-30-30")]
SHIPMENTS = [
    (1, "Москва", "Санкт-Петербург", 710, [("Ноутбуки, 10 шт.", 25, "хрупкий"),
                                            ("Мониторы, 4 шт.", 28, "хрупкий")]),
    (3, "Екатеринбург", "Пермь", 360, [("Арматура 12 мм", 800, "обычный")]),
    (4, "Краснодар", "Москва", 1350, [("Овощи, 30 ящиков", 450, "обычный")]),
    (1, "Москва", "Казань", 820, [("Офисные кресла", 60, "обычный"), ("Краска", 120, "опасный")]),
    (2, "Казань", "Самара", 360, [("Посуда", 18, "хрупкий")]),
    (2, "Казань", "Нижний Новгород", 390, [("Книги, 6 коробок", 90, "обычный")]),
    (3, "Екатеринбург", "Челябинск", 210, [("Трубы стальные", 1500, "обычный")]),
]


def seed(service: ShipmentService) -> None:
    for name, email, city, phone in CLIENTS:
        service.create_client({"name": name, "email": email, "city": city, "phone": phone})
    for client_id, origin, dest, km, cargos in SHIPMENTS:
        service.create({"client_id": client_id, "origin": origin, "destination": dest,
                        "distance_km": km,
                        "cargos": [{"description": d, "weight_kg": w, "cargo_type": t}
                                   for d, w, t in cargos]})
    service.change_status(1, "IN_TRANSIT", "Тверь")
    service.change_status(1, "DELIVERED", "Санкт-Петербург")
    service.change_status(2, "IN_TRANSIT", "Кунгур")
    service.change_status(3, "CANCELLED", "Краснодар")
    service.change_status(7, "IN_TRANSIT", "Екатеринбург")
