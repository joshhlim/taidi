"""Verifies the supabase-mode JWT path against realistically-shaped tokens,
without needing a real Supabase project. See auth.py's module docstring —
dev and supabase modes share everything downstream of get_current_user, and
Supabase projects use one of two signing schemes depending on when they were
created (legacy shared secret, or a newer asymmetric key verified via JWKS)
— both are covered here."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import app.auth as auth_module
import jwt
import pytest
from app.auth import _decode, _display_name_from_claims
from app.config import settings
from cryptography.hazmat.primitives.asymmetric import ec

TEST_SECRET = "test-supabase-secret-at-least-32-characters-long"


@pytest.fixture(autouse=True)
def _supabase_mode(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "supabase_jwt_secret", TEST_SECRET)
    monkeypatch.setattr(settings, "supabase_url", None)
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


# ============== JWKS mode (newer Supabase projects) ==============
#
# Newer Supabase projects sign with an asymmetric key instead of a shared
# secret, verified against a public JWKS endpoint. Real network access isn't
# needed to prove this works — PyJWKClient.fetch_data is monkeypatched to
# return a JWKS built from a real, freshly generated EC keypair.

TEST_KID = "test-key-1"


@pytest.fixture
def ec_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


@pytest.fixture
def jwks_mode(monkeypatch, ec_keypair):
    """Switches the autouse _supabase_mode fixture's config to JWKS mode and
    makes any PyJWKClient this test creates serve our test keypair instead
    of fetching a real JWKS over the network."""
    _private_key, public_key = ec_keypair
    monkeypatch.setattr(settings, "supabase_url", "https://fake-project.supabase.co")
    monkeypatch.setattr(settings, "supabase_jwt_secret", None)
    monkeypatch.setattr(auth_module, "_jwks_client", None)

    alg = jwt.algorithms.get_default_algorithms()["ES256"]
    jwk_dict = alg.to_jwk(public_key, as_dict=True)
    jwk_dict.update(kid=TEST_KID, alg="ES256", use="sig")
    fake_jwks = {"keys": [jwk_dict]}
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: fake_jwks)
    return None


def _sign_asymmetric(claims: dict, private_key) -> str:
    return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": TEST_KID})


def test_jwks_mode_valid_token_decodes(jwks_mode, ec_keypair):
    private_key, _ = ec_keypair
    claims = _supabase_claims()
    decoded = _decode(_sign_asymmetric(claims, private_key))
    assert decoded["sub"] == claims["sub"]
    assert _display_name_from_claims(decoded) == "Alice"


def test_jwks_mode_token_signed_by_a_different_key_is_rejected(jwks_mode, ec_keypair):
    other_private_key = ec.generate_private_key(ec.SECP256R1())
    claims = _supabase_claims()
    with pytest.raises(Exception):  # noqa: B017
        _decode(_sign_asymmetric(claims, other_private_key))


def test_jwks_mode_wrong_audience_is_rejected(jwks_mode, ec_keypair):
    private_key, _ = ec_keypair
    claims = _supabase_claims(aud="anon")
    with pytest.raises(Exception):  # noqa: B017
        _decode(_sign_asymmetric(claims, private_key))


def test_jwks_preferred_over_legacy_secret_when_both_configured(monkeypatch, jwks_mode, ec_keypair):
    # supabase_jwt_secret set alongside supabase_url — JWKS must win, not
    # silently fall back to (or require) the legacy secret.
    monkeypatch.setattr(settings, "supabase_jwt_secret", TEST_SECRET)
    private_key, _ = ec_keypair
    claims = _supabase_claims()
    decoded = _decode(_sign_asymmetric(claims, private_key))
    assert decoded["sub"] == claims["sub"]


def test_neither_jwks_nor_secret_configured_raises_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_jwt_secret", None)
    with pytest.raises(Exception):  # noqa: B017
        _decode(_sign(_supabase_claims()))
