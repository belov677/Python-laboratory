"""Конфигурация из переменных окружения (токен в коде не хранится)."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///warehouse_bot.db"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    admin_ids: frozenset[int] = field(default_factory=lambda: frozenset(
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "bot_actions.log"))


def get_settings() -> Settings:
    return Settings()
