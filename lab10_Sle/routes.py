"""HTTP-слой: разбор запроса, вызов сервиса, формирование ответа."""
from __future__ import annotations

import hashlib
import json

from flask import Blueprint, current_app, jsonify, request

from exceptions import ValidationError

api = Blueprint("api", __name__)


def service():
    return current_app.config["ITEM_SERVICE"]


def int_arg(name: str, minimum: int = 0) -> int | None:
    value = request.args.get(name)
    if value is None:
        return None
    if not value.lstrip("-").isdigit() or int(value) < minimum:
        raise ValidationError(f"Параметр {name} должен быть целым числом ≥ {minimum}")
    return int(value)


@api.get("/items")
def list_items():
    items = service().get_items(
        category=request.args.get("category"), location=request.args.get("location"),
        min_quantity=int_arg("min_quantity"), max_quantity=int_arg("max_quantity"),
        search=request.args.get("search"), sort=request.args.get("sort", "id"),
        order=request.args.get("order", "asc"))
    data = [i.to_dict() for i in items]
    page = int_arg("page", 1)
    if page is None:
        return jsonify(data)
    limit = int_arg("limit", 1) or 10
    return jsonify({"items": data[(page - 1) * limit: page * limit], "page": page,
                    "limit": limit, "total": len(data)})


@api.get("/items/low-stock")
def low_stock():
    return jsonify([i.to_dict() for i in service().low_stock()])


@api.get("/items/statistics")
def statistics():
    return jsonify(service().statistics())


@api.get("/items/<int:item_id>")
def get_item(item_id: int):
    body = service().get_item(item_id).to_dict()
    etag = hashlib.md5(json.dumps(body, sort_keys=True).encode()).hexdigest()
    if request.headers.get("If-None-Match") == etag:
        return "", 304, {"ETag": etag}
    return jsonify(body), 200, {"ETag": etag}


@api.post("/items")
def create_item():
    item = service().create_item(request.get_json(silent=True))
    return jsonify(item.to_dict()), 201, {"Location": f"/items/{item.id}"}


@api.put("/items/<int:item_id>")
def replace_item(item_id: int):
    return jsonify(service().replace_item(item_id, request.get_json(silent=True)).to_dict())


@api.patch("/items/<int:item_id>")
def patch_item(item_id: int):
    return jsonify(service().patch_item(item_id, request.get_json(silent=True)).to_dict())


@api.delete("/items/<int:item_id>")
def delete_item(item_id: int):
    service().delete_item(item_id)
    return "", 204
