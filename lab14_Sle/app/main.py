"""REST API склада на FastAPI (лабораторная №14, вариант 17).

Запуск: uvicorn main:app --app-dir app --port 8000   (или python app/main.py)
Документация: /docs (Swagger UI), /redoc
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from cache import ItemCache
from config import Settings, settings
from database import Database
from exceptions import AppError
from routers import auth, items
from services.auth import AuthService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")


def create_app(config: Settings = settings, reset_db: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = Database(config.database_url)
        app.state.db.create_all(drop=reset_db)
        app.state.cache = ItemCache(config.redis_url, config.cache_ttl)
        with app.state.db.session_factory() as session:
            AuthService(session).ensure_admin(config.admin_username, config.admin_password)
        log.info("Application started (env=%s)", config.app_env)
        yield
        app.state.db.engine.dispose()

    app = FastAPI(title="Warehouse API — склад (вариант 17)", version="1.0.0",
                  description="REST API складского учёта: товары, остатки, поставщики, "
                              "сроки годности. Чтение — USER, изменение — ADMIN (JWT).",
                  lifespan=lifespan, docs_url=None, redoc_url=None)
    # Swagger UI и ReDoc раздаются локально — документация работает без доступа в интернет
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui():
        return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title + " — Swagger UI",
                                   swagger_js_url="/static/swagger-ui-bundle.js",
                                   swagger_css_url="/static/swagger-ui.css")

    @app.get("/redoc", include_in_schema=False)
    async def redoc():
        return get_redoc_html(openapi_url="/openapi.json", title=app.title + " — ReDoc",
                              redoc_js_url="/static/redoc.standalone.js")

    app.include_router(auth.router)
    app.include_router(items.router)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        log.info("%s %s -> %s %.1f ms", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - start) * 1000)
        return response

    @app.exception_handler(AppError)
    async def app_error(request: Request, error: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        return JSONResponse({"error": error.code, "message": str(error)},
                            status_code=error.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
                   for e in error.errors()]
        return JSONResponse({"error": "VALIDATION_ERROR", "message": "Некорректные данные",
                             "details": details}, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request: Request, error: SQLAlchemyError):
        log.exception("Database error")
        return JSONResponse({"error": "DATABASE_ERROR", "message": "Ошибка базы данных"},
                            status_code=500)

    @app.get("/health", tags=["Служебное"], summary="Проверка работоспособности")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app(reset_db=os.getenv("RESET_DB") == "1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
