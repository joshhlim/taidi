"""Authentication: a pluggable JWT verifier plus a dev-only token minter.

Both auth modes produce the same thing — a CurrentUser(user_id, display_name)
— so the rest of the app never needs to know which mode is active. In "dev"
mode, POST /auth/dev-login mints a token for any display name, no external
identity provider needed; that's what local development and tests use. In
"supabase" mode, tokens are verified against the Supabase project's JWT
secret instead, and nothing else changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .time import utcnow

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    display_name: str


def mint_dev_token(display_name: str, user_id: UUID | None = None) -> tuple[str, UUID]:
    """Dev-mode only: mint a token for a fresh (or given) user id."""
    uid = user_id or uuid4()
    payload = {
        "sub": str(uid),
        "display_name": display_name,
        "exp": utcnow() + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    token = jwt.encode(payload, settings.dev_jwt_secret, algorithm="HS256")
    return token, uid


def _decode(token: str) -> dict[str, Any]:
    if settings.auth_mode == "dev":
        secret = settings.dev_jwt_secret
        # Dev tokens carry no audience claim — nothing to check.
        decode_kwargs: dict[str, Any] = {"options": {"verify_aud": False}}
    else:
        if not settings.supabase_jwt_secret:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR, "Supabase auth is not configured."
            )
        secret = settings.supabase_jwt_secret
        # Supabase stamps every access token with aud="authenticated" —
        # verifying it rejects, e.g., a service-role or anon-key token
        # being mistakenly used as a user's bearer token.
        decode_kwargs = {"audience": "authenticated"}
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], **decode_kwargs)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e


def _display_name_from_claims(claims: dict[str, Any]) -> str:
    if settings.auth_mode == "dev":
        return str(claims.get("display_name", "Player"))
    # Supabase's default claims don't carry a display name unless the
    # client set one in user_metadata at sign-up.
    meta = claims.get("user_metadata") or {}
    name = meta.get("display_name") or claims.get("email") or "Player"
    return str(name)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token.")
    claims = _decode(creds.credentials)
    return CurrentUser(user_id=UUID(claims["sub"]), display_name=_display_name_from_claims(claims))
