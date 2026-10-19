import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from database import make_engine, make_session_factory  # noqa: E402
from main import seed  # noqa: E402
from models import Base  # noqa: E402
from services.services import LogisticsService  # noqa: E402

TEST_URL = "postgresql+psycopg://lab:lab@localhost:5432/logistics_test"


@pytest.fixture
def service():
    engine = make_engine(TEST_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    svc = LogisticsService(make_session_factory(engine))
    seed(svc)
    yield svc
    engine.dispose()
