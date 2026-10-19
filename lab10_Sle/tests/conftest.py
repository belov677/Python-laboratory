import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402

KEY = {"X-API-Key": "test-key"}
NEW = dict(sku="KB-01", name="Клавиатура", category="электроника", quantity=20,
           min_stock=5, price=1990, location="A-03")


@pytest.fixture
def client():
    app = create_app(api_key="test-key")
    app.config["TESTING"] = True
    return app.test_client()
