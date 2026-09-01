"""App settings, read from environment (prefix TAIDI_) or a local .env file."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TAIDI_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://taidi:taidi_dev@localhost:5433/taidi"

    # "dev": local HS256 tokens minted by POST /auth/dev-login, no external IdP needed.
    # "supabase": verify tokens issued by Supabase Auth against its JWT secret.
    auth_mode: Literal["dev", "supabase"] = "dev"
    dev_jwt_secret: str = "dev-only-insecure-secret-change-me"
    supabase_jwt_secret: str | None = None
    access_token_ttl_minutes: int = 60 * 24 * 7  # a week — fine for a party-game app

    # :3000 is Next.js's default; :3100 is what this repo's local dev
    # and Playwright config use instead, since :3000 is often already
    # taken by an unrelated project on a shared dev machine.
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3100"]


settings = Settings()
