"""Monthly budget persistence model (profile-scoped).

A budget is a spending target for one calendar month. ``category_id`` is
nullable: a NULL row is the profile's single overall monthly budget, while a
non-NULL row targets one spending category. Partial unique indexes enforce the
product plan's "one overall budget per profile/month" and "one category budget
per profile/category/month" rules (SQLite treats NULLs as distinct in ordinary
unique constraints, so two separate partial indexes are required).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.profile import Profile


class Budget(TimestampMixin, Base):
    """A monthly spending target owned by exactly one profile."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("limit_cents > 0", name="limit_cents_positive"),
        CheckConstraint(
            "period_month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'",
            name="period_month_format",
        ),
        Index(
            "uq_budgets_overall_profile_month",
            "profile_id",
            "period_month",
            unique=True,
            sqlite_where=text("category_id IS NULL"),
        ),
        Index(
            "uq_budgets_category_profile_month",
            "profile_id",
            "category_id",
            "period_month",
            unique=True,
            sqlite_where=text("category_id IS NOT NULL"),
        ),
        Index("ix_budgets_profile_id_period_month", "profile_id", "period_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )
    period_month: Mapped[str] = mapped_column(String(7), nullable=False)
    limit_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="budgets")
    category: Mapped[Category | None] = relationship()
