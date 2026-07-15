"""Typed profile lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import ProfileCreate, ProfileRead, ProfileUpdate
from app.services import (
    archive_profile,
    create_profile,
    list_profiles,
    require_profile,
    restore_profile,
    update_profile,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def post_profile(values: ProfileCreate, session: SessionDependency):
    """Create a local profile."""

    return create_profile(session, values)


@router.get("", response_model=list[ProfileRead])
def get_profiles(
    session: SessionDependency,
    include_archived: Annotated[bool, Query()] = False,
):
    """List profiles, hiding archived profiles unless explicitly requested."""

    return list_profiles(session, include_archived=include_archived)


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: int, session: SessionDependency):
    """Get one profile, including an archived profile."""

    return require_profile(session, profile_id)


@router.patch("/{profile_id}", response_model=ProfileRead)
def patch_profile(
    profile_id: int,
    values: ProfileUpdate,
    session: SessionDependency,
):
    """Update mutable profile fields."""

    return update_profile(session, profile_id, values)


@router.post("/{profile_id}/archive", response_model=ProfileRead)
def post_profile_archive(profile_id: int, session: SessionDependency):
    """Archive a profile without deleting its data."""

    return archive_profile(session, profile_id)


@router.post("/{profile_id}/restore", response_model=ProfileRead)
def post_profile_restore(profile_id: int, session: SessionDependency):
    """Restore an archived profile."""

    return restore_profile(session, profile_id)
