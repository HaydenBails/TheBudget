"""Typed profile-isolated recurring-charge endpoints (product plan §12)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import (
    RecurringDetectResult,
    RecurringSeriesRead,
    RecurringSeriesUpdate,
    RecurringStatus,
)
from app.services import (
    delete_recurring_series,
    detect_and_sync,
    list_recurring_series,
    require_recurring_series,
    update_recurring_series,
)

router = APIRouter(prefix="/profiles/{profile_id}/recurring", tags=["recurring"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/detect", response_model=RecurringDetectResult)
def post_detect(profile_id: int, session: SessionDependency):
    """Run recurring detection, sync series, and re-link matched transactions."""

    created, updated, series = detect_and_sync(session, profile_id)
    return RecurringDetectResult(
        detected=created + updated,
        created=created,
        updated=updated,
        series=[RecurringSeriesRead.model_validate(s) for s in series],
    )


@router.get("", response_model=list[RecurringSeriesRead])
def get_recurring(
    profile_id: int,
    session: SessionDependency,
    status_filter: Annotated[RecurringStatus | None, Query(alias="status")] = None,
):
    """List recurring series for one profile, optionally filtered by status."""

    return list_recurring_series(session, profile_id, status=status_filter)


@router.get("/{series_id}", response_model=RecurringSeriesRead)
def get_recurring_series_route(profile_id: int, series_id: int, session: SessionDependency):
    """Get one recurring series within its owning profile."""

    return require_recurring_series(session, profile_id, series_id)


@router.patch("/{series_id}", response_model=RecurringSeriesRead)
def patch_recurring_series(
    profile_id: int,
    series_id: int,
    values: RecurringSeriesUpdate,
    session: SessionDependency,
):
    """Update a recurring series' status, confirmation, reminder, or name."""

    return update_recurring_series(session, profile_id, series_id, values)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_series_route(profile_id: int, series_id: int, session: SessionDependency):
    """Remove a recurring series and unlink its transactions."""

    delete_recurring_series(session, profile_id, series_id)
