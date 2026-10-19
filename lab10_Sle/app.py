"""REST API склада на Flask (лабораторная №10, вариант 17).

Запуск: python app.py  → http://127.0.0.1:5000
"""
from __future__ import annotations

import logging
import os
import time

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from exceptions import ApiError
from repository import ItemRepository
from routes import api
from service import ItemService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

SEED = [
    dict(sku="NB-001", name="Ноутбук Lenovo", category="электроника", quantity=12, min_stock=5, price=54990, location="A-01"),
    dict(sku="MS-010", name="Мышь Logitech", category="электроника", quantity=3, min_stock=10, price=1490, location="A-02"),
    dict(sku="PP-A4", name="Бумага A4 500 л.", category="канцелярия", quantity=80, min_stock=40, price=420, location="B-01"),
    dict(sku="PN-BL", name="Ручка шариковая синяя", category="канцелярия", quantity=15, min_stock=50, price=25, location="B-02"),
    dict(sku="CH-OF", name="Кресло офисное", category="мебель", quantity=7, min_stock=2, price=8990, location="C-01"),
    dict(sku="TB-120", name="Стол письменный 120 см", category="мебель", quantity=0, min_stock=1, price=12500, location="C-02"),
]


def create_app(service: ItemService | None = None, api_key: str | None = None,
               seed: bool = True) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    if service is None:
        service = ItemService(ItemRepository())
        if seed:
            for data in SEED:
                service.create_item(data)
    app.config["ITEM_SERVICE"] = service
    app.config["API_KEY"] = api_key if api_key is not None else os.getenv("API_KEY", "secret-key")
    app.register_blueprint(api)

    @app.before_request
    def before():
        g.started = time.perf_counter()
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and app.config["API_KEY"]:
            if request.headers.get("X-API-Key") != app.config["API_KEY"]:
                return jsonify({"error": "Missing or invalid API key",
                                "code": "UNAUTHORIZED"}), 401

    @app.after_request
    def after(response):
        duration = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        log.info("%s %s -> %s -> %.1f ms", request.method, request.full_path.rstrip("?"),
                 response.status_code, duration)
        return response

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify({"error": str(error), "code": error.code}), error.status

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        code = error.name.upper().replace(" ", "_")
        return jsonify({"error": error.description, "code": code}), error.code

    @app.errorhandler(Exception)
    def internal_error(error: Exception):
        log.exception("Unhandled error")
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)))
