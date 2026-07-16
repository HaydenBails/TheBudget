"""Structured, privacy-safe import warning persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch

WARNING_SEVERITIES = ("info", "warning", "error")


class ImportWarning(TimestampMixin, Base):
    """One structured issue code/message without statement page content."""

    __tablename__ = "import_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "import_batch_id"],
            ["import_batches.profile_id", "import_batches.id"],
            name="fk_import_warnings_profile_batch",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(trim(code)) > 0", name="code_not_blank"),
        CheckConstraint("length(trim(message)) > 0", name="message_not_blank"),
        CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="severity_supported",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    import_batch_id: Mapped[int] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    source_row_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    import_batch: Mapped[ImportBatch] = relationship(
        back_populates="warnings", overlaps="profile"
    )
