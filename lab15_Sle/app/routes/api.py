"""REST API (Blueprint api) — JSON."""
from flask import Blueprint, current_app, jsonify, request

from extensions import get_service

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/shipments")
def list_shipments():
    a = request.args
    page = a.get("page", 1, type=int)
    items, total, pages = get_service().list(
        search=a.get("q"), status=a.get("status"), client_id=a.get("client_id", type=int),
        sort=a.get("sort", "created"), order=a.get("order", "desc"), page=page,
        page_size=a.get("size", current_app.config["PAGE_SIZE"], type=int))
    return jsonify({"items": [s.to_dict() for s in items], "total": total, "page": page,
                    "pages": pages})


@bp.get("/shipments/<int:shipment_id>")
def get_shipment(shipment_id: int):
    return jsonify(get_service().get(shipment_id).to_dict())


@bp.get("/track/<number>")
def track(number: str):
    return jsonify(get_service().track(number).to_dict())


def payload() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        from services.exceptions import ValidationError
        raise ValidationError({"body": "Ожидается JSON-объект"})
    return data


@bp.post("/shipments")
def create_shipment():
    shipment = get_service().create(payload())
    return jsonify(shipment.to_dict()), 201, {"Location": f"/api/shipments/{shipment.id}"}


@bp.put("/shipments/<int:shipment_id>")
def update_shipment(shipment_id: int):
    return jsonify(get_service().update(shipment_id, payload()).to_dict())


@bp.post("/shipments/<int:shipment_id>/status")
def change_status(shipment_id: int):
    data = payload()
    s = get_service().change_status(shipment_id, data.get("status", ""), data.get("location", ""))
    return jsonify(s.to_dict())


@bp.delete("/shipments/<int:shipment_id>")
def delete_shipment(shipment_id: int):
    get_service().delete(shipment_id)
    return "", 204


@bp.get("/clients")
def list_clients():
    return jsonify([c.to_dict() for c in get_service().list_clients()])


@bp.post("/clients")
def create_client():
    return jsonify(get_service().create_client(payload()).to_dict()), 201


@bp.get("/clients/<int:client_id>/shipments")
def client_shipments(client_id: int):
    client = get_service().get_client(client_id)
    return jsonify({"client": client.to_dict(),
                    "shipments": [{"id": s.id, "tracking_number": s.tracking_number,
                                   "status": s.status.name} for s in client.shipments]})
