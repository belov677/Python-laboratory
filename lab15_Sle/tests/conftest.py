import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from seed import seed  # noqa: E402
from services.services import ShipmentService  # noqa: E402


class Cfg(TestConfig):
    WTF_CSRF_DISABLED = True
    DEBUG_ROUTES = True


@pytest.fixture()
def app():
    application = create_app(Cfg, reset=True)
    seed(ShipmentService(application.extensions["db"].session()))
    application.extensions["db"].session.remove()
    yield application
    application.extensions["db"].session.remove()
    application.extensions["db"].engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def new_shipment():
    return {"client_id": 1, "origin": "Москва", "destination": "Тула", "distance_km": 180,
            "cargos": [{"description": "Холодильник", "weight_kg": 75, "cargo_type": "хрупкий"}]}
