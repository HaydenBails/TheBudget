"""Typed profile-isolated category lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import (
    archive_category,
    create_category,
    list_categories,
    require_category,
    restore_category,
    update_category,
)

router = APIRouter(prefix="/profiles/{profile_id}/categories", tags=["categories"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def post_category(
    profile_id: int,
    values: CategoryCreate,
    session: SessionDependency,
):
    """Create a custom category owned by the path profile."""

    return create_category(session, profile_id, values)


@router.get("", response_model=list[CategoryRead])
def get_categories(
    profile_id: int,
    session: SessionDependency,
    include_archived: Annotated[bool, Query()] = False,
):
    """List categories within one explicit profile scope, in display order."""

    return list_categories(session, profile_id, include_archived=include_archived)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category_route(profile_id: int, category_id: int, session: SessionDependency):
    """Get a category only within its owning profile."""

    return require_category(session, profile_id, category_id)


@router.patch("/{category_id}", response_model=CategoryRead)
def patch_category(
    profile_id: int,
    category_id: int,
    values: CategoryUpdate,
    session: SessionDependency,
):
    """Update a category only within its owning profile."""

    return update_category(session, profile_id, category_id, values)


@router.post("/{category_id}/archive", response_model=CategoryRead)
def post_category_archive(
    profile_id: int,
    category_id: int,
    session: SessionDependency,
):
    """Archive a scoped category while preserving references to it."""

    return archive_category(session, profile_id, category_id)


@router.post("/{category_id}/restore", response_model=CategoryRead)
def post_category_restore(
    profile_id: int,
    category_id: int,
    session: SessionDependency,
):
    """Restore an archived scoped category."""

    return restore_category(session, profile_id, category_id)
