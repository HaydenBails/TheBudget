"""Canonical structured transaction candidates awaiting import commit."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.transaction import TRANSACTION_TYPES

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.import_transaction_link import ImportTransactionLink

STAGED_TRANSACTION_STATUSES = ("pending", "accepted", "skipped", "needs_review")
STAGED_DUPLICATE_DECISIONS = ("new", "skip_exact", "potential_overlap", "keep")
MAX_SAFE_CENTS = (1 << 53) - 1


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ImportStagedTransaction(TimestampMixin, Base):
    """One normalized, structured row from a statement preview."""

    __tablename__ = "import_staged_transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "import_batch_id", "account_id"],
            [
                "import_batches.profile_id",
                "import_batches.id",
                "import_batches.account_id",
            ],
            name="fk_import_staged_transactions_profile_batch_account",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "profile_id",
            "import_batch_id",
            "account_id",
            "id",
            name="uq_import_staged_transactions_scope_id",
        ),
        UniqueConstraint(
            "import_batch_id",
            "transaction_fingerprint",
            name="uq_import_staged_transactions_batch_fingerprint",
        ),
        CheckConstraint("length(trim(source_row_reference)) > 0", name="row_ref_not_blank"),
        CheckConstraint("length(trim(raw_description)) > 0", name="description_not_blank"),
        CheckConstraint("currency = 'CAD'", name="currency_cad"),
        CheckConstraint("direction IN ('debit', 'credit')", name="direction_supported"),
        CheckConstraint(_in("type", TRANSACTION_TYPES), name="type_supported"),
        CheckConstraint(
            _in("status", STAGED_TRANSACTION_STATUSES), name="status_supported"
        ),
        CheckConstraint(
            _in("duplicate_decision", STAGED_DUPLICATE_DECISIONS),
            name="duplicate_decision_supported",
        ),
        CheckConstraint("occurrence_index >= 0", name="occurrence_index_nonnegative"),
        CheckConstraint(
            f"amount_cents BETWEEN {-MAX_SAFE_CENTS} AND {MAX_SAFE_CENTS}",
            name="amount_safe_cents",
        ),
        CheckConstraint(
            "original_foreign_amount_cents IS NULL OR "
            f"original_foreign_amount_cents BETWEEN {-MAX_SAFE_CENTS} "
            f"AND {MAX_SAFE_CENTS}",
            name="foreign_amount_safe_cents",
        ),
        CheckConstraint(
            "(original_foreign_amount_cents IS NULL) = "
            "(original_foreign_currency IS NULL)",
            name="foreign_amount_currency_together",
        ),
        CheckConstraint(
            "exchange_rate IS NULL OR "
            "(exchange_rate > 0 AND original_foreign_amount_cents IS NOT NULL)",
            name="exchange_rate_positive",
        ),
        CheckConstraint(
            "length(transaction_fingerprint) = 64 "
            "AND transaction_fingerprint NOT GLOB '*[^0-9a-f]*'",
            name="fingerprint_hex",
        ),
        Index(
            "ix_import_staged_transactions_profile_account_fingerprint",
            "profile_id",
            "account_id",
            "transaction_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(nullable=False)
    import_batch_id: Mapped[int] = mapped_column(nullable=False)
    account_id: Mapped[int] = mapped_column(nullable=False)
    source_row_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    merchant: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    direction: Mapped[str] = mapped_column(String(6), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    included_in_spending: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    exclusion_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    original_foreign_amount_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    original_foreign_currency: Mapped[str | None] = mapped_column(
        String(3), nullable=True
    )
    exchange_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8), nullable=True
    )
    transaction_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    occurrence_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_decision: Mapped[str] = mapped_column(
        String(24), default="new", nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    import_batch: Mapped[ImportBatch] = relationship(back_populates="staged_transactions")
    transaction_link: Mapped[ImportTransactionLink | None] = relationship(
        back_populates="staged_transaction",
        uselist=False,
        overlaps="import_batch,import_links,transaction,transaction_links",
    )
