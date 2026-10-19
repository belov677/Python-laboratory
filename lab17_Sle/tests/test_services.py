"""Тесты бизнес-логики (без Telegram)."""
import pytest

from bot.services.exceptions import NotEnoughStockError, NotFoundError, ValidationError
from bot.services.validators import parse_price, parse_quantity, parse_sku

pytestmark = pytest.mark.asyncio


async def test_create_and_get_product(service):
    product = await service.create_product("Степлер №24", "of-5004", "340", 20, 3)
    loaded = await service.get_product(product.id)
    assert (loaded.sku, loaded.price, loaded.supplier.name) == ("OF-5004", 340.0, "ООО «Офис-Плюс»")
    assert len(loaded.stocks) == 3 and loaded.total == 0 and loaded.is_critical


async def test_create_duplicate_sku(service):
    with pytest.raises(ValidationError, match="уже существует"):
        await service.create_product("Дубль", "EL-1001", "100", 1, 1)


async def test_update_product(service):
    product = await service.update_product(1, "price", "65 000,50")
    assert product.price == 65000.5
    with pytest.raises(ValidationError):
        await service.update_product(1, "min_stock", "-3")


async def test_delete_product(service):
    name = await service.delete_product(2)
    assert name.startswith("Монитор")
    with pytest.raises(NotFoundError):
        await service.get_product(2)


async def test_search(service):
    assert [p.sku for p in await service.search("монитор")] == ["EL-1002"]
    assert len(await service.search("Офис-Плюс")) == 3          # по поставщику
    assert {p.sku for p in await service.search("bd-30")} == {"BD-3001", "BD-3002", "BD-3003"}
    with pytest.raises(ValidationError):
        await service.search("x")


async def test_receive_increases_stock(service):
    result = await service.receive(4, 1, 50, user_id=1)
    assert (result.left, result.product.total, result.critical) == (58, 65, False)


async def test_write_off_and_critical_notification_flag(service):
    result = await service.write_off(3, 1, 20, user_id=1)      # клавиатуры: 55 → 35 < 30? нет
    assert result.left == 5 and result.product.total == 35 and not result.critical
    result = await service.write_off(3, 2, 10, user_id=1)      # 35 → 25 < 30 — стал критическим
    assert result.critical


async def test_write_off_cannot_go_negative(service):
    with pytest.raises(NotEnoughStockError, match="есть 3, требуется 4"):
        await service.write_off(1, 2, 4, user_id=1)
    assert (await service.get_product(1)).total == 7          # остаток не изменился


async def test_critical_list(service):
    assert {p.sku for p in await service.critical()} == {"EL-1004", "BD-3002", "OF-5003", "FD-2002"}


@pytest.mark.parametrize("text, error", [("abc", "целым числом"), ("0", "больше нуля"),
                                         ("-5", "больше нуля"), ("1000000", "Слишком большое")])
async def test_quantity_validation(text, error):
    with pytest.raises(ValidationError, match=error):
        parse_quantity(text)


async def test_other_validators():
    assert parse_quantity(" 15 ") == 15
    assert parse_sku("el-123") == "EL-123"
    with pytest.raises(ValidationError):
        parse_sku("123")
    with pytest.raises(ValidationError):
        parse_price("дорого")
