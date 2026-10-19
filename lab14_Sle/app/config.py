"""Настройки приложения из переменных окружения."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL",
                                  "postgresql+psycopg://lab:lab@localhost:5432/warehouse_api")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    cache_ttl: int = int(os.getenv("CACHE_TTL", "120"))
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-secret-change-me-in-production-0017")
    jwt_ttl_minutes: int = int(os.getenv("JWT_TTL_MINUTES", "60"))
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin12345")
    app_env: str = os.getenv("APP_ENV", "development")
    audit_log: str = os.getenv("AUDIT_LOG", "audit.log")


settings = Settings()
