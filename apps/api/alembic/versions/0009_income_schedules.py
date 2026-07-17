"""Create profile-scoped income-schedule storage.

Revision ID: 0009_income_schedules
Revises: 0008_recurring_series
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_income_schedules"
down_revision: str | None = "0008_recurring_series"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the income_schedules table, scoped to an owning profile."""

    op.create_table(
        "income_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("frequency", sa.String(length=10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint("amount_cents > 0", name="ck_income_schedules_amount_cents_positive"),
        sa.CheckConstraint(
            "length(trim(name)) > 0", name="ck_income_schedules_name_not_blank"
        ),
        sa.CheckConstraint(
            "frequency IN ('weekly','biweekly','monthly')",
            name="ck_income_schedules_frequency_valid",
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_income_schedules_end_after_start",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_income_schedules_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_income_schedules"),
    )
    op.create_index(
        "ix_income_schedules_profile_id_is_active",
        "income_schedules",
        ["profile_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Remove income-schedule storage."""

    op.drop_index("ix_income_schedules_profile_id_is_active", table_name="income_schedules")
    op.drop_table("income_schedules")
