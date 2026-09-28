"""Shared test fixtures: temp DB, seeded app client."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("VAYUSETU_DB_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'vayusetu_test.db'}")
os.environ.setdefault("AUTO_TRAIN_ON_START", "false")


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
