"""Profile-isolated income-schedule persistence and forecast (§10, §11.2).

Services flush but do not commit; the API layer owns transaction boundaries.
Forecast occurrences are computed on demand via ``income_rules`` and never
persisted, so no infinite future records accumulate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IncomeSchedule
from app.schemas import IncomeScheduleCreate, IncomeScheduleUpdate
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.income_rules import (
    generate_occurrence_dates,
    next_occurrence_on_or_after,
)
from app.services.profiles import require_profile


@dataclass(frozen=True, slots=True)
class ForecastOccurrence:
    schedule_id: int
    name: str
    occurrence_date: date
    amount_cents: int


@dataclass(frozen=True, slots=True)
class IncomeSummary:
    period_start: date
    period_end: date
    expected_cents: int
    expected_remaining_cents: int
    occurrences: list[ForecastOccurrence]


def _validate_dates(start: date, end: date | None) -> None:
    if end is not None and end < start:
        raise InvalidUpdateError("end_date must not precede start_date")


def _attach_next_expected(schedule: IncomeSchedule, *, today: date) -> IncomeSchedule:
    pivot = max(today, schedule.start_date)
    schedule.next_expected_date = next_occurrence_on_or_after(  # type: ignore[attr-defined]
        schedule.start_date,
        schedule.frequency,  # type: ignore[arg-type]
        pivot,
        end=schedule.end_date,
    )
    return schedule


def create_income_schedule(
    session: Session, profile_id: int, values: IncomeScheduleCreate, *, today: date | None = None
) -> IncomeSchedule:
    require_profile(session, profile_id)
    _validate_dates(values.start_date, values.end_date)
    schedule = IncomeSchedule(profile_id=profile_id, **values.model_dump())
    session.add(schedule)
    session.flush()
    return _attach_next_expected(schedule, today=today or date.today())


def list_income_schedules(
    session: Session, profile_id: int, *, today: date | None = None
) -> list[IncomeSchedule]:
    require_profile(session, profile_id)
    schedules = list(
        session.scalars(
            select(IncomeSchedule)
            .where(IncomeSchedule.profile_id == profile_id)
            .order_by(IncomeSchedule.is_active.desc(), IncomeSchedule.name, IncomeSchedule.id)
        )
    )
    resolved_today = today or date.today()
    return [_attach_next_expected(schedule, today=resolved_today) for schedule in schedules]


def get_income_schedule(
    session: Session, profile_id: int, schedule_id: int
) -> IncomeSchedule | None:
    return session.scalar(
        select(IncomeSchedule).where(
            IncomeSchedule.id == schedule_id,
            IncomeSchedule.profile_id == profile_id,
        )
    )


def require_income_schedule(
    session: Session, profile_id: int, schedule_id: int, *, today: date | None = None
) -> IncomeSchedule:
    schedule = get_income_schedule(session, profile_id, schedule_id)
    if schedule is None:
        raise ResourceNotFoundError("income schedule not found")
    return _attach_next_expected(schedule, today=today or date.today())


def update_income_schedule(
    session: Session,
    profile_id: int,
    schedule_id: int,
    values: IncomeScheduleUpdate,
    *,
    today: date | None = None,
) -> IncomeSchedule:
    schedule = require_income_schedule(session, profile_id, schedule_id, today=today)
    changes = values.model_dump(exclude_unset=True)
    for field in ("name", "amount_cents", "frequency", "start_date", "is_active"):
        if field in changes and changes[field] is None:
            raise InvalidUpdateError(f"required fields cannot be null: {field}")
    new_start = changes.get("start_date", schedule.start_date)
    new_end = changes.get("end_date", schedule.end_date)
    _validate_dates(new_start, new_end)
    for field, value in changes.items():
        setattr(schedule, field, value)
    session.flush()
    return _attach_next_expected(schedule, today=today or date.today())


def delete_income_schedule(session: Session, profile_id: int, schedule_id: int) -> None:
    schedule = get_income_schedule(session, profile_id, schedule_id)
    if schedule is None:
        raise ResourceNotFoundError("income schedule not found")
    session.delete(schedule)
    session.flush()


def forecast_occurrences(
    session: Session,
    profile_id: int,
    range_from: date,
    range_to: date,
) -> list[ForecastOccurrence]:
    """Return active-schedule forecast occurrences within an inclusive range."""

    require_profile(session, profile_id)
    if range_to < range_from:
        raise InvalidUpdateError("date_to must not precede date_from")
    schedules = session.scalars(
        select(IncomeSchedule).where(
            IncomeSchedule.profile_id == profile_id,
            IncomeSchedule.is_active.is_(True),
        )
    )
    occurrences: list[ForecastOccurrence] = []
    for schedule in schedules:
        for occurrence_date in generate_occurrence_dates(
            schedule.start_date,
            schedule.frequency,  # type: ignore[arg-type]
            range_from,
            range_to,
            end=schedule.end_date,
        ):
            occurrences.append(
                ForecastOccurrence(
                    schedule_id=schedule.id,
                    name=schedule.name,
                    occurrence_date=occurrence_date,
                    amount_cents=schedule.amount_cents,
                )
            )
    occurrences.sort(key=lambda o: (o.occurrence_date, o.schedule_id))
    return occurrences


def income_summary(
    session: Session,
    profile_id: int,
    range_from: date,
    range_to: date,
    *,
    today: date | None = None,
) -> IncomeSummary:
    """Expected and still-due income for a period (feeds available-to-save)."""

    occurrences = forecast_occurrences(session, profile_id, range_from, range_to)
    resolved_today = today or date.today()
    expected = sum(o.amount_cents for o in occurrences)
    remaining = sum(o.amount_cents for o in occurrences if o.occurrence_date > resolved_today)
    return IncomeSummary(
        period_start=range_from,
        period_end=range_to,
        expected_cents=expected,
        expected_remaining_cents=remaining,
        occurrences=occurrences,
    )
