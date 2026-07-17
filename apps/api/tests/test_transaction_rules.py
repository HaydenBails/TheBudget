"""Domain-rule tests (split-sum, default inclusion) and ORM persistence."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory
from app.models import Base, Transaction, TransactionSplit
from app.schemas import AccountCreate, ProfileCreate
from app.services import (
    SplitSumError,
    create_account,
    create_profile,
    default_included_for_type,
    list_categories,
    validate_splits_sum,
    validate_transaction_sign,
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine: Engine = create_db_engine(tmp_path / "txns.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as db:
            yield db
    finally:
        engine.dispose()


def test_default_inclusion_policy() -> None:
    # Purchases (positive) and refunds (negative) net into spending.
    assert default_included_for_type("purchase") is True
    assert default_included_for_type("refund") is True
    for excluded in (
        "payment",
        "transfer",
        "cash_advance",
        "fee",
        "interest",
        "income",
        "unknown",
    ):
        assert default_included_for_type(excluded) is False


def test_validate_splits_sum_exact_and_mismatch() -> None:
    validate_splits_sum(10000, [6000, 4000])  # ok, returns None
    with pytest.raises(SplitSumError):
        validate_splits_sum(10000, [6000, 3000])


@pytest.mark.parametrize(
    ("amount_cents", "direction"),
    [(0, "debit"), (-1, "debit"), (1, "credit")],
)
def test_transaction_sign_validation_rejects_mismatches(
    amount_cents: int,
    direction: str,
) -> None:
    with pytest.raises(ValueError):
        validate_transaction_sign(amount_cents, direction)

    validate_transaction_sign(1, "debit")
    validate_transaction_sign(-1, "credit")


def test_transaction_persists_with_splits(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    account = create_account(
        session,
        profile.id,
        AccountCreate(issuer="TD", display_name="Visa", color="#4f6bff", last4="4821"),
    )
    cats = list_categories(session, profile.id)
    groceries = next(c for c in cats if c.slug == "groceries")
    dining = next(c for c in cats if c.slug == "dining")

    txn = Transaction(
        profile_id=profile.id,
        account_id=account.id,
        category_id=groceries.id,
        date=date(2026, 7, 14),
        raw_description="LOBLAWS #1042",
        merchant="Loblaws",
        amount_cents=10000,
        direction="debit",
        type="purchase",
        included_in_spending=True,
    )
    txn.splits = [
        TransactionSplit(category_id=groceries.id, amount_cents=6000),
        TransactionSplit(category_id=dining.id, amount_cents=4000),
    ]
    session.add(txn)
    session.flush()

    stored = session.scalar(select(Transaction).where(Transaction.id == txn.id))
    assert stored is not None
    assert stored.deleted_at is None
    assert len(stored.splits) == 2
    validate_splits_sum(stored.amount_cents, [s.amount_cents for s in stored.splits])
