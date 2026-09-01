"""Shared fixtures: every test gets a throwaway local SQLite database."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import db  # noqa: E402

APP_PATH = ROOT / "taidi.py"


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Point db at a fresh file and make sure no cloud credentials leak in."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("APP_PASSCODE", raising=False)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    yield


@pytest.fixture
def app_path():
    return str(APP_PATH)
