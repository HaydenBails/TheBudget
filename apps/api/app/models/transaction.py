"""Transaction persistence model (profile + account scoped)."""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.transaction_split import TransactionSplit

TRANSACTION_TYPES = (
    "purchase",
    "refund",
    "payment",
    "cash_advance",
    "fee",
    "interest",
    "income",
    "adjustment",
    "unknown",
)
CATEGORIZATION_STATUSES = (
    "suggested",
    "confirmed",
    "rule_applied",
    "manual",
    "uncategorized",
)
SOURCES = ("pdf_import", "csv_import", "manual")


def _in(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


class Transaction(TimestampMixin, Base):
    """A single ledger line owned by one profile and one of its accounts.

    ``amount_cents`` is signed integer minor units (purchases negative, refunds
    and income positive). Rows are soft-deleted via ``deleted_at`` so history is
    never lost. ``included_in_spending`` records the spending-inclusion decision.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(_in("type", TRANSACTION_TYPES), name="type_supported"),
        CheckConstraint(
            _in("categorization_status", CATEGORIZATION_STATUSES),
            name="categorization_status_supported",
        ),
        CheckConstraint(_in("source", SOURCES), name="source_supported"),
        CheckConstraint("direction IN ('debit', 'credit')", name="direction_supported"),
        CheckConstraint("currency = 'CAD'", name="currency_cad"),
        Index("ix_transactions_profile_id_account_id", "profile_id", "account_id"),
        Index("ix_transactions_profile_id_date", "profile_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    date: Mapped[_date] = mapped_column(Date, nullable=False)
    posted_date: Mapped[_date | None] = mapped_column(Date, nullable=True)
    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    merchant: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    direction: Mapped[str] = mapped_column(String(6), nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    categorization_status: Mapped[str] = mapped_column(
        String(16), default="uncategorized", nullable=False
    )
    included_in_spending: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    exclusion_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recurring_series_id: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)
    import_id: Mapped[int | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    profile: Mapped[Profile] = relationship(back_populates="transactions")
    splits: Mapped[list[TransactionSplit]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
