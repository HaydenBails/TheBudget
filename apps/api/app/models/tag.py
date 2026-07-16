"""Tag and transaction-tag association models (profile-scoped)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class Tag(TimestampMixin, Base):
    """A free-form label owned by exactly one profile, unique by name."""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("profile_id", "name", name="uq_tags_profile_id_name"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="tags")


class TransactionTag(Base):
    """Many-to-many link between transactions and tags."""

    __tablename__ = "transaction_tags"

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
