"""Credit-card account persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.profile import Profile


class Account(TimestampMixin, Base):
    """A masked card account owned by exactly one profile."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "issuer IN ('TD', 'AMEX', 'CIBC', 'OTHER')",
            name="issuer_supported",
        ),
        CheckConstraint("length(trim(display_name)) > 0", name="display_name_not_blank"),
        CheckConstraint("currency = 'CAD'", name="currency_cad"),
        CheckConstraint(
            "last4 IS NULL OR "
            "(length(last4) IN (4, 5) AND last4 NOT GLOB '*[^0-9]*')",
            name="last4_masked_digits",
        ),
        CheckConstraint("kind IN ('asset', 'liability')", name="kind_valid"),
        Index("ix_accounts_profile_id_is_archived", "profile_id", "is_archived"),
        Index("ux_accounts_profile_id_id", "profile_id", "id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    issuer: Mapped[str] = mapped_column(String(10), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    last4: Mapped[str | None] = mapped_column(String(5), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    account_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 'liability' = a card/loan (positive balance = owed); 'asset' = cash/bank.
    kind: Mapped[str] = mapped_column(String(9), default="liability", nullable=False)
    # Current balance in the account's natural terms; None = not tracked.
    current_balance_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="accounts")
    import_batches: Mapped[list[ImportBatch]] = relationship(
        back_populates="account",
        passive_deletes="all",
        overlaps="import_batches,profile",
    )
