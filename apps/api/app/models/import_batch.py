"""Profile-scoped statement import batch persistence."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.import_staged_transaction import ImportStagedTransaction
    from app.models.import_transaction_link import ImportTransactionLink
    from app.models.import_warning import ImportWarning
    from app.models.profile import Profile
    from app.models.transaction import Transaction

IMPORT_STATUSES = ("staged", "ready", "committed", "cancelled", "failed")
VALIDATION_STATUSES = (
    "validated",
    "validated_with_warnings",
    "needs_review",
    "failed",
)
IMPORT_DUPLICATE_DECISIONS = (
    "new",
    "blocked_file_hash",
    "blocked_logical_key",
    "potential_overlap",
)
MAX_SAFE_CENTS = (1 << 53) - 1


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ImportBatch(TimestampMixin, Base):
    """One privacy-safe import preview/commit lifecycle."""

    __tablename__ = "import_batches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "account_id"],
            ["accounts.profile_id", "accounts.id"],
            name="fk_import_batches_profile_account",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["profile_id", "duplicate_of_import_id"],
            ["import_batches.profile_id", "import_batches.id"],
            name="fk_import_batches_profile_duplicate",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "profile_id", "id", name="uq_import_batches_profile_id_id"
        ),
        UniqueConstraint(
            "profile_id",
            "id",
            "account_id",
            name="uq_import_batches_profile_id_account_id",
        ),
        CheckConstraint(_in("status", IMPORT_STATUSES), name="status_supported"),
        CheckConstraint(
            _in("validation_status", VALIDATION_STATUSES),
            name="validation_status_supported",
        ),
        CheckConstraint(
            _in("duplicate_decision", IMPORT_DUPLICATE_DECISIONS),
            name="duplicate_decision_supported",
        ),
        CheckConstraint("length(trim(issuer)) > 0", name="issuer_not_blank"),
        CheckConstraint("length(trim(parser_name)) > 0", name="parser_name_not_blank"),
        CheckConstraint(
            "length(trim(parser_version)) > 0", name="parser_version_not_blank"
        ),
        CheckConstraint(
            "length(trim(source_filename)) > 0 "
            "AND instr(source_filename, '/') = 0 "
            "AND instr(source_filename, char(92)) = 0 "
            "AND instr(source_filename, char(0)) = 0 "
            "AND source_filename NOT GLOB "
            "('*[' || char(1) || '-' || char(31) || char(127) || '-' || "
            "char(159) || ']*') "
            "AND instr(source_filename, char(1564)) = 0 "
            "AND instr(source_filename, char(8206)) = 0 "
            "AND instr(source_filename, char(8207)) = 0 "
            "AND instr(source_filename, char(8234)) = 0 "
            "AND instr(source_filename, char(8235)) = 0 "
            "AND instr(source_filename, char(8236)) = 0 "
            "AND instr(source_filename, char(8237)) = 0 "
            "AND instr(source_filename, char(8238)) = 0 "
            "AND instr(source_filename, char(8294)) = 0 "
            "AND instr(source_filename, char(8295)) = 0 "
            "AND instr(source_filename, char(8296)) = 0 "
            "AND instr(source_filename, char(8297)) = 0",
            name="source_filename_sanitized",
        ),
        CheckConstraint(
            "length(file_sha256) = 64 "
            "AND file_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="file_sha256_hex",
        ),
        CheckConstraint(
            "length(logical_statement_key) = 64 "
            "AND logical_statement_key NOT GLOB '*[^0-9a-f]*'",
            name="logical_statement_key_hex",
        ),
        CheckConstraint("currency = 'CAD'", name="currency_cad"),
        CheckConstraint(
            "transaction_count >= 0 AND purchase_count >= 0 "
            "AND credit_count >= 0 AND payment_count >= 0 "
            "AND fee_interest_count >= 0 AND unresolved_count >= 0",
            name="counts_nonnegative",
        ),
        *(
            CheckConstraint(
                f"{column} IS NULL OR {column} BETWEEN {-MAX_SAFE_CENTS} "
                f"AND {MAX_SAFE_CENTS}",
                name=f"{column}_safe_cents",
            )
            for column in (
                "expected_total_cents",
                "parsed_total_cents",
                "reconciliation_delta_cents",
                "purchase_total_cents",
                "credit_total_cents",
                "payment_total_cents",
                "fee_interest_total_cents",
            )
        ),
        Index("ix_import_batches_profile_file_sha256", "profile_id", "file_sha256"),
        Index(
            "ix_import_batches_profile_logical_key",
            "profile_id",
            "logical_statement_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(nullable=False)
    issuer: Mapped[str] = mapped_column(String(20), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    logical_statement_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(50), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    statement_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    statement_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="staged", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    duplicate_decision: Mapped[str] = mapped_column(
        String(32), default="new", nullable=False
    )
    duplicate_of_import_id: Mapped[int | None] = mapped_column(nullable=True)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchase_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fee_interest_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unresolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expected_total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    parsed_total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reconciliation_delta_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    purchase_total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    credit_total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payment_total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fee_interest_total_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    profile: Mapped[Profile] = relationship(
        back_populates="import_batches", overlaps="account,import_batches"
    )
    account: Mapped[Account] = relationship(
        back_populates="import_batches", overlaps="import_batches,profile"
    )
    staged_transactions: Mapped[list[ImportStagedTransaction]] = relationship(
        back_populates="import_batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    warnings: Mapped[list[ImportWarning]] = relationship(
        back_populates="import_batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    transaction_links: Mapped[list[ImportTransactionLink]] = relationship(
        back_populates="import_batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="import_links,staged_transaction,transaction,transaction_link",
    )
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="import_batch",
        passive_deletes="all",
        overlaps="profile,transactions",
    )
