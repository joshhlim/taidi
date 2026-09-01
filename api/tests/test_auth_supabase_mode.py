"""Verifies the supabase-mode JWT path against realistically-shaped tokens,
without needing a real Supabase project. See auth.py's module docstring —
dev and supabase modes share everything downstream of get_current_user."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from app.auth import _decode, _display_name_from_claims
from app.config import settings

TEST_SECRET = "test-supabase-secret-at-least-32-characters-long"


@pytest.fixture(autouse=True)
def _supabase_mode(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "supabase_jwt_secret", TEST_SECRET)
    yield


def _supabase_claims(**overrides) -> dict:
    claims = {
        "sub": str(uuid4()),
        "aud": "authenticated",
        "role": "authenticated",
        "email": "alice@example.com",
        "user_metadata": {"display_name": "Alice"},
        "app_metadata": {"provider": "email"},
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    claims.update(overrides)
    return claims


def _sign(claims: dict, secret: str = TEST_SECRET) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def test_valid_supabase_token_decodes_with_display_name():
    claims = _supabase_claims()
    decoded = _decode(_sign(claims))
    assert decoded["sub"] == claims["sub"]
    assert _display_name_from_claims(decoded) == "Alice"


def test_falls_back_to_email_when_no_display_name_set():
    claims = _supabase_claims(user_metadata={})
    decoded = _decode(_sign(claims))
    assert _display_name_from_claims(decoded) == "alice@example.com"


def test_wrong_audience_is_rejected():
    claims = _supabase_claims(aud="anon")
    with pytest.raises(Exception):  # noqa: B017 - HTTPException, imported lazily by auth.py
        _decode(_sign(claims))


def test_wrong_secret_is_rejected():
    claims = _supabase_claims()
    with pytest.raises(Exception):  # noqa: B017
        _decode(_sign(claims, secret="a-completely-different-secret-value"))


def test_expired_token_is_rejected():
    claims = _supabase_claims(exp=datetime.now(UTC) - timedelta(minutes=1))
    with pytest.raises(Exception):  # noqa: B017
        _decode(_sign(claims))
