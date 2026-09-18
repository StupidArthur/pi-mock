import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PI_STORAGE_TYPE", "memory")
os.environ.setdefault("PI_SERVER_NAME", "TEST-PI")

from fastapi.testclient import TestClient  # noqa: E402

from app.core import fault  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_state(client):
    client.post("/mock/reset")
    yield
    client.post("/mock/reset")
