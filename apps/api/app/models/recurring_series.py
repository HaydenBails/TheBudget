"""Recurring-charge / subscription series persistence model (profile-scoped)."""

from __future__ import annotations

from datetime import date as _date
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile

# Product plan §12.3: Keep / Review / Cancel / Ended / Ignored. "Cancel" is a
# user tracking state; the app never cancels a real subscription.
_STATUSES = ("keep", "review", "cancel", "ended", "ignored")
_CADENCES = ("weekly", "biweekly", "monthly", "quarterly", "annual")
_CONFIDENCES = ("high", "medium", "low")


class RecurringSeries(TimestampMixin, Base):
    """A detected repeating charge owned by exactly one profile."""

    __tablename__ = "recurring_series"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "merchant_key", name="uq_recurring_series_profile_merchant"
        ),
        CheckConstraint("amount_cents > 0", name="amount_cents_positive"),
        CheckConstraint(
            "amount_min_cents > 0 AND amount_max_cents >= amount_min_cents",
            name="amount_range_valid",
        ),
        CheckConstraint("interval_days > 0", name="interval_days_positive"),
        CheckConstraint(
            "cadence IN ('weekly','biweekly','monthly','quarterly','annual')",
            name="cadence_valid",
        ),
        CheckConstraint(
            "confidence IN ('high','medium','low')", name="confidence_valid"
        ),
        CheckConstraint(
            "status IN ('keep','review','cancel','ended','ignored')",
            name="status_valid",
        ),
        Index("ix_recurring_series_profile_status", "profile_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    merchant_key: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_min_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_max_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cadence: Mapped[str] = mapped_column(String(10), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(String(6), nullable=False)
    status: Mapped[str] = mapped_column(String(8), default="review", nullable=False)
    confirmed_by_user: Mapped[bool] = mapped_column(default=False, nullable=False)
    reminder_lead_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_charge_date: Mapped[_date] = mapped_column(Date, nullable=False)
    last_charge_date: Mapped[_date] = mapped_column(Date, nullable=False)
    next_expected_date: Mapped[_date] = mapped_column(Date, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="recurring_series")
