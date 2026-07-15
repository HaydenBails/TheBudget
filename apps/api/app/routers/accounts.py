"""Typed profile-isolated account lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import AccountCreate, AccountRead, AccountUpdate
from app.services import (
    archive_account,
    create_account,
    list_accounts,
    require_account,
    restore_account,
    update_account,
)

router = APIRouter(prefix="/profiles/{profile_id}/accounts", tags=["accounts"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def post_account(
    profile_id: int,
    values: AccountCreate,
    session: SessionDependency,
):
    """Create an account owned by the path profile."""

    return create_account(session, profile_id, values)


@router.get("", response_model=list[AccountRead])
def get_accounts(
    profile_id: int,
    session: SessionDependency,
    include_archived: Annotated[bool, Query()] = False,
):
    """List accounts within one explicit profile scope."""

    return list_accounts(session, profile_id, include_archived=include_archived)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(profile_id: int, account_id: int, session: SessionDependency):
    """Get an account only within its owning profile."""

    return require_account(session, profile_id, account_id)


@router.patch("/{account_id}", response_model=AccountRead)
def patch_account(
    profile_id: int,
    account_id: int,
    values: AccountUpdate,
    session: SessionDependency,
):
    """Update an account only within its owning profile."""

    return update_account(session, profile_id, account_id, values)


@router.post("/{account_id}/archive", response_model=AccountRead)
def post_account_archive(
    profile_id: int,
    account_id: int,
    session: SessionDependency,
):
    """Archive a scoped account without deleting its history."""

    return archive_account(session, profile_id, account_id)


@router.post("/{account_id}/restore", response_model=AccountRead)
def post_account_restore(
    profile_id: int,
    account_id: int,
    session: SessionDependency,
):
    """Restore an archived scoped account."""

    return restore_account(session, profile_id, account_id)
