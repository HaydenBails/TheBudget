"""Alembic lifecycle test for the profile/account revision."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from alembic import command
from alembic.config import Config
from app.config import settings
from app.db import create_db_engine


def test_profile_account_migration_upgrade_downgrade_cycle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "migration.db"
    monkeypatch.setattr(settings, "database_path", database_path)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    command.upgrade(config, "head")
    engine = create_db_engine(database_path)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "accounts",
            "alembic_version",
            "budgets",
            "categories",
            "import_batches",
            "import_staged_transactions",
            "import_transaction_links",
            "import_warnings",
            "profiles",
            "tags",
            "transaction_splits",
            "transaction_tags",
            "transactions",
        }
    finally:
        engine.dispose()

    command.downgrade(config, "0001_migration_baseline")
    engine = create_db_engine(database_path)
    try:
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_db_engine(database_path)
    try:
        assert {"profiles", "accounts"}.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
