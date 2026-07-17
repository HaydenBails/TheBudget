"""Typed profile-isolated monthly budget endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import BudgetCreate, BudgetRead, BudgetUpdate
from app.services import (
    create_budget,
    delete_budget,
    list_budgets,
    require_budget,
    update_budget,
)

router = APIRouter(prefix="/profiles/{profile_id}/budgets", tags=["budgets"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def post_budget(profile_id: int, values: BudgetCreate, session: SessionDependency):
    """Set an overall or category budget for a month under the path profile."""

    return create_budget(session, profile_id, values)


@router.get("", response_model=list[BudgetRead])
def get_budgets(
    profile_id: int,
    session: SessionDependency,
    period_month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
):
    """List budgets in one profile scope, optionally filtered to one month."""

    return list_budgets(session, profile_id, period_month=period_month)


@router.get("/{budget_id}", response_model=BudgetRead)
def get_budget_route(profile_id: int, budget_id: int, session: SessionDependency):
    """Get a budget only within its owning profile."""

    return require_budget(session, profile_id, budget_id)


@router.patch("/{budget_id}", response_model=BudgetRead)
def patch_budget(
    profile_id: int,
    budget_id: int,
    values: BudgetUpdate,
    session: SessionDependency,
):
    """Update a budget's limit only within its owning profile."""

    return update_budget(session, profile_id, budget_id, values)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_route(profile_id: int, budget_id: int, session: SessionDependency):
    """Remove a budget target only within its owning profile."""

    delete_budget(session, profile_id, budget_id)
