"""Persistence tests for profile and account ownership semantics."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, select, text

from app.db import create_db_engine, create_session_factory
from app.models import Account, Base, Profile


def test_profile_account_persistence_and_timestamps(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "models.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory.begin() as session:
            profile = Profile(name="Personal")
            account = Account(
                profile=profile,
                issuer="AMEX",
                display_name="Cobalt",
                color="#2f6fed",
                last4="71007",
            )
            session.add(profile)

        assert profile.id > 0
        assert account.id > 0
        assert account.profile_id == profile.id
        assert profile.base_currency == "CAD"
        assert account.currency == "CAD"
        assert profile.created_at is not None
        assert profile.updated_at is not None
        assert account.created_at is not None
        assert account.updated_at is not None
    finally:
        engine.dispose()


def test_account_foreign_key_is_required_and_cascades_on_delete(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "cascade.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        foreign_key = inspect(engine).get_foreign_keys("accounts")[0]
        assert foreign_key["referred_table"] == "profiles"
        assert foreign_key["options"]["ondelete"] == "CASCADE"
        assert inspect(engine).get_columns("accounts")[1]["nullable"] is False

        with session_factory.begin() as session:
            profile = Profile(name="Profile")
            profile.accounts.append(
                Account(
                    issuer="TD",
                    display_name="Cash Back",
                    color="#12805c",
                    last4="4821",
                )
            )
            session.add(profile)

        with engine.begin() as connection:
            connection.execute(text("DELETE FROM profiles WHERE id = :id"), {"id": profile.id})

        with session_factory() as session:
            assert session.scalar(select(Account).where(Account.profile_id == profile.id)) is None
    finally:
        engine.dispose()
