"""Общие функции: сессия БД на запрос, CSRF-токен."""
import secrets

from flask import abort, current_app, g, request, session

from services.services import ShipmentService


def get_service() -> ShipmentService:
    if "service" not in g:
        g.service = ShipmentService(current_app.extensions["db"].session())
    return g.service


def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def check_csrf() -> None:
    if current_app.config.get("WTF_CSRF_DISABLED"):
        return
    token = request.form.get("csrf_token")
    if not token or token != session.get("_csrf"):
        abort(400, description="Неверный CSRF-токен")
