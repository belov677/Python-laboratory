"""Настройки приложения: только из переменных окружения (секреты не хранятся в коде)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {name} (см. .env.example)")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _required("DATABASE_URL"))
    jwt_secret: str = field(default_factory=lambda: _required("JWT_SECRET"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    broker_url: str = field(default_factory=lambda: os.getenv("BROKER_URL", ""))
    jwt_ttl_minutes: int = field(default_factory=lambda: int(os.getenv("JWT_TTL_MINUTES", "60")))
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "300")))
    outbox_interval: float = field(default_factory=lambda: float(os.getenv("OUTBOX_INTERVAL", "2")))
    admin_email: str = field(default_factory=lambda: os.getenv("ADMIN_EMAIL", ""))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    seed_demo_data: bool = field(default_factory=lambda: os.getenv("SEED_DEMO_DATA", "1") == "1")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
