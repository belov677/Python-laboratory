from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from exceptions import ValidationError

api = Blueprint("api", __name__)


def service():
    return current_app.config["ITEM_SERVICE"]


def int_arg(name: str, minimum: int = 0) -> int | None:
    value = request.args.get(name)
    if value is None:
        return None
    if not value.isdigit() or int(value) < minimum:
        raise ValidationError(f"Параметр {name} должен быть целым числом ≥ {minimum}")
    return int(value)


@api.get("/items")
def list_items():
    page, limit = int_arg("page", 1), int_arg("limit", 1)
    kwargs = dict(category=request.args.get("category"), min_quantity=int_arg("min_quantity"),
                  max_quantity=int_arg("max_quantity"), search=request.args.get("search"),
                  sort=request.args.get("sort", "id"), order=request.args.get("order", "asc"))
    if page is None:
        return jsonify(service().get_items(**kwargs))
    limit = limit or 10
    items = service().get_items(limit=limit, offset=(page - 1) * limit, **kwargs)
    return jsonify({"items": items, "page": page, "limit": limit,
                    "total": service().repository.count()})


@api.get("/items/low-stock")
def low_stock():
    return jsonify(service().low_stock())


@api.get("/items/statistics")
def statistics():
    return jsonify(service().statistics())


@api.get("/items/<int:item_id>")
def get_item(item_id: int):
    item, source = service().get_item(item_id)
    return jsonify(item), 200, {"X-Cache": source}


@api.get("/items/<int:item_id>/suppliers")
def suppliers(item_id: int):
    return jsonify(service().repository.suppliers(item_id))


@api.get("/items/<int:item_id>/movements")
def movements(item_id: int):
    return jsonify(service().repository.movements(item_id))


@api.post("/items")
def create_item():
    item = service().create_item(request.get_json(silent=True))
    return jsonify(item), 201, {"Location": f"/items/{item['id']}"}


@api.put("/items/<int:item_id>")
def replace_item(item_id: int):
    return jsonify(service().replace_item(item_id, request.get_json(silent=True)))


@api.patch("/items/<int:item_id>")
def patch_item(item_id: int):
    return jsonify(service().patch_item(item_id, request.get_json(silent=True)))


@api.delete("/items/<int:item_id>")
def delete_item(item_id: int):
    service().delete_item(item_id)
    return "", 204


@api.post("/items/<int:item_id>/receipts")
def receive(item_id: int):
    return jsonify(service().receive(item_id, request.get_json(silent=True))), 201


@api.post("/items/<int:item_id>/shipments")
def ship(item_id: int):
    return jsonify(service().ship(item_id, request.get_json(silent=True))), 201


@api.get("/cache")
def cache_info():
    return jsonify(service().cache.info())
