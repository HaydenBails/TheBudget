"""Reversible migration coverage for import persistence."""

from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from alembic.config import Config
from app.config import settings
from app.db import create_db_engine


def test_0006_upgrade_downgrade_preserves_existing_transaction_children(
    monkeypatch, tmp_path: Path
) -> None:
    database_path = tmp_path / "import-migration.db"
    monkeypatch.setattr(settings, "database_path", database_path)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0005_transaction_transfer_type")
    engine = create_db_engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO profiles "
                    "(id, name, base_currency, is_archived) "
                    "VALUES (1, 'P', 'CAD', 0)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO accounts "
                    "(id, profile_id, issuer, display_name, color, currency, "
                    "is_archived) VALUES "
                    "(1, 1, 'TD', 'Visa', '#12805c', 'CAD', 0)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO categories "
                    "(id, profile_id, slug, name, color, icon, "
                    "excluded_from_spending, is_default, sort_order, is_archived) "
                    "VALUES (1, 1, 'food', 'Food', '#12805c', 'food', 0, 0, 1, 0)"
                )
            )
            connection.execute(
                text("INSERT INTO tags (id, profile_id, name) VALUES (1, 1, 'Work')")
            )
            connection.execute(
                text(
                    "INSERT INTO transactions "
                    "(id, profile_id, account_id, category_id, date, "
                    "raw_description, merchant, amount_cents, currency, direction, "
                    "type, categorization_status, included_in_spending, source) "
                    "VALUES (1, 1, 1, 1, '2026-07-01', 'Lunch', 'Cafe', 1200, "
                    "'CAD', 'debit', 'transfer', 'manual', 0, 'manual')"
                )
            )
            connection.execute(text("UPDATE transactions SET import_id = 77 WHERE id = 1"))
            connection.execute(
                text(
                    "INSERT INTO transaction_splits "
                    "(id, transaction_id, category_id, amount_cents, created_at, updated_at) "
                    "VALUES (7, 1, 1, 1200, "
                    "'2026-07-01 12:34:56', '2026-07-02 01:02:03')"
                )
            )
            connection.execute(
                text("INSERT INTO transaction_tags (transaction_id, tag_id) VALUES (1, 1)")
            )
    finally:
        engine.dispose()

    command.upgrade(config, "0006_import_persistence")
    # A retry after the original legacy-import failure mode is harmless once
    # the valid 0005 placeholder has been normalized.
    command.upgrade(config, "0006_import_persistence")
    engine = create_db_engine(database_path)
    try:
        inspector = inspect(engine)
        assert {
            "import_batches",
            "import_staged_transactions",
            "import_warnings",
            "import_transaction_links",
        } <= set(inspector.get_table_names())
        assert {"source_row_reference", "transaction_fingerprint", "exchange_rate"} <= {
            column["name"] for column in inspector.get_columns("transactions")
        }
        transaction_foreign_keys = {
            tuple(foreign_key["constrained_columns"])
            for foreign_key in inspector.get_foreign_keys("transactions")
        }
        assert ("profile_id", "account_id") in transaction_foreign_keys
        assert ("profile_id", "import_id", "account_id") in transaction_foreign_keys
        staged_foreign_keys = {
            tuple(foreign_key["constrained_columns"])
            for foreign_key in inspector.get_foreign_keys("import_staged_transactions")
        }
        assert ("profile_id", "import_batch_id", "account_id") in staged_foreign_keys
        link_foreign_keys = {
            tuple(foreign_key["constrained_columns"])
            for foreign_key in inspector.get_foreign_keys("import_transaction_links")
        }
        assert ("profile_id", "import_batch_id", "account_id") in link_foreign_keys
        assert (
            "profile_id",
            "import_batch_id",
            "account_id",
            "staged_transaction_id",
        ) in link_foreign_keys
        assert ("profile_id", "account_id", "transaction_id") in link_foreign_keys
        transaction_indexes = {
            index["name"]: index for index in inspector.get_indexes("transactions")
        }
        assert "ux_transactions_profile_account_id" in transaction_indexes
        fingerprint_index = transaction_indexes[
            "ux_transactions_profile_account_fingerprint"
        ]
        assert bool(fingerprint_index["unique"]) is True
        assert "transaction_fingerprint IS NOT NULL" in str(
            fingerprint_index["dialect_options"]["sqlite_where"]
        )
        batch_unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("import_batches")
        }
        assert ("profile_id", "id", "account_id") in batch_unique_constraints
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT import_id FROM transactions WHERE id = 1")) is None
            )
            assert connection.execute(
                text(
                    "SELECT id, transaction_id, category_id, amount_cents, "
                    "created_at, updated_at FROM transaction_splits"
                )
            ).one() == (7, 1, 1, 1200, "2026-07-01 12:34:56", "2026-07-02 01:02:03")
            assert connection.execute(
                text("SELECT transaction_id, tag_id FROM transaction_tags")
            ).one() == (1, 1)
    finally:
        engine.dispose()

    command.downgrade(config, "0005_transaction_transfer_type")
    engine = create_db_engine(database_path)
    try:
        inspector = inspect(engine)
        assert "import_batches" not in inspector.get_table_names()
        assert "transaction_fingerprint" not in {
            column["name"] for column in inspector.get_columns("transactions")
        }
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT type FROM transactions WHERE id = 1")) == "transfer"
            )
            assert (
                connection.scalar(text("SELECT import_id FROM transactions WHERE id = 1")) is None
            )
            assert connection.execute(
                text(
                    "SELECT id, transaction_id, category_id, amount_cents, "
                    "created_at, updated_at FROM transaction_splits"
                )
            ).one() == (7, 1, 1, 1200, "2026-07-01 12:34:56", "2026-07-02 01:02:03")
            assert connection.execute(
                text("SELECT transaction_id, tag_id FROM transaction_tags")
            ).one() == (1, 1)
    finally:
        engine.dispose()


def test_0006_database_rejects_cross_profile_transaction_account(
    monkeypatch, tmp_path: Path
) -> None:
    database_path = tmp_path / "transaction-ownership.db"
    monkeypatch.setattr(settings, "database_path", database_path)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0006_import_persistence")
    engine = create_db_engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO profiles (id, name, base_currency, is_archived) "
                    "VALUES (1, 'First', 'CAD', 0), (2, 'Second', 'CAD', 0)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO accounts "
                    "(id, profile_id, issuer, display_name, color, currency, is_archived) "
                    "VALUES (2, 2, 'TD', 'Other', '#12805c', 'CAD', 0)"
                )
            )
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                connection.execute(
                    text(
                        "INSERT INTO transactions "
                        "(profile_id, account_id, date, raw_description, merchant, "
                        "amount_cents, currency, direction, type, categorization_status, "
                        "included_in_spending, source) VALUES "
                        "(1, 2, '2026-07-01', 'Bad owner', '', 100, 'CAD', 'debit', "
                        "'purchase', 'manual', 1, 'manual')"
                    )
                )
    finally:
        engine.dispose()


def test_0006_failed_preflight_leaves_no_partial_ddl_and_retry_succeeds(
    monkeypatch, tmp_path: Path
) -> None:
    database_path = tmp_path / "migration-retry.db"
    monkeypatch.setattr(settings, "database_path", database_path)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0005_transaction_transfer_type")
    engine = create_db_engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO profiles (id, name, base_currency, is_archived) "
                    "VALUES (1, 'First', 'CAD', 0), (2, 'Second', 'CAD', 0)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO accounts "
                    "(id, profile_id, issuer, display_name, color, currency, is_archived) "
                    "VALUES (2, 2, 'TD', 'Other', '#12805c', 'CAD', 0)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO transactions "
                    "(id, profile_id, account_id, date, raw_description, merchant, "
                    "amount_cents, currency, direction, type, categorization_status, "
                    "included_in_spending, source, import_id) VALUES "
                    "(1, 1, 2, '2026-07-01', 'Legacy', '', 100, 'CAD', 'debit', "
                    "'purchase', 'manual', 1, 'manual', 77)"
                )
            )
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="account to belong to its profile"):
        command.upgrade(config, "0006_import_persistence")
    engine = create_db_engine(database_path)
    try:
        inspector = inspect(engine)
        assert "import_batches" not in inspector.get_table_names()
        assert "ux_accounts_profile_id_id" not in {
            index["name"] for index in inspector.get_indexes("accounts")
        }
        assert "transaction_fingerprint" not in {
            column["name"] for column in inspector.get_columns("transactions")
        }
        with engine.begin() as connection:
            connection.execute(text("UPDATE transactions SET profile_id = 2 WHERE id = 1"))
    finally:
        engine.dispose()

    command.upgrade(config, "0006_import_persistence")
    engine = create_db_engine(database_path)
    try:
        assert "import_batches" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT import_id FROM transactions WHERE id = 1")) is None
            )
    finally:
        engine.dispose()
