"""Merchant → category rule for auto-categorization (profile-scoped, §rules)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class MerchantRule(TimestampMixin, Base):
    """A remembered mapping from a normalized merchant pattern to a category."""

    __tablename__ = "merchant_rules"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "pattern", "match_type", name="uq_merchant_rules_profile_pattern"
        ),
        CheckConstraint("length(trim(pattern)) > 0", name="pattern_not_blank"),
        CheckConstraint(
            "match_type IN ('exact','prefix','contains')", name="match_type_valid"
        ),
        Index("ix_merchant_rules_profile_active", "profile_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    pattern: Mapped[str] = mapped_column(String(120), nullable=False)
    match_type: Mapped[str] = mapped_column(String(8), default="exact", nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="merchant_rules")
