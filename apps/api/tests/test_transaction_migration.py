"""Migration coverage for the corrected transaction-type contract."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import text

from alembic import command
from alembic.config import Config
from app.config import settings
from app.db import create_db_engine, create_session_factory
from app.schemas import AccountCreate, ProfileCreate, TransactionCreate
from app.services import create_account, create_profile, create_transaction


def test_migrated_database_accepts_transfer_transactions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "transaction-transfer.db"
    monkeypatch.setattr(settings, "database_path", database_path)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_db_engine(database_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory.begin() as session:
            profile = create_profile(session, ProfileCreate(name="Personal"))
            account = create_account(
                session,
                profile.id,
                AccountCreate(
                    issuer="TD",
                    display_name="Visa",
                    color="#0ea5e9",
                    last4="4821",
                ),
            )
            transaction = create_transaction(
                session,
                profile.id,
                TransactionCreate(
                    account_id=account.id,
                    date=date(2026, 7, 16),
                    raw_description="TRANSFER",
                    merchant="Own account transfer",
                    amount_cents=25000,
                    direction="debit",
                    type="transfer",
                ),
            )
            assert transaction.type == "transfer"
            assert transaction.included_in_spending is False
            transaction_id = transaction.id
    finally:
        engine.dispose()

    command.downgrade(config, "0004_transaction_models")
    engine = create_db_engine(database_path)
    try:
        with engine.connect() as connection:
            stored_type = connection.scalar(
                text("SELECT type FROM transactions WHERE id = :id"),
                {"id": transaction_id},
            )
        assert stored_type == "payment"
    finally:
        engine.dispose()
