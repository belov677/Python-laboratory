"""REST API склада на Flask + PostgreSQL + Redis (лабораторная №11, вариант 17).

Запуск: python app.py [--port 5000]
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

import config
from cache import RedisCache
from database import Database
from exceptions import ApiError
from repository import ItemRepository
from routes import api
from service import ItemService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")
STATIC_DIR = Path(__file__).resolve().parents[1] / "cdn" / "static"


def create_app(database_url: str = config.DATABASE_URL, redis_url: str = config.REDIS_URL,
               api_key: str = config.API_KEY) -> Flask:
    app = Flask(__name__, static_folder=None)   # статику отдаёт собственный маршрут
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    db = Database(database_url)
    app.config["ITEM_SERVICE"] = ItemService(ItemRepository(db),
                                             RedisCache(redis_url, config.CACHE_TTL))
    app.config["DB"] = db
    app.register_blueprint(api)
    instance = os.getenv("INSTANCE", "api")

    @app.get("/static/<path:name>")       # origin-сервер статических ресурсов
    def static_files(name: str):
        return send_from_directory(STATIC_DIR, name, max_age=3600)

    @app.before_request
    def before():
        g.started = time.perf_counter()
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and \
                request.headers.get("X-API-Key") != api_key:
            return jsonify({"error": "Missing or invalid API key", "code": "UNAUTHORIZED"}), 401

    @app.after_request
    def after(response):
        response.headers["X-Instance"] = instance
        log.info("[%s] %s %s -> %s -> %.1f ms", instance, request.method,
                 request.full_path.rstrip("?"), response.status_code,
                 (time.perf_counter() - g.get("started", time.perf_counter())) * 1000)
        return response

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify({"error": str(error), "code": error.code}), error.status

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return jsonify({"error": error.description,
                        "code": error.name.upper().replace(" ", "_")}), error.code

    @app.errorhandler(Exception)
    def internal_error(error: Exception):
        log.exception("Unhandled error")
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    # в контейнере нужно слушать все интерфейсы (0.0.0.0), иначе проброшенный порт недоступен
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--reset-db", action="store_true", help="пересоздать схему и данные")
    args = parser.parse_args()
    application = create_app()
    if args.reset_db:
        application.config["DB"].reset()
    application.run(host=args.host, port=args.port)
