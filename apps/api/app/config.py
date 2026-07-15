"""Application configuration.

Settings are loaded from environment variables (prefixed ``ST_``) and an
optional ``.env`` file. See ``.env.example`` for the supported keys.

Local-first note: ``host`` defaults to ``127.0.0.1`` so the API is never
exposed beyond the local machine unless the operator deliberately overrides it.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Spending Tracker API."""

    model_config = SettingsConfigDict(
        env_prefix="ST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "spending-tracker-api"
    version: str = "0.0.1"

    # Local-first: bind to loopback by default.
    host: str = "127.0.0.1"
    port: int = 8787

    # Origins allowed to call the API from the browser (Vite dev server).
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
