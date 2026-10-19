"""Unit: пароли, JWT и валидация входных данных (параметризованные тесты)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.core.exceptions import UnauthorizedError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.schemas.dto import DriverIn, OrderIn, RegisterIn, VehicleIn

SECRET = "unit-test-secret-0123456789abcdef0123456789"


def test_password_hash_is_salted_and_verifiable():
    first, second = hash_password("Secret2026"), hash_password("Secret2026")
    assert first != second and first.startswith("pbkdf2_sha256$")  # соль у каждого хеша своя
    assert verify_password("Secret2026", first) and not verify_password("secret2026", first)
    assert not verify_password("Secret2026", "повреждённый-хеш")


def test_token_roundtrip_and_tampering():
    token = create_token(7, "ADMIN", SECRET, 5)
    payload = decode_token(token, SECRET)
    assert (payload["sub"], payload["role"]) == ("7", "ADMIN")
    with pytest.raises(UnauthorizedError, match="Недействительный"):
        decode_token(token, "другой-секрет-0123456789abcdef0123456789")


def test_expired_token():
    expired = jwt.encode(
        {"sub": "1", "role": "USER", "exp": datetime.now(UTC) - timedelta(minutes=1)}, SECRET, algorithm="HS256"
    )
    with pytest.raises(UnauthorizedError) as info:
        decode_token(expired, SECRET)
    assert info.value.code == "TOKEN_EXPIRED"


@pytest.mark.parametrize(
    "password, ok", [("Client2026", True), ("short1", False), ("onlyletters", False), ("1234567890", False)]
)
def test_password_policy(password, ok):
    data = {"email": "a@b.ru", "password": password, "full_name": "Тест Тестов"}
    if ok:
        RegisterIn(**data)
    else:
        with pytest.raises(ValidationError):
            RegisterIn(**data)


PICKUP = datetime(2030, 1, 10, 9, tzinfo=UTC)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"deadline_at": PICKUP}, "срок доставки"),  # срок не позже подачи
        ({"destination": "москва"}, "различаться"),  # тот же город
        ({"weight_kg": 0}, "greater than 0"),  # граница веса
        ({"weight_kg": 40001}, "less than or equal"),
        ({"pickup_at": datetime(2030, 1, 10, 9)}, "часовым поясом"),  # без часового пояса
    ],
)
def test_order_validation(changes, message):
    data = {
        "origin": "Москва",
        "destination": "Казань",
        "cargo": "Мебель",
        "weight_kg": 100,
        "pickup_at": PICKUP,
        "deadline_at": PICKUP + timedelta(days=1),
        **changes,
    }
    with pytest.raises(ValidationError, match=message):
        OrderIn(**data)


@pytest.mark.parametrize(
    "category, capacity, ok",
    [("B", 3500, True), ("B", 3501, False), ("C", 20000, True), ("CE", 40000, True), ("C", 25000, False)],
)
def test_vehicle_capacity_matches_category(category, capacity, ok):
    data = {"plate": "А123ВС77", "model": "Тест", "category": category, "capacity_kg": capacity}
    if ok:
        assert VehicleIn(**data).capacity_kg == capacity
    else:
        with pytest.raises(ValidationError, match="грузоподъёмность"):
            VehicleIn(**data)


@pytest.mark.parametrize(
    "field, value",
    [
        ("license_number", "7701100001"),
        ("phone", "89161234567"),
        ("license_categories", []),
        ("license_categories", ["D"]),
    ],
)
def test_driver_validation(field, value):
    data = {
        "full_name": "Иванов Иван",
        "license_number": "77 01 100001",
        "license_categories": ["B"],
        "phone": "+79161234567",
        field: value,
    }
    with pytest.raises(ValidationError):
        DriverIn(**data)
