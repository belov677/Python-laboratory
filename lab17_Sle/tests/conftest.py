import sys
from pathlib import Path

import pytest
import pytest_asyncio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.config import get_settings  # noqa: E402
from bot.database.db import create_tables, make_engine, make_session_factory  # noqa: E402
from bot.database.seed import seed  # noqa: E402
from bot.main import build_dispatcher  # noqa: E402
from bot.services.inventory import InventoryService  # noqa: E402
from emulator import ChatEmulator  # noqa: E402

ADMIN_ID = 9001


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ADMIN_IDS", str(ADMIN_ID))
    monkeypatch.delenv("REDIS_URL", raising=False)
    return get_settings()


@pytest_asyncio.fixture()
async def service(env):
    engine = make_engine(env.database_url)
    await create_tables(engine, drop=True)
    factory = make_session_factory(engine)
    async with factory() as session:
        await seed(session)
    async with factory() as session:
        yield InventoryService(session)
    await engine.dispose()


@pytest_asyncio.fixture()
async def chat(env):
    dp = await build_dispatcher(env, reset=True)
    emulator = ChatEmulator(dp)
    yield emulator
    await dp["engine"].dispose()
    for router in dp.sub_routers:          # роутеры — модульные объекты: отсоединяем для
        router._parent_router = None       # следующего теста с новым Dispatcher
