"""Manual income-schedule persistence model (profile-scoped, §10)."""

from __future__ import annotations

from datetime import date as _date
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class IncomeSchedule(TimestampMixin, Base):
    """A recurring income source configured by the user (never inferred)."""

    __tablename__ = "income_schedules"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_cents_positive"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint(
            "frequency IN ('weekly','biweekly','monthly')", name="frequency_valid"
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="end_after_start"
        ),
        Index("ix_income_schedules_profile_id_is_active", "profile_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[_date] = mapped_column(Date, nullable=False)
    end_date: Mapped[_date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped[Profile] = relationship(back_populates="income_schedules")
