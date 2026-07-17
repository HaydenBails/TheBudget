"""Typed profile-isolated income-schedule endpoints (product plan §10)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import (
    IncomeOccurrenceRead,
    IncomeScheduleCreate,
    IncomeScheduleRead,
    IncomeScheduleUpdate,
    IncomeSummaryRead,
)
from app.services import (
    create_income_schedule,
    delete_income_schedule,
    forecast_occurrences,
    income_summary,
    list_income_schedules,
    require_income_schedule,
    update_income_schedule,
)

router = APIRouter(prefix="/profiles/{profile_id}/income", tags=["income"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=IncomeScheduleRead, status_code=status.HTTP_201_CREATED)
def post_income_schedule(
    profile_id: int, values: IncomeScheduleCreate, session: SessionDependency
):
    """Create an income schedule owned by the path profile."""

    return create_income_schedule(session, profile_id, values)


@router.get("", response_model=list[IncomeScheduleRead])
def get_income_schedules(profile_id: int, session: SessionDependency):
    """List income schedules for one profile (active first)."""

    return list_income_schedules(session, profile_id)


@router.get("/occurrences", response_model=list[IncomeOccurrenceRead])
def get_income_occurrences(
    profile_id: int,
    session: SessionDependency,
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
):
    """Return forecast income occurrences within an inclusive date range."""

    return forecast_occurrences(session, profile_id, date_from, date_to)


@router.get("/summary", response_model=IncomeSummaryRead)
def get_income_summary(
    profile_id: int,
    session: SessionDependency,
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
):
    """Return expected and still-due income for a period (§11.2)."""

    return income_summary(session, profile_id, date_from, date_to)


@router.get("/{schedule_id}", response_model=IncomeScheduleRead)
def get_income_schedule_route(profile_id: int, schedule_id: int, session: SessionDependency):
    """Get one income schedule within its owning profile."""

    return require_income_schedule(session, profile_id, schedule_id)


@router.patch("/{schedule_id}", response_model=IncomeScheduleRead)
def patch_income_schedule(
    profile_id: int,
    schedule_id: int,
    values: IncomeScheduleUpdate,
    session: SessionDependency,
):
    """Update an income schedule only within its owning profile."""

    return update_income_schedule(session, profile_id, schedule_id, values)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income_schedule_route(profile_id: int, schedule_id: int, session: SessionDependency):
    """Remove an income schedule only within its owning profile."""

    delete_income_schedule(session, profile_id, schedule_id)
