"""HTML-страницы (Blueprint web)."""
from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   url_for)

from extensions import check_csrf, get_service
from models.models import Status
from services.exceptions import ConflictError, NotFoundError, ValidationError
from services.services import CARGO_TYPES

bp = Blueprint("web", __name__)


def form_data() -> dict:
    f = request.form
    cargos = [{"description": d, "weight_kg": w, "cargo_type": t}
              for d, w, t in zip(f.getlist("cargo_description"), f.getlist("cargo_weight"),
                                 f.getlist("cargo_type"))]
    return {"client_id": f.get("client_id"), "origin": f.get("origin"),
            "destination": f.get("destination"), "distance_km": f.get("distance_km"),
            "cargos": cargos}


def render_form(template: str, data: dict, errors=None, **extra):
    while len(data.setdefault("cargos", [])) < 3:
        data["cargos"].append({"description": "", "weight_kg": "", "cargo_type": "обычный"})
    return render_template(template, data=data, errors=errors or {},
                           clients=get_service().list_clients(), cargo_types=CARGO_TYPES,
                           **extra), 400 if errors else 200


@bp.get("/")
def index():
    service = get_service()
    latest, total, _ = service.list(page_size=3)
    return render_template("index.html", stats=service.stats(), latest=latest, total=total)


@bp.get("/shipments")
def shipment_list():
    args = request.args
    page = args.get("page", 1, type=int)
    items, total, pages = get_service().list(
        search=args.get("q") or None, status=args.get("status") or None,
        client_id=args.get("client_id", type=int), sort=args.get("sort", "created"),
        order=args.get("order", "desc"), page=page,
        page_size=current_app.config["PAGE_SIZE"])
    return render_template("shipments/list.html", items=items, total=total, pages=pages,
                           page=page, args=args, statuses=Status,
                           clients=get_service().list_clients())


@bp.get("/shipments/<int:shipment_id>")
def shipment_detail(shipment_id: int):
    shipment = get_service().get(shipment_id)
    return render_template("shipments/detail.html", s=shipment, statuses=Status)


@bp.get("/track")
def track():
    number = request.args.get("number", "").strip()
    if not number:
        return render_template("shipments/track.html", number="")
    try:
        shipment = get_service().track(number)
    except NotFoundError as error:
        flash(str(error), "error")
        return render_template("shipments/track.html", number=number), 404
    return redirect(url_for("web.shipment_detail", shipment_id=shipment.id))


@bp.route("/shipments/new", methods=["GET", "POST"])
def shipment_create():
    if request.method == "GET":
        return render_form("shipments/form.html", {"client_id": request.args.get("client_id")},
                           title="Новое отправление")
    check_csrf()
    data = form_data()
    try:
        shipment = get_service().create(data)
    except ValidationError as error:
        return render_form("shipments/form.html", data, error.errors, title="Новое отправление")
    except ConflictError as error:
        flash(str(error), "error")
        return render_form("shipments/form.html", data, {"_": str(error)}, title="Новое отправление")
    flash(f"Отправление {shipment.tracking_number} создано, стоимость {shipment.cost} руб.", "ok")
    return redirect(url_for("web.shipment_detail", shipment_id=shipment.id))


@bp.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
def shipment_edit(shipment_id: int):
    service = get_service()
    shipment = service.get(shipment_id)
    title = f"Редактирование {shipment.tracking_number}"
    if request.method == "GET":
        data = {"client_id": shipment.client_id, "origin": shipment.origin,
                "destination": shipment.destination, "distance_km": shipment.distance_km,
                "cargos": [{"description": c.description, "weight_kg": c.weight_kg,
                            "cargo_type": c.cargo_type} for c in shipment.cargos]}
        return render_form("shipments/form.html", data, title=title, shipment=shipment)
    check_csrf()
    data = form_data()
    try:
        service.update(shipment_id, data)
    except ValidationError as error:
        return render_form("shipments/form.html", data, error.errors, title=title, shipment=shipment)
    except ConflictError as error:
        flash(str(error), "error")
        return redirect(url_for("web.shipment_detail", shipment_id=shipment_id))
    flash("Изменения сохранены", "ok")
    return redirect(url_for("web.shipment_detail", shipment_id=shipment_id))


@bp.post("/shipments/<int:shipment_id>/status")
def shipment_status(shipment_id: int):
    check_csrf()
    try:
        s = get_service().change_status(shipment_id, request.form.get("status", ""),
                                        request.form.get("location", ""))
        flash(f"Статус изменён: {s.status.value}", "ok")
    except (ValidationError, ConflictError) as error:
        flash(str(error), "error")
    return redirect(url_for("web.shipment_detail", shipment_id=shipment_id))


@bp.route("/shipments/<int:shipment_id>/delete", methods=["GET", "POST"])
def shipment_delete(shipment_id: int):
    service = get_service()
    shipment = service.get(shipment_id)
    if request.method == "GET":
        return render_template("shipments/delete.html", s=shipment)
    check_csrf()
    try:
        service.delete(shipment_id)
    except ConflictError as error:
        flash(str(error), "error")
        return redirect(url_for("web.shipment_detail", shipment_id=shipment_id))
    flash(f"Отправление {shipment.tracking_number} удалено", "ok")
    return redirect(url_for("web.shipment_list"))


@bp.get("/clients")
def client_list():
    return render_template("clients/list.html", clients=get_service().list_clients())


@bp.get("/clients/<int:client_id>")
def client_detail(client_id: int):
    return render_template("clients/detail.html", c=get_service().get_client(client_id))


@bp.route("/clients/new", methods=["GET", "POST"])
def client_create():
    data, errors = {}, {}
    if request.method == "POST":
        check_csrf()
        data = request.form.to_dict()
        try:
            client = get_service().create_client(data)
            flash(f"Клиент {client.name} добавлен", "ok")
            return redirect(url_for("web.client_detail", client_id=client.id))
        except ValidationError as error:
            errors = error.errors
        except ConflictError as error:
            errors = {"email": str(error)}
    return render_template("clients/form.html", data=data, errors=errors), 400 if errors else 200


@bp.get("/boom")
def boom():
    """Маршрут для демонстрации обработки ошибки 500."""
    if not current_app.config.get("DEBUG_ROUTES"):
        abort(404)
    raise RuntimeError("Демонстрационная внутренняя ошибка")
