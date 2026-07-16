"""Transaction split persistence model.

A transaction may be divided across categories. The split amounts must sum to
the parent transaction amount (enforced by the service layer / domain rule, as a
cross-row invariant SQLite cannot express as a CHECK).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class TransactionSplit(TimestampMixin, Base):
    """One category allocation of a parent transaction, in integer cents."""

    __tablename__ = "transaction_splits"
    __table_args__ = (
        Index("ix_transaction_splits_transaction_id", "transaction_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="splits")
