"""Application configuration.

Settings are loaded from environment variables (prefixed ``ST_``) and an
optional ``.env`` file. See ``.env.example`` for the supported keys.

Local-first note: ``host`` defaults to ``127.0.0.1`` so the API is never
exposed beyond the local machine unless the operator deliberately overrides it.
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path
from threading import Lock

from pydantic import Field
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

    # Persistent application data stays in a local, configurable SQLite file.
    database_path: Path = Path("data/spending_tracker.db")

    # Bounded, local-only statement processing. Raw uploads remain temporary.
    import_max_bytes: int = Field(default=15 * 1024 * 1024, gt=0)
    import_multipart_overhead_bytes: int = Field(default=64 * 1024, gt=0)
    import_max_pages: int = Field(default=20, gt=0)
    import_max_extracted_chars: int = Field(default=2_000_000, gt=0)
    import_extraction_timeout_seconds: float = Field(default=15.0, gt=0)
    import_temp_root: Path | None = None
    import_fingerprint_key_path: Path | None = None

    # Origins allowed to call the API from the browser (Vite dev server).
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
_fingerprint_key_lock = Lock()


def load_or_create_import_fingerprint_key(
    configured_path: Path | None = None,
) -> bytes:
    """Load stable local HMAC key material, creating it with owner-only mode."""

    path = configured_path or settings.import_fingerprint_key_path
    if path is None:
        path = settings.database_path.parent / ".import-fingerprint.key"
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _fingerprint_key_lock:
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_BINARY", 0),
                0o600,
            )
        except FileExistsError:
            pass
        else:
            try:
                remaining = memoryview(secrets.token_bytes(32))
                while remaining:
                    remaining = remaining[os.write(descriptor, remaining) :]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            try:
                path.chmod(0o600)
            except OSError:
                # Windows ACLs are authoritative; the file remains under local data.
                pass
        key = path.read_bytes()
        # A second local process can observe an exclusively-created file just
        # before its first writer completes. Wait briefly for the fixed payload.
        for _ in range(100):
            if len(key) >= 32:
                break
            time.sleep(0.01)
            key = path.read_bytes()
    if len(key) < 32:
        raise RuntimeError("import fingerprint key must contain at least 32 bytes")
    return key
