"""Create profile and account tables.

Revision ID: 0002_profile_account_models
Revises: 0001_migration_baseline
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_profile_account_models"
down_revision: str | None = "0001_migration_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create isolated profile and account storage."""

    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
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
        sa.CheckConstraint("base_currency = 'CAD'", name="ck_profiles_base_currency_cad"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_profiles_name_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("issuer", sa.String(length=10), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("last4", sa.String(length=5), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("account_fingerprint", sa.String(length=255), nullable=True),
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
        sa.CheckConstraint("currency = 'CAD'", name="ck_accounts_currency_cad"),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0",
            name="ck_accounts_display_name_not_blank",
        ),
        sa.CheckConstraint(
            "issuer IN ('TD', 'AMEX', 'CIBC', 'OTHER')",
            name="ck_accounts_issuer_supported",
        ),
        sa.CheckConstraint(
            "last4 IS NULL OR "
            "(length(last4) IN (4, 5) AND last4 NOT GLOB '*[^0-9]*')",
            name="ck_accounts_last4_masked_digits",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_accounts_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_index(
        "ix_accounts_profile_id_is_archived",
        "accounts",
        ["profile_id", "is_archived"],
        unique=False,
    )


def downgrade() -> None:
    """Remove account storage before its owning profiles."""

    op.drop_index("ix_accounts_profile_id_is_archived", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("profiles")
