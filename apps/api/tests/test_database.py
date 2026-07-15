"""Tests for isolated SQLite engine and session configuration."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.config import Settings
from app.db import create_db_engine, create_session_factory


def test_database_path_can_be_configured(monkeypatch, tmp_path: Path) -> None:
    configured_path = tmp_path / "configured" / "tracker.db"
    monkeypatch.setenv("ST_DATABASE_PATH", str(configured_path))

    configured_settings = Settings(_env_file=None)

    assert configured_settings.database_path == configured_path


def test_engine_enables_wal_and_foreign_keys(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "nested" / "tracker.db")
    try:
        with engine.connect() as connection:
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

        assert journal_mode == "wal"
        assert foreign_keys == 1
    finally:
        engine.dispose()


def test_session_factory_uses_isolated_database(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "sessions.db")
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
            assert session.bind is engine
    finally:
        engine.dispose()
