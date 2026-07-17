"""Create profile-scoped recurring-charge series storage.

Revision ID: 0008_recurring_series
Revises: 0007_budget_models
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_recurring_series"
down_revision: str | None = "0007_budget_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recurring_series table, scoped to an owning profile."""

    op.create_table(
        "recurring_series",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("merchant_key", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("amount_min_cents", sa.BigInteger(), nullable=False),
        sa.Column("amount_max_cents", sa.BigInteger(), nullable=False),
        sa.Column("cadence", sa.String(length=10), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=6), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("confirmed_by_user", sa.Boolean(), nullable=False),
        sa.Column("reminder_lead_days", sa.Integer(), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_charge_date", sa.Date(), nullable=False),
        sa.Column("last_charge_date", sa.Date(), nullable=False),
        sa.Column("next_expected_date", sa.Date(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
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
        sa.CheckConstraint("amount_cents > 0", name="ck_recurring_series_amount_cents_positive"),
        sa.CheckConstraint(
            "amount_min_cents > 0 AND amount_max_cents >= amount_min_cents",
            name="ck_recurring_series_amount_range_valid",
        ),
        sa.CheckConstraint(
            "interval_days > 0", name="ck_recurring_series_interval_days_positive"
        ),
        sa.CheckConstraint(
            "cadence IN ('weekly','biweekly','monthly','quarterly','annual')",
            name="ck_recurring_series_cadence_valid",
        ),
        sa.CheckConstraint(
            "confidence IN ('high','medium','low')",
            name="ck_recurring_series_confidence_valid",
        ),
        sa.CheckConstraint(
            "status IN ('keep','review','cancel','ended','ignored')",
            name="ck_recurring_series_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_recurring_series_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_recurring_series_account_id_accounts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_recurring_series_category_id_categories",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_series"),
        sa.UniqueConstraint(
            "profile_id", "merchant_key", name="uq_recurring_series_profile_merchant"
        ),
    )
    op.create_index(
        "ix_recurring_series_profile_status",
        "recurring_series",
        ["profile_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove recurring-charge series storage."""

    op.drop_index("ix_recurring_series_profile_status", table_name="recurring_series")
    op.drop_table("recurring_series")
