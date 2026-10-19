"""Лабораторная №15, вариант 17 — веб-приложение «Логистическая компания» (Flask).

Запуск: python app.py  (переменные окружения — см. .env.example)
"""
from __future__ import annotations

import logging
import os
import time

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from config import Config
from database import Database
from extensions import csrf_token
from routes import api, web
from services.exceptions import AppError, ValidationError


def setup_logging(app: Flask) -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    app.logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def wants_json() -> bool:
    return request.path.startswith("/api/")


def register_errors(app: Flask) -> None:
    @app.errorhandler(AppError)
    def app_error(error: AppError):
        app.logger.warning("%s %s -> %s: %s", request.method, request.path,
                           error.status_code, error)
        body = {"error": type(error).__name__, "message": str(error)}
        if isinstance(error, ValidationError):
            body["fields"] = error.errors
        if wants_json():
            return jsonify(body), error.status_code
        return render_template("error.html", code=error.status_code, message=str(error)), \
            error.status_code

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        if wants_json():
            return jsonify({"error": error.name, "message": error.description}), error.code
        template = "404.html" if error.code == 404 else "error.html"
        return render_template(template, code=error.code, message=error.description), error.code

    @app.errorhandler(Exception)
    def server_error(error: Exception):
        app.extensions["db"].session.rollback()
        app.logger.exception("Необработанная ошибка: %s", error)
        if wants_json():
            return jsonify({"error": "Internal Server Error",
                            "message": "Внутренняя ошибка сервера"}), 500
        return render_template("error.html", code=500,
                               message="Внутренняя ошибка сервера. Попробуйте позже."), 500


def create_app(config: type[Config] = Config, reset: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    app.secret_key = config.SECRET_KEY
    setup_logging(app)
    db = Database(config.DATABASE_URL)
    db.init(drop=reset)
    app.extensions["db"] = db
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.register_blueprint(web.bp)
    app.register_blueprint(api.bp)
    register_errors(app)

    @app.before_request
    def start_timer():
        g.started = time.perf_counter()

    @app.after_request
    def log_request(response):
        ms = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        app.logger.info("%s %s -> %s (%.1f мс)", request.method, request.full_path.rstrip("?"),
                        response.status_code, ms)
        return response

    @app.teardown_appcontext
    def remove_session(_exc=None):
        db.session.remove()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    reset = os.getenv("RESET_DB") == "1"
    application = create_app(reset=reset)
    if reset:
        from seed import seed
        from services.services import ShipmentService
        seed(ShipmentService(application.extensions["db"].session()))
        application.extensions["db"].session.remove()
    application.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5015")),
                    debug=os.getenv("FLASK_DEBUG") == "1")
