"""Profile-isolated monthly budget persistence.

Services flush but do not commit; the API layer owns transaction boundaries.
A budget with a NULL ``category_id`` is the profile's overall monthly budget;
a non-NULL row targets one spending category. Uniqueness ("one overall budget
per profile/month", "one category budget per profile/category/month") is
enforced in the service and by partial unique indexes on the table.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Budget
from app.schemas import BudgetCreate, BudgetUpdate
from app.services.categories import require_category
from app.services.errors import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.profiles import require_profile


def create_budget(session: Session, profile_id: int, values: BudgetCreate) -> Budget:
    """Set a budget for a month, scoped to an existing explicit profile."""

    require_profile(session, profile_id)
    if values.category_id is not None:
        # A category budget's category must belong to the same profile.
        require_category(session, profile_id, values.category_id)

    if _find_budget(session, profile_id, values.category_id, values.period_month):
        target = "overall" if values.category_id is None else "category"
        raise ResourceConflictError(
            f"a {target} budget already exists for {values.period_month}"
        )

    budget = Budget(
        profile_id=profile_id,
        category_id=values.category_id,
        period_month=values.period_month,
        limit_cents=values.limit_cents,
    )
    session.add(budget)
    session.flush()
    return budget


def list_budgets(
    session: Session,
    profile_id: int,
    *,
    period_month: str | None = None,
) -> list[Budget]:
    """List budgets owned by ``profile_id``, optionally for one month."""

    require_profile(session, profile_id)
    statement = select(Budget).where(Budget.profile_id == profile_id)
    if period_month is not None:
        statement = statement.where(Budget.period_month == period_month)
    statement = statement.order_by(
        Budget.period_month,
        Budget.category_id.is_(None).desc(),  # overall budget first within a month
        Budget.category_id,
    )
    return list(session.scalars(statement))


def get_budget(session: Session, profile_id: int, budget_id: int) -> Budget | None:
    """Return a budget only when both its ID and profile owner match."""

    statement = select(Budget).where(
        Budget.id == budget_id,
        Budget.profile_id == profile_id,
    )
    return session.scalar(statement)


def require_budget(session: Session, profile_id: int, budget_id: int) -> Budget:
    """Return a scoped budget or the same error used for missing records."""

    budget = get_budget(session, profile_id, budget_id)
    if budget is None:
        raise ResourceNotFoundError("budget not found")
    return budget


def update_budget(
    session: Session,
    profile_id: int,
    budget_id: int,
    values: BudgetUpdate,
) -> Budget:
    """Update a budget's limit only through its owning profile scope."""

    budget = require_budget(session, profile_id, budget_id)
    changes = values.model_dump(exclude_unset=True)
    if "limit_cents" in changes and changes["limit_cents"] is None:
        raise InvalidUpdateError("required fields cannot be null: limit_cents")
    for field, value in changes.items():
        setattr(budget, field, value)
    session.flush()
    return budget


def delete_budget(session: Session, profile_id: int, budget_id: int) -> None:
    """Remove a budget target within its owning profile scope.

    Budgets are forward-looking targets rather than ledger records, so removing
    one is a hard delete; historical spending is unaffected.
    """

    budget = require_budget(session, profile_id, budget_id)
    session.delete(budget)
    session.flush()


def _find_budget(
    session: Session,
    profile_id: int,
    category_id: int | None,
    period_month: str,
) -> Budget | None:
    statement = select(Budget).where(
        Budget.profile_id == profile_id,
        Budget.period_month == period_month,
    )
    if category_id is None:
        statement = statement.where(Budget.category_id.is_(None))
    else:
        statement = statement.where(Budget.category_id == category_id)
    return session.scalar(statement)
