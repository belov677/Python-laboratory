"""Логистическая система (итоговый проект, вариант 17). Запуск: uvicorn --factory app.main:create_app"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api import routers
from app.config import Settings
from app.container import Container
from app.core.exceptions import AppError
from app.core.observability import RequestLogMiddleware, setup_logging

log = logging.getLogger("app")


def error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse(body, status_code=status)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_r: Request, e: AppError):
        return error(e.status_code, e.code, e.message, e.details or None)

    @app.exception_handler(RequestValidationError)
    async def validation(_r: Request, e: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]} for err in e.errors()]
        return error(422, "VALIDATION_ERROR", "Некорректные входные данные", details)

    @app.exception_handler(IntegrityError)
    async def integrity(_r: Request, e: IntegrityError):
        log.warning("нарушение ограничения БД: %s", e.orig)
        return error(409, "CONSTRAINT_VIOLATION", "Операция нарушает ограничения данных")

    @app.exception_handler(Exception)
    async def unexpected(_r: Request, e: Exception):
        log.exception("необработанная ошибка: %s", e)  # traceback — только в журнал
        return error(500, "INTERNAL_ERROR", "Внутренняя ошибка сервера")


def broker_connected(container: Container) -> bool:
    connection = getattr(container.publisher, "connection", None)
    if connection is None or connection.is_closed:
        return False
    connected = getattr(connection, "connected", None)  # RobustConnection: False во время переподключения
    return connected.is_set() if connected is not None else True


def create_app(container: Container | None = None, *, create_schema: bool = False) -> FastAPI:
    container = container or Container(Settings())
    setup_logging(container.settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await container.start(create=create_schema)
        yield
        await container.stop()

    app = FastAPI(
        title="Логистическая система",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/swagger",
        redoc_url="/redoc",
        description="Заказы на перевозку, маршруты, транспорт, водители и доставки. "
        "Авторизация: JWT (роли USER и ADMIN).",
    )
    app.state.container = container
    # документация с локальными ресурсами swagger-ui/redoc (работает без доступа к CDN)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

    @app.get("/swagger", include_in_schema=False)
    async def swagger():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} — Swagger UI",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc():
        return get_redoc_html(
            openapi_url="/openapi.json", title=f"{app.title} — ReDoc", redoc_js_url="/static/redoc.standalone.js"
        )

    app.add_middleware(RequestLogMiddleware, metrics=container.metrics)
    register_error_handlers(app)
    for router in (routers.auth, routers.routes, routers.fleet, routers.orders, routers.deliveries):
        app.include_router(router)

    @app.get("/health", tags=["Служебные"])
    async def health() -> JSONResponse:
        """healthy — всё работает; degraded — Redis/брокер недоступны (работа продолжается); unhealthy — нет БД."""
        checks = {}
        try:
            async with container.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "up"
        except Exception:  # noqa: BLE001
            checks["database"] = "down"
        checks["redis"] = "up" if await container.cache.ping() else "down"
        checks["broker"] = "up" if broker_connected(container) else "down"
        backlog = await container.outbox.backlog() if checks["database"] == "up" else None
        if checks["database"] == "down":
            status, code = "unhealthy", 503
        else:
            status, code = ("healthy", 200) if all(v == "up" for v in checks.values()) else ("degraded", 200)
        return JSONResponse({"status": status, "checks": checks, "outbox_backlog": backlog}, status_code=code)

    @app.get("/metrics", tags=["Служебные"])
    async def metrics() -> dict:
        return {**container.metrics.snapshot(), "cache": container.cache.stats}

    return app
