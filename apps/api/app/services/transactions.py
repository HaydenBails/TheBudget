"""Profile-isolated transaction persistence operations.

Services flush but never commit or roll back. HTTP/import callers own the
transaction boundary. Every resource lookup includes the explicit profile ID,
so missing and cross-profile records have the same public result.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date as _date

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    ImportBatch,
    ImportStagedTransaction,
    Tag,
    Transaction,
    TransactionSplit,
    TransactionTag,
)
from app.models.base import utc_now
from app.schemas import SplitInput, TransactionCreate, TransactionUpdate
from app.services.accounts import require_account
from app.services.categories import require_category
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.profiles import require_profile
from app.services.transactions_rules import (
    default_included_for_type,
    validate_splits_sum,
    validate_transaction_sign,
)

_REQUIRED_UPDATE_FIELDS = frozenset(
    {
        "date",
        "raw_description",
        "merchant",
        "amount_cents",
        "direction",
        "type",
        "categorization_status",
        "included_in_spending",
    }
)


def create_transaction(
    session: Session,
    profile_id: int,
    values: TransactionCreate,
    *,
    splits: Sequence[SplitInput] = (),
    tag_names: Sequence[str] = (),
) -> Transaction:
    """Create a transaction with optional validated splits and tags."""

    require_account(session, profile_id, values.account_id)
    category = None
    if values.category_id is not None:
        category = require_category(session, profile_id, values.category_id)

    validate_transaction_sign(values.amount_cents, values.direction)
    included_in_spending = default_included_for_type(values.type)
    if category is not None and category.excluded_from_spending:
        included_in_spending = False

    split_values = tuple(splits)
    if split_values:
        _validate_split_values(
            session,
            profile_id,
            values.amount_cents,
            values.type,
            included_in_spending,
            split_values,
        )
    normalized_tags = _normalize_tag_names(tag_names)

    transaction = Transaction(
        profile_id=profile_id,
        included_in_spending=included_in_spending,
        **values.model_dump(),
    )
    if split_values:
        transaction.splits = [
            TransactionSplit(**split_value.model_dump())
            for split_value in split_values
        ]
    session.add(transaction)
    session.flush()
    if normalized_tags:
        replace_transaction_tags(
            session,
            profile_id,
            transaction.id,
            normalized_tags,
        )
    return transaction


def create_imported_transaction(
    session: Session,
    profile_id: int,
    import_batch: ImportBatch,
    staged: ImportStagedTransaction,
) -> Transaction:
    """Create one final ledger row from a same-scope canonical staged row."""

    if (
        import_batch.profile_id != profile_id
        or staged.profile_id != profile_id
        or staged.import_batch_id != import_batch.id
        or staged.account_id != import_batch.account_id
    ):
        raise ResourceNotFoundError("staged import transaction not found")
    require_account(session, profile_id, import_batch.account_id)
    validate_transaction_sign(staged.amount_cents, staged.direction)
    transaction = Transaction(
        profile_id=profile_id,
        account_id=import_batch.account_id,
        date=staged.date,
        posted_date=staged.posted_date,
        raw_description=staged.raw_description,
        merchant=staged.merchant,
        amount_cents=staged.amount_cents,
        currency=staged.currency,
        direction=staged.direction,
        type=staged.type,
        categorization_status="uncategorized",
        included_in_spending=staged.included_in_spending,
        exclusion_reason=staged.exclusion_reason,
        source="pdf_import",
        import_id=import_batch.id,
        source_row_reference=staged.source_row_reference,
        transaction_fingerprint=staged.transaction_fingerprint,
        original_foreign_amount_cents=staged.original_foreign_amount_cents,
        original_foreign_currency=staged.original_foreign_currency,
        exchange_rate=staged.exchange_rate,
    )
    session.add(transaction)
    session.flush()
    return transaction


def list_transactions(
    session: Session,
    profile_id: int,
    *,
    account_id: int | None = None,
    category_id: int | None = None,
    transaction_type: str | None = None,
    date_from: _date | None = None,
    date_to: _date | None = None,
    included_in_spending: bool | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> list[Transaction]:
    """List profile-owned transactions with composable ledger filters."""

    require_profile(session, profile_id)
    statement = select(Transaction).where(Transaction.profile_id == profile_id)
    if not include_deleted:
        statement = statement.where(Transaction.deleted_at.is_(None))
    if account_id is not None:
        statement = statement.where(Transaction.account_id == account_id)
    if category_id is not None:
        split_category_match = (
            select(TransactionSplit.id)
            .where(
                TransactionSplit.transaction_id == Transaction.id,
                TransactionSplit.category_id == category_id,
            )
            .exists()
        )
        statement = statement.where(
            or_(Transaction.category_id == category_id, split_category_match)
        )
    if transaction_type is not None:
        statement = statement.where(Transaction.type == transaction_type)
    if date_from is not None:
        statement = statement.where(Transaction.date >= date_from)
    if date_to is not None:
        statement = statement.where(Transaction.date <= date_to)
    if included_in_spending is not None:
        statement = statement.where(
            Transaction.included_in_spending.is_(included_in_spending)
        )
    if search is not None and (needle := search.strip().lower()):
        tag_match = (
            select(TransactionTag.transaction_id)
            .join(Tag, Tag.id == TransactionTag.tag_id)
            .where(
                TransactionTag.transaction_id == Transaction.id,
                func.lower(Tag.name).contains(needle, autoescape=True),
            )
            .exists()
        )
        statement = statement.where(
            or_(
                func.lower(Transaction.merchant).contains(needle, autoescape=True),
                func.lower(Transaction.raw_description).contains(
                    needle, autoescape=True
                ),
                func.lower(Transaction.notes).contains(needle, autoescape=True),
                tag_match,
            )
        )
    statement = statement.order_by(Transaction.date.desc(), Transaction.id.desc())
    return list(session.scalars(statement))


def get_transaction(
    session: Session,
    profile_id: int,
    transaction_id: int,
) -> Transaction | None:
    """Return a transaction only when both its ID and profile owner match."""

    return session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.profile_id == profile_id,
        )
    )


def require_transaction(
    session: Session,
    profile_id: int,
    transaction_id: int,
) -> Transaction:
    """Return a scoped transaction or the uniform not-found error."""

    transaction = get_transaction(session, profile_id, transaction_id)
    if transaction is None:
        raise ResourceNotFoundError("transaction not found")
    return transaction


def update_transaction(
    session: Session,
    profile_id: int,
    transaction_id: int,
    values: TransactionUpdate,
) -> Transaction:
    """Update mutable fields without weakening split or profile invariants."""

    transaction = require_transaction(session, profile_id, transaction_id)
    changes = values.model_dump(exclude_unset=True)
    _reject_null_required_fields(changes)
    category_id = changes.get("category_id", transaction.category_id)
    category = None
    if category_id is not None:
        category = require_category(session, profile_id, int(category_id))

    candidate_amount = int(changes.get("amount_cents", transaction.amount_cents))
    candidate_direction = str(changes.get("direction", transaction.direction))
    candidate_type = str(changes.get("type", transaction.type))
    validate_transaction_sign(candidate_amount, candidate_direction)

    if changes.get("included_in_spending") is True and candidate_type not in {
        "purchase",
        "cash_advance",
        "refund",
    }:
        raise InvalidUpdateError(
            "only purchases, cash advances, and refunds may be explicitly included in spending"
        )
    if "type" in changes and "included_in_spending" not in changes:
        changes["included_in_spending"] = default_included_for_type(candidate_type)
    if category is not None and category.excluded_from_spending:
        changes["included_in_spending"] = False

    candidate_included = bool(
        changes.get("included_in_spending", transaction.included_in_spending)
    )
    if transaction.splits:
        existing_splits = tuple(
            SplitInput(
                category_id=split.category_id,
                amount_cents=split.amount_cents,
            )
            for split in transaction.splits
        )
        _validate_split_values(
            session,
            profile_id,
            candidate_amount,
            candidate_type,
            candidate_included,
            existing_splits,
        )
    for field, value in changes.items():
        setattr(transaction, field, value)
    session.flush()
    return transaction


def list_transaction_splits(
    session: Session,
    profile_id: int,
    transaction_id: int,
) -> list[TransactionSplit]:
    """List splits for a scoped transaction in stable creation order."""

    transaction = require_transaction(session, profile_id, transaction_id)
    return list(
        session.scalars(
            select(TransactionSplit)
            .where(TransactionSplit.transaction_id == transaction.id)
            .order_by(TransactionSplit.id)
        )
    )


def replace_transaction_splits(
    session: Session,
    profile_id: int,
    transaction_id: int,
    splits: Sequence[SplitInput],
) -> list[TransactionSplit]:
    """Replace all splits after validating scope and the exact cent sum."""

    transaction = require_transaction(session, profile_id, transaction_id)
    split_values = tuple(splits)
    if split_values:
        _validate_split_values(
            session,
            profile_id,
            transaction.amount_cents,
            transaction.type,
            transaction.included_in_spending,
            split_values,
        )
    transaction.splits = [
        TransactionSplit(**split_value.model_dump()) for split_value in split_values
    ]
    session.flush()
    return list(transaction.splits)


def list_transaction_tags(
    session: Session,
    profile_id: int,
    transaction_id: int,
) -> list[Tag]:
    """List tags attached to a scoped transaction."""

    transaction = require_transaction(session, profile_id, transaction_id)
    return list(
        session.scalars(
            select(Tag)
            .join(TransactionTag, TransactionTag.tag_id == Tag.id)
            .where(TransactionTag.transaction_id == transaction.id)
            .order_by(func.lower(Tag.name), Tag.id)
        )
    )


def replace_transaction_tags(
    session: Session,
    profile_id: int,
    transaction_id: int,
    tag_names: Iterable[str],
) -> list[Tag]:
    """Replace a transaction's tags, reusing profile-owned tag records."""

    transaction = require_transaction(session, profile_id, transaction_id)
    names = _normalize_tag_names(tag_names)
    tags_by_key = {
        tag.name.casefold(): tag
        for tag in session.scalars(
            select(Tag).where(Tag.profile_id == profile_id)
        )
    }
    tags: list[Tag] = []
    for name in names:
        tag = tags_by_key.get(name.casefold())
        if tag is None:
            tag = Tag(profile_id=profile_id, name=name)
            session.add(tag)
            session.flush()
            tags_by_key[name.casefold()] = tag
        tags.append(tag)

    session.execute(
        delete(TransactionTag).where(
            TransactionTag.transaction_id == transaction.id
        )
    )
    session.add_all(
        TransactionTag(transaction_id=transaction.id, tag_id=tag.id) for tag in tags
    )
    session.flush()
    return tags


def add_transaction_tag(
    session: Session,
    profile_id: int,
    transaction_id: int,
    name: str,
) -> Tag:
    """Attach one named profile tag, creating it when necessary."""

    existing = list_transaction_tags(session, profile_id, transaction_id)
    names = [tag.name for tag in existing]
    normalized = _normalize_tag_names([name])[0]
    if normalized.casefold() in {name.casefold() for name in names}:
        return next(
            tag for tag in existing if tag.name.casefold() == normalized.casefold()
        )
    return replace_transaction_tags(
        session,
        profile_id,
        transaction_id,
        [*names, normalized],
    )[-1]


def remove_transaction_tag(
    session: Session,
    profile_id: int,
    transaction_id: int,
    tag_id: int,
) -> Transaction:
    """Detach a profile-owned tag without deleting the reusable tag record."""

    transaction = require_transaction(session, profile_id, transaction_id)
    tag = session.scalar(
        select(Tag).where(Tag.id == tag_id, Tag.profile_id == profile_id)
    )
    if tag is None:
        raise ResourceNotFoundError("tag not found")
    session.execute(
        delete(TransactionTag).where(
            TransactionTag.transaction_id == transaction.id,
            TransactionTag.tag_id == tag.id,
        )
    )
    session.flush()
    return transaction


def soft_delete_transaction(
    session: Session,
    profile_id: int,
    transaction_id: int,
) -> Transaction:
    """Soft-delete a scoped transaction while retaining its full history."""

    transaction = require_transaction(session, profile_id, transaction_id)
    if transaction.deleted_at is None:
        transaction.deleted_at = utc_now()
        session.flush()
    return transaction


def restore_transaction(
    session: Session,
    profile_id: int,
    transaction_id: int,
) -> Transaction:
    """Restore a soft-deleted transaction within its owning profile."""

    transaction = require_transaction(session, profile_id, transaction_id)
    if transaction.deleted_at is not None:
        transaction.deleted_at = None
        session.flush()
    return transaction


def _validate_split_values(
    session: Session,
    profile_id: int,
    parent_amount_cents: int,
    parent_type: str,
    parent_included: bool,
    splits: Sequence[SplitInput],
) -> None:
    if parent_type != "purchase" or not parent_included:
        raise InvalidUpdateError("only included purchases may be split")
    if len(splits) < 2:
        raise InvalidUpdateError(
            "split transactions require at least two category allocations"
        )
    for split in splits:
        require_category(session, profile_id, split.category_id)
        if split.amount_cents == 0 or (split.amount_cents > 0) != (
            parent_amount_cents > 0
        ):
            raise InvalidUpdateError(
                "split amounts must be nonzero and use the parent transaction sign"
            )
    validate_splits_sum(
        parent_amount_cents,
        (split.amount_cents for split in splits),
    )


def _normalize_tag_names(tag_names: Iterable[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in tag_names:
        name = raw_name.strip()
        if not name or len(name) > 60:
            raise InvalidUpdateError("tag names must contain 1 to 60 characters")
        key = name.casefold()
        if key not in seen:
            names.append(name)
            seen.add(key)
    return names


def _reject_null_required_fields(changes: dict[str, object]) -> None:
    null_fields = sorted(
        field for field in _REQUIRED_UPDATE_FIELDS if changes.get(field, object()) is None
    )
    if null_fields:
        joined = ", ".join(null_fields)
        raise InvalidUpdateError(f"required fields cannot be null: {joined}")
