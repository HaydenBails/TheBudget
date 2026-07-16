"""Spending-category persistence model (profile-scoped)."""

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


class Category(TimestampMixin, Base):
    """A spending category owned by exactly one profile.

    ``slug`` is unique per profile and used for idempotent default seeding.
    Categories are archived, never hard-deleted, so historical references stay
    valid. A nullable ``parent_id`` supports future sub-categories.
    """

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("profile_id", "slug", name="uq_categories_profile_id_slug"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("length(trim(slug)) > 0", name="slug_not_blank"),
        CheckConstraint(
            "color GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
            "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'",
            name="color_hex",
        ),
        Index("ix_categories_profile_id_is_archived", "profile_id", "is_archived"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    icon: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    excluded_from_spending: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="categories")
