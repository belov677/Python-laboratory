"""Подключение к PostgreSQL через SQLAlchemy 2.x."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL",
                         "postgresql+psycopg://lab:lab@localhost:5432/logistics")


def make_engine(url: str = DATABASE_URL, echo: bool = False):
    return create_engine(url, echo=echo)


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
