"""Audit link from a staged row to its final or duplicate transaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.import_staged_transaction import ImportStagedTransaction
    from app.models.transaction import Transaction

LINK_DECISIONS = ("created", "linked_duplicate", "skipped")


class ImportTransactionLink(TimestampMixin, Base):
    """Persist the explicit outcome for one staged transaction candidate."""

    __tablename__ = "import_transaction_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "import_batch_id", "account_id"],
            [
                "import_batches.profile_id",
                "import_batches.id",
                "import_batches.account_id",
            ],
            name="fk_import_transaction_links_profile_batch_account",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["profile_id", "import_batch_id", "account_id", "staged_transaction_id"],
            [
                "import_staged_transactions.profile_id",
                "import_staged_transactions.import_batch_id",
                "import_staged_transactions.account_id",
                "import_staged_transactions.id",
            ],
            name="fk_import_transaction_links_staged_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["profile_id", "account_id", "transaction_id"],
            [
                "transactions.profile_id",
                "transactions.account_id",
                "transactions.id",
            ],
            name="fk_import_transaction_links_transaction_account_scope",
            ondelete="CASCADE",
        ),
        UniqueConstraint("staged_transaction_id", name="uq_import_transaction_links_staged_id"),
        CheckConstraint(
            "decision IN ('created', 'linked_duplicate', 'skipped')",
            name="decision_supported",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    import_batch_id: Mapped[int] = mapped_column(nullable=False)
    account_id: Mapped[int] = mapped_column(nullable=False)
    staged_transaction_id: Mapped[int] = mapped_column(nullable=False)
    transaction_id: Mapped[int] = mapped_column(nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)

    import_batch: Mapped[ImportBatch] = relationship(
        back_populates="transaction_links",
        overlaps="import_links,staged_transaction,transaction,transaction_link",
    )
    staged_transaction: Mapped[ImportStagedTransaction] = relationship(
        back_populates="transaction_link",
        overlaps="import_batch,import_links,transaction,transaction_links",
    )
    transaction: Mapped[Transaction] = relationship(
        back_populates="import_links",
        overlaps="import_batch,staged_transaction,transaction_link,transaction_links",
    )
