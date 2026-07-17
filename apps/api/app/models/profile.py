"""Profile persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.import_batch import ImportBatch
    from app.models.income_schedule import IncomeSchedule
    from app.models.recurring_series import RecurringSeries
    from app.models.tag import Tag
    from app.models.transaction import Transaction


class Profile(TimestampMixin, Base):
    """An isolated local data boundary with no authentication semantics."""

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("base_currency = 'CAD'", name="base_currency_cad"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    accounts: Mapped[list[Account]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    categories: Mapped[list[Category]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    budgets: Mapped[list[Budget]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recurring_series: Mapped[list[RecurringSeries]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    income_schedules: Mapped[list[IncomeSchedule]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="import_batch,transactions",
    )
    tags: Mapped[list[Tag]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    import_batches: Mapped[list[ImportBatch]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="account,import_batches",
    )
