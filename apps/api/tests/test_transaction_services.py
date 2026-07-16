"""BE-10 transaction service behavior and isolation tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory
from app.models import Base
from app.schemas import (
    AccountCreate,
    ProfileCreate,
    SplitInput,
    TransactionCreate,
    TransactionUpdate,
)
from app.services import (
    InvalidUpdateError,
    ResourceNotFoundError,
    SplitSumError,
    add_transaction_tag,
    create_account,
    create_profile,
    create_transaction,
    list_categories,
    list_transaction_splits,
    list_transaction_tags,
    list_transactions,
    remove_transaction_tag,
    replace_transaction_splits,
    replace_transaction_tags,
    restore_transaction,
    soft_delete_transaction,
    update_transaction,
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine: Engine = create_db_engine(tmp_path / "transaction-services.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as db:
            yield db
    finally:
        engine.dispose()


def _account(session: Session, profile_id: int, name: str):
    return create_account(
        session,
        profile_id,
        AccountCreate(
            issuer="TD",
            display_name=name,
            color="#0ea5e9",
            last4="4821",
        ),
    )


def _values(
    account_id: int,
    *,
    amount_cents: int = 10000,
    transaction_type: str = "purchase",
    category_id: int | None = None,
    merchant: str = "Loblaws",
    raw_description: str = "LOBLAWS #1042",
    transaction_date: date = date(2026, 7, 10),
    notes: str | None = None,
) -> TransactionCreate:
    return TransactionCreate(
        account_id=account_id,
        date=transaction_date,
        raw_description=raw_description,
        merchant=merchant,
        amount_cents=amount_cents,
        direction="debit" if amount_cents >= 0 else "credit",
        type=transaction_type,
        category_id=category_id,
        notes=notes,
    )


def test_create_applies_policy_and_validates_owned_references(session: Session) -> None:
    owner = create_profile(session, ProfileCreate(name="Owner"))
    other = create_profile(session, ProfileCreate(name="Other"))
    account = _account(session, owner.id, "Owner card")
    other_account = _account(session, other.id, "Other card")
    groceries = next(c for c in list_categories(session, owner.id) if c.slug == "groceries")
    other_category = next(c for c in list_categories(session, other.id) if c.slug == "groceries")

    purchase = create_transaction(
        session,
        owner.id,
        _values(account.id, category_id=groceries.id),
    )
    refund = create_transaction(
        session,
        owner.id,
        _values(
            account.id,
            amount_cents=-2500,
            transaction_type="refund",
            category_id=groceries.id,
        ),
    )

    assert purchase.included_in_spending is True
    assert refund.included_in_spending is False
    savings = next(c for c in list_categories(session, owner.id) if c.slug == "savings")
    excluded_purchase = create_transaction(
        session,
        owner.id,
        _values(account.id, category_id=savings.id),
    )
    assert excluded_purchase.included_in_spending is False

    with pytest.raises(InvalidUpdateError, match="debit.*positive"):
        create_transaction(
            session,
            owner.id,
            TransactionCreate(
                account_id=account.id,
                date=date(2026, 7, 10),
                raw_description="BAD SIGN",
                amount_cents=-100,
                direction="debit",
                type="purchase",
            ),
        )
    with pytest.raises(ResourceNotFoundError, match="account not found"):
        create_transaction(session, owner.id, _values(other_account.id))
    with pytest.raises(ResourceNotFoundError, match="category not found"):
        create_transaction(
            session,
            owner.id,
            _values(account.id, category_id=other_category.id),
        )


def test_list_filters_account_category_type_date_inclusion_and_search(
    session: Session,
) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    card_a = _account(session, profile.id, "Card A")
    card_b = _account(session, profile.id, "Card B")
    categories = {c.slug: c for c in list_categories(session, profile.id)}
    purchase = create_transaction(
        session,
        profile.id,
        _values(card_a.id, category_id=categories["groceries"].id),
        tag_names=["weekly"],
    )
    transfer = create_transaction(
        session,
        profile.id,
        _values(
            card_b.id,
            amount_cents=5000,
            transaction_type="transfer",
            category_id=categories["dining"].id,
            merchant="Card payment",
            raw_description="ONLINE PAYMENT",
            transaction_date=date(2026, 7, 11),
        ),
    )
    split = create_transaction(
        session,
        profile.id,
        _values(
            card_a.id,
            amount_cents=3000,
            merchant="Market",
            raw_description="CITY MARKET",
            transaction_date=date(2026, 7, 12),
            notes="shared household run",
        ),
        splits=[
            SplitInput(category_id=categories["groceries"].id, amount_cents=2000),
            SplitInput(category_id=categories["dining"].id, amount_cents=1000),
        ],
        tag_names=["family"],
    )

    assert list_transactions(session, profile.id, account_id=card_b.id) == [transfer]
    assert list_transactions(
        session, profile.id, category_id=categories["dining"].id
    ) == [split, transfer]
    assert list_transactions(session, profile.id, transaction_type="transfer") == [
        transfer
    ]
    assert list_transactions(
        session,
        profile.id,
        date_from=date(2026, 7, 11),
        date_to=date(2026, 7, 11),
    ) == [transfer]
    assert list_transactions(
        session, profile.id, included_in_spending=False
    ) == [transfer]
    for term in ("loblaws", "LOBLAWS #1042", "weekly"):
        assert list_transactions(session, profile.id, search=term) == [purchase]
    for term in ("household", "family"):
        assert list_transactions(session, profile.id, search=term) == [split]


def test_update_preserves_exact_splits_and_recomputes_default_inclusion(
    session: Session,
) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    account = _account(session, profile.id, "Card")
    categories = {c.slug: c for c in list_categories(session, profile.id)}
    transaction = create_transaction(
        session,
        profile.id,
        _values(account.id, category_id=categories["groceries"].id),
        splits=[
            SplitInput(category_id=categories["groceries"].id, amount_cents=6000),
            SplitInput(category_id=categories["dining"].id, amount_cents=4000),
        ],
    )

    with pytest.raises(SplitSumError):
        update_transaction(
            session,
            profile.id,
            transaction.id,
            TransactionUpdate(amount_cents=9000),
        )
    assert transaction.amount_cents == 10000
    with pytest.raises(InvalidUpdateError, match="credit.*negative"):
        update_transaction(
            session,
            profile.id,
            transaction.id,
            TransactionUpdate(direction="credit"),
        )
    assert transaction.direction == "debit"

    with pytest.raises(InvalidUpdateError, match="included purchases"):
        update_transaction(
            session,
            profile.id,
            transaction.id,
            TransactionUpdate(type="transfer"),
        )

    with pytest.raises(SplitSumError):
        replace_transaction_splits(
            session,
            profile.id,
            transaction.id,
            [
                SplitInput(category_id=categories["groceries"].id, amount_cents=6000),
                SplitInput(category_id=categories["dining"].id, amount_cents=3999),
            ],
        )
    with pytest.raises(InvalidUpdateError, match="at least two"):
        replace_transaction_splits(
            session,
            profile.id,
            transaction.id,
            [SplitInput(category_id=categories["groceries"].id, amount_cents=10000)],
        )
    replacement = replace_transaction_splits(
        session,
        profile.id,
        transaction.id,
        [
            SplitInput(category_id=categories["dining"].id, amount_cents=7500),
            SplitInput(category_id=categories["groceries"].id, amount_cents=2500),
        ],
    )
    assert [(item.category_id, item.amount_cents) for item in replacement] == [
        (categories["dining"].id, 7500),
        (categories["groceries"].id, 2500),
    ]

    replace_transaction_splits(session, profile.id, transaction.id, [])
    updated = update_transaction(
        session,
        profile.id,
        transaction.id,
        TransactionUpdate(type="transfer", raw_description="OWN TRANSFER"),
    )
    assert updated.included_in_spending is False
    assert updated.raw_description == "OWN TRANSFER"
    with pytest.raises(InvalidUpdateError, match="cash advances"):
        update_transaction(
            session,
            profile.id,
            transaction.id,
            TransactionUpdate(included_in_spending=True),
        )
    with pytest.raises(InvalidUpdateError, match="cannot be null"):
        update_transaction(
            session,
            profile.id,
            transaction.id,
            TransactionUpdate(raw_description=None),
        )

    updated = update_transaction(
        session,
        profile.id,
        transaction.id,
        TransactionUpdate(type="cash_advance", included_in_spending=True),
    )
    assert updated.included_in_spending is True
    updated = update_transaction(
        session,
        profile.id,
        transaction.id,
        TransactionUpdate(type="purchase", category_id=categories["savings"].id),
    )
    assert updated.included_in_spending is False


def test_split_and_tag_management_enforces_profile_scope(session: Session) -> None:
    owner = create_profile(session, ProfileCreate(name="Owner"))
    other = create_profile(session, ProfileCreate(name="Other"))
    account = _account(session, owner.id, "Card")
    owner_category = next(
        c for c in list_categories(session, owner.id) if c.slug == "groceries"
    )
    owner_category_2 = next(
        c for c in list_categories(session, owner.id) if c.slug == "dining"
    )
    other_category = next(
        c for c in list_categories(session, other.id) if c.slug == "groceries"
    )
    transaction = create_transaction(session, owner.id, _values(account.id))

    with pytest.raises(ResourceNotFoundError, match="category not found"):
        replace_transaction_splits(
            session,
            owner.id,
            transaction.id,
            [
                SplitInput(category_id=other_category.id, amount_cents=5000),
                SplitInput(category_id=owner_category.id, amount_cents=5000),
            ],
        )
    replace_transaction_splits(
        session,
        owner.id,
        transaction.id,
        [
            SplitInput(category_id=owner_category.id, amount_cents=5000),
            SplitInput(category_id=owner_category_2.id, amount_cents=5000),
        ],
    )
    assert len(list_transaction_splits(session, owner.id, transaction.id)) == 2
    with pytest.raises(InvalidUpdateError, match="parent transaction sign"):
        replace_transaction_splits(
            session,
            owner.id,
            transaction.id,
            [
                SplitInput(category_id=owner_category.id, amount_cents=11000),
                SplitInput(category_id=owner_category_2.id, amount_cents=-1000),
            ],
        )

    tags = replace_transaction_tags(
        session,
        owner.id,
        transaction.id,
        ["travel", "review", "TRAVEL"],
    )
    assert [tag.name for tag in tags] == ["travel", "review"]
    assert add_transaction_tag(session, owner.id, transaction.id, "Travel").id == tags[0].id
    remove_transaction_tag(session, owner.id, transaction.id, tags[1].id)
    assert [tag.name for tag in list_transaction_tags(session, owner.id, transaction.id)] == [
        "travel"
    ]
    with pytest.raises(InvalidUpdateError, match="1 to 60"):
        add_transaction_tag(session, owner.id, transaction.id, "   ")

    for operation in (
        lambda: list_transaction_splits(session, other.id, transaction.id),
        lambda: list_transaction_tags(session, other.id, transaction.id),
        lambda: replace_transaction_tags(session, other.id, transaction.id, ["leak"]),
    ):
        with pytest.raises(ResourceNotFoundError, match="transaction not found"):
            operation()


def test_soft_delete_restore_and_cross_profile_not_found_are_uniform(
    session: Session,
) -> None:
    owner = create_profile(session, ProfileCreate(name="Owner"))
    other = create_profile(session, ProfileCreate(name="Other"))
    account = _account(session, owner.id, "Card")
    transaction = create_transaction(session, owner.id, _values(account.id))

    deleted = soft_delete_transaction(session, owner.id, transaction.id)
    assert deleted.deleted_at is not None
    assert list_transactions(session, owner.id) == []
    assert list_transactions(session, owner.id, include_deleted=True) == [transaction]
    restored = restore_transaction(session, owner.id, transaction.id)
    assert restored.deleted_at is None
    assert list_transactions(session, owner.id) == [transaction]

    operations = (
        lambda transaction_id: update_transaction(
            session, other.id, transaction_id, TransactionUpdate(notes="leak")
        ),
        lambda transaction_id: soft_delete_transaction(
            session, other.id, transaction_id
        ),
        lambda transaction_id: restore_transaction(session, other.id, transaction_id),
    )
    for operation in operations:
        with pytest.raises(ResourceNotFoundError) as wrong_owner:
            operation(transaction.id)
        with pytest.raises(ResourceNotFoundError) as missing:
            operation(999999)
        assert str(wrong_owner.value) == str(missing.value) == "transaction not found"


def test_services_flush_without_commit_or_rollback(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    account = _account(session, profile.id, "Card")

    with patch.object(session, "commit", wraps=session.commit) as commit, patch.object(
        session, "rollback", wraps=session.rollback
    ) as rollback:
        transaction = create_transaction(session, profile.id, _values(account.id))
        update_transaction(
            session,
            profile.id,
            transaction.id,
            TransactionUpdate(notes="updated"),
        )
        soft_delete_transaction(session, profile.id, transaction.id)
        restore_transaction(session, profile.id, transaction.id)

    commit.assert_not_called()
    rollback.assert_not_called()
