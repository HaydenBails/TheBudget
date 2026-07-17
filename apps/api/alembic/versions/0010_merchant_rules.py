"""Create profile-scoped merchant auto-categorization rules.

Revision ID: 0010_merchant_rules
Revises: 0009_income_schedules
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_merchant_rules"
down_revision: str | None = "0009_income_schedules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the merchant_rules table, scoped to an owning profile."""

    op.create_table(
        "merchant_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("pattern", sa.String(length=120), nullable=False),
        sa.Column("match_type", sa.String(length=8), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
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
        sa.CheckConstraint("length(trim(pattern)) > 0", name="ck_merchant_rules_pattern_not_blank"),
        sa.CheckConstraint(
            "match_type IN ('exact','prefix','contains')",
            name="ck_merchant_rules_match_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_merchant_rules_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_merchant_rules_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_merchant_rules"),
        sa.UniqueConstraint(
            "profile_id", "pattern", "match_type", name="uq_merchant_rules_profile_pattern"
        ),
    )
    op.create_index(
        "ix_merchant_rules_profile_active",
        "merchant_rules",
        ["profile_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Remove merchant auto-categorization rules."""

    op.drop_index("ix_merchant_rules_profile_active", table_name="merchant_rules")
    op.drop_table("merchant_rules")
