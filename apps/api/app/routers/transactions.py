"""Typed profile-isolated transaction, split, tag, and bulk endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import (
    SplitRead,
    TagRead,
    TransactionBulkAction,
    TransactionBulkCategorize,
    TransactionBulkResult,
    TransactionCreate,
    TransactionDeletedRead,
    TransactionDetailRead,
    TransactionRead,
    TransactionSplitsReplace,
    TransactionTagsReplace,
    TransactionType,
    TransactionUpdate,
)
from app.services import (
    create_transaction,
    list_transaction_splits,
    list_transaction_tags,
    list_transactions,
    replace_transaction_splits,
    replace_transaction_tags,
    require_category,
    require_transaction,
    restore_transaction,
    soft_delete_transaction,
    update_transaction,
)

router = APIRouter(prefix="/profiles/{profile_id}/transactions", tags=["transactions"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def post_transaction(
    profile_id: int,
    values: TransactionCreate,
    session: SessionDependency,
):
    """Create a manual or imported transaction under the path profile."""

    return create_transaction(session, profile_id, values)


@router.get("", response_model=list[TransactionRead])
def get_transactions(
    profile_id: int,
    session: SessionDependency,
    account_id: Annotated[int | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
    transaction_type: Annotated[TransactionType | None, Query(alias="type")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    included_in_spending: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=500)] = None,
    include_deleted: Annotated[bool, Query()] = False,
):
    """List transactions within one profile using composable ledger filters."""

    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be on or before date_to",
        )
    return list_transactions(
        session,
        profile_id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
        included_in_spending=included_in_spending,
        search=search,
        include_deleted=include_deleted,
    )


# Keep this static route before /{transaction_id}; otherwise "bulk" can be
# consumed by the dynamic path and fail integer parsing before reaching here.
@router.patch("/bulk", response_model=TransactionBulkResult)
def patch_transactions_bulk(
    profile_id: int,
    values: TransactionBulkAction,
    session: SessionDependency,
) -> TransactionBulkResult:
    """Atomically categorize or change spending inclusion for many rows."""

    # Preflight every addressed ID before the first mutation. If later domain
    # validation fails, the request-owned session transaction rolls back all
    # prior flushes, so callers never observe a partial bulk edit.
    for transaction_id in values.transaction_ids:
        require_transaction(session, profile_id, transaction_id)

    updated = []
    if isinstance(values, TransactionBulkCategorize):
        if values.category_id is not None:
            require_category(session, profile_id, values.category_id)
        update = TransactionUpdate(
            category_id=values.category_id,
            categorization_status=(
                "manual" if values.category_id is not None else "uncategorized"
            ),
        )
        for transaction_id in values.transaction_ids:
            updated.append(
                update_transaction(session, profile_id, transaction_id, update)
            )
    else:
        update = TransactionUpdate(
            included_in_spending=values.included_in_spending,
            exclusion_reason=(
                None if values.included_in_spending else values.exclusion_reason
            ),
        )
        for transaction_id in values.transaction_ids:
            updated.append(
                update_transaction(session, profile_id, transaction_id, update)
            )

    return TransactionBulkResult(
        updated_count=len(updated),
        transactions=[TransactionRead.model_validate(item) for item in updated],
    )


@router.get("/{transaction_id}", response_model=TransactionDetailRead)
def get_transaction_route(
    profile_id: int,
    transaction_id: int,
    session: SessionDependency,
) -> TransactionDetailRead:
    """Get a transaction and its split/tag detail within the owning profile."""

    transaction = require_transaction(session, profile_id, transaction_id)
    return _transaction_detail(session, profile_id, transaction_id, transaction)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def patch_transaction(
    profile_id: int,
    transaction_id: int,
    values: TransactionUpdate,
    session: SessionDependency,
):
    """Update mutable fields on a profile-owned transaction."""

    return update_transaction(session, profile_id, transaction_id, values)


@router.delete("/{transaction_id}", response_model=TransactionDeletedRead)
def delete_transaction_route(
    profile_id: int,
    transaction_id: int,
    session: SessionDependency,
) -> TransactionDeletedRead:
    """Soft-delete a transaction while retaining it for restoration."""

    transaction = soft_delete_transaction(session, profile_id, transaction_id)
    return TransactionDeletedRead(id=transaction.id, deleted=True)


@router.post("/{transaction_id}/restore", response_model=TransactionDeletedRead)
def post_transaction_restore(
    profile_id: int,
    transaction_id: int,
    session: SessionDependency,
) -> TransactionDeletedRead:
    """Restore a soft-deleted transaction within the owning profile."""

    transaction = restore_transaction(session, profile_id, transaction_id)
    return TransactionDeletedRead(id=transaction.id, deleted=False)


@router.put("/{transaction_id}/splits", response_model=list[SplitRead])
def put_transaction_splits(
    profile_id: int,
    transaction_id: int,
    values: TransactionSplitsReplace,
    session: SessionDependency,
):
    """Replace or clear exact-cent category allocations for one transaction."""

    return replace_transaction_splits(
        session,
        profile_id,
        transaction_id,
        values.splits,
    )


@router.put("/{transaction_id}/tags", response_model=list[TagRead])
def put_transaction_tags(
    profile_id: int,
    transaction_id: int,
    values: TransactionTagsReplace,
    session: SessionDependency,
):
    """Replace or clear reusable profile-owned tags for one transaction."""

    return replace_transaction_tags(
        session,
        profile_id,
        transaction_id,
        [tag.name for tag in values.tags],
    )


def _transaction_detail(
    session: Session,
    profile_id: int,
    transaction_id: int,
    transaction,
) -> TransactionDetailRead:
    base = TransactionRead.model_validate(transaction).model_dump()
    return TransactionDetailRead(
        **base,
        splits=list_transaction_splits(session, profile_id, transaction_id),
        tags=list_transaction_tags(session, profile_id, transaction_id),
    )
