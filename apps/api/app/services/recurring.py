"""Profile-isolated recurring-charge persistence and detection sync.

Services flush but do not commit; the API layer owns transaction boundaries.
Detection heuristics live in ``recurring_rules`` and are reused here to keep the
persistence layer thin and testable.
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RecurringSeries, Transaction
from app.schemas import RecurringSeriesUpdate
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.profiles import require_profile
from app.services.recurring_rules import (
    DetectedSeries,
    RecurringObservation,
    detect_recurring_series,
)

# High-confidence series are auto-kept but remain reviewable (§12.2); lower
# confidence asks the user to confirm.
_TERMINAL_USER_STATUSES = frozenset({"cancel", "ended", "ignored"})


def _default_status(confidence: str) -> str:
    return "keep" if confidence == "high" else "review"


def _load_observations(session: Session, profile_id: int) -> list[RecurringObservation]:
    rows = session.scalars(
        select(Transaction).where(
            Transaction.profile_id == profile_id,
            Transaction.deleted_at.is_(None),
            Transaction.included_in_spending.is_(True),
            Transaction.direction == "debit",
            Transaction.type == "purchase",
        )
    )
    return [
        RecurringObservation(
            transaction_id=row.id,
            txn_date=row.date,
            merchant=row.merchant,
            raw_description=row.raw_description,
            amount_cents=row.amount_cents,
            category_id=row.category_id,
            account_id=row.account_id,
        )
        for row in rows
    ]


def detect_and_sync(session: Session, profile_id: int) -> tuple[int, int, list[RecurringSeries]]:
    """Run detection and idempotently upsert series; return (created, updated, all).

    Matched transactions are re-linked to their series on every run so the links
    stay consistent with the current ledger.
    """

    require_profile(session, profile_id)
    detected = detect_recurring_series(_load_observations(session, profile_id))

    existing = {
        series.merchant_key: series
        for series in session.scalars(
            select(RecurringSeries).where(RecurringSeries.profile_id == profile_id)
        )
    }

    # Clear existing links for this profile; re-link from the current detection.
    session.execute(
        update(Transaction)
        .where(
            Transaction.profile_id == profile_id,
            Transaction.recurring_series_id.is_not(None),
        )
        .values(recurring_series_id=None)
    )

    created = 0
    updated = 0
    for candidate in detected:
        series = existing.get(candidate.merchant_key)
        if series is None:
            series = RecurringSeries(
                profile_id=profile_id,
                merchant_key=candidate.merchant_key,
                status=_default_status(candidate.confidence),
            )
            session.add(series)
            created += 1
        else:
            updated += 1
        _apply_detection(series, candidate)
        session.flush()
        if candidate.transaction_ids:
            session.execute(
                update(Transaction)
                .where(
                    Transaction.profile_id == profile_id,
                    Transaction.id.in_(candidate.transaction_ids),
                )
                .values(recurring_series_id=series.id)
            )

    session.flush()
    return created, updated, list_recurring_series(session, profile_id)


def _apply_detection(series: RecurringSeries, candidate: DetectedSeries) -> None:
    series.amount_cents = candidate.amount_cents
    series.amount_min_cents = candidate.amount_min_cents
    series.amount_max_cents = candidate.amount_max_cents
    series.cadence = candidate.cadence
    series.interval_days = candidate.interval_days
    series.confidence = candidate.confidence
    series.occurrence_count = candidate.occurrence_count
    series.first_charge_date = candidate.first_charge_date
    series.last_charge_date = candidate.last_charge_date
    series.next_expected_date = candidate.next_expected_date
    series.category_id = candidate.category_id
    series.account_id = candidate.account_id
    series.rationale = candidate.rationale
    # Only a user-supplied display name survives re-detection.
    if not series.display_name:
        series.display_name = candidate.display_name
    # Respect user decisions; otherwise track the confidence-derived default.
    if not series.confirmed_by_user and series.status not in _TERMINAL_USER_STATUSES:
        series.status = _default_status(candidate.confidence)


def list_recurring_series(
    session: Session,
    profile_id: int,
    *,
    status: str | None = None,
) -> list[RecurringSeries]:
    require_profile(session, profile_id)
    statement = select(RecurringSeries).where(RecurringSeries.profile_id == profile_id)
    if status is not None:
        statement = statement.where(RecurringSeries.status == status)
    statement = statement.order_by(
        RecurringSeries.next_expected_date,
        RecurringSeries.merchant_key,
        RecurringSeries.id,
    )
    return list(session.scalars(statement))


def get_recurring_series(
    session: Session, profile_id: int, series_id: int
) -> RecurringSeries | None:
    return session.scalar(
        select(RecurringSeries).where(
            RecurringSeries.id == series_id,
            RecurringSeries.profile_id == profile_id,
        )
    )


def require_recurring_series(
    session: Session, profile_id: int, series_id: int
) -> RecurringSeries:
    series = get_recurring_series(session, profile_id, series_id)
    if series is None:
        raise ResourceNotFoundError("recurring series not found")
    return series


def update_recurring_series(
    session: Session,
    profile_id: int,
    series_id: int,
    values: RecurringSeriesUpdate,
) -> RecurringSeries:
    series = require_recurring_series(session, profile_id, series_id)
    changes = values.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None:
            raise InvalidUpdateError(f"required fields cannot be null: {field}")
    if "reminder_lead_days" in changes and changes["reminder_lead_days"] < 0:
        raise InvalidUpdateError("reminder_lead_days must not be negative")
    if "display_name" in changes and not str(changes["display_name"]).strip():
        raise InvalidUpdateError("display_name must not be blank")
    for field, value in changes.items():
        setattr(series, field, value)
    session.flush()
    return series


def delete_recurring_series(session: Session, profile_id: int, series_id: int) -> None:
    series = require_recurring_series(session, profile_id, series_id)
    session.execute(
        update(Transaction)
        .where(
            Transaction.profile_id == profile_id,
            Transaction.recurring_series_id == series.id,
        )
        .values(recurring_series_id=None)
    )
    session.delete(series)
    session.flush()
