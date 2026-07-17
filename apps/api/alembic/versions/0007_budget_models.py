"""Create profile-scoped monthly budget storage.

Revision ID: 0007_budget_models
Revises: 0006_import_persistence
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_budget_models"
down_revision: str | None = "0006_import_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the budgets table, scoped to an owning profile."""

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("period_month", sa.String(length=7), nullable=False),
        sa.Column("limit_cents", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("limit_cents > 0", name="ck_budgets_limit_cents_positive"),
        sa.CheckConstraint(
            "period_month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'",
            name="ck_budgets_period_month_format",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_budgets_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_budgets_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
    )
    # One overall budget per profile/month (category_id IS NULL).
    op.create_index(
        "uq_budgets_overall_profile_month",
        "budgets",
        ["profile_id", "period_month"],
        unique=True,
        sqlite_where=sa.text("category_id IS NULL"),
    )
    # One category budget per profile/category/month (category_id IS NOT NULL).
    op.create_index(
        "uq_budgets_category_profile_month",
        "budgets",
        ["profile_id", "category_id", "period_month"],
        unique=True,
        sqlite_where=sa.text("category_id IS NOT NULL"),
    )
    op.create_index(
        "ix_budgets_profile_id_period_month",
        "budgets",
        ["profile_id", "period_month"],
        unique=False,
    )


def downgrade() -> None:
    """Remove budget storage."""

    op.drop_index("ix_budgets_profile_id_period_month", table_name="budgets")
    op.drop_index("uq_budgets_category_profile_month", table_name="budgets")
    op.drop_index("uq_budgets_overall_profile_month", table_name="budgets")
    op.drop_table("budgets")
