"""Create profile-scoped category storage.

Revision ID: 0003_category_models
Revises: 0002_profile_account_models
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_category_models"
down_revision: str | None = "0002_profile_account_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the categories table, scoped to an owning profile."""

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("icon", sa.String(length=16), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("excluded_from_spending", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_categories_name_not_blank"),
        sa.CheckConstraint("length(trim(slug)) > 0", name="ck_categories_slug_not_blank"),
        sa.CheckConstraint(
            "color GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
            "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'",
            name="ck_categories_color_hex",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_categories_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name="fk_categories_parent_id_categories",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("profile_id", "slug", name="uq_categories_profile_id_slug"),
    )
    op.create_index(
        "ix_categories_profile_id_is_archived",
        "categories",
        ["profile_id", "is_archived"],
        unique=False,
    )


def downgrade() -> None:
    """Remove category storage."""

    op.drop_index("ix_categories_profile_id_is_archived", table_name="categories")
    op.drop_table("categories")
