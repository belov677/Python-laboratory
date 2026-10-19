from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .models import Base


def make_engine(url: str) -> AsyncEngine:
    engine = create_async_engine(url)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine.sync_engine, "connect")
        def unicode_lower(dbapi_connection, _record) -> None:
            # встроенная lower() SQLite меняет регистр только латиницы — заменяем на Python-версию,
            # чтобы поиск «монитор» находил «Монитор»
            dbapi_connection.create_function("lower", 1, lambda s: s.lower() if s else s)
    return engine


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(engine: AsyncEngine, drop: bool = False) -> None:
    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
