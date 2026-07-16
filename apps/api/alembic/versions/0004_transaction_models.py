"""Create transaction, split, and tag storage.

Revision ID: 0004_transaction_models
Revises: 0003_category_models
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_transaction_models"
down_revision: str | None = "0003_category_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPE_IN = (
    "type IN ('purchase', 'refund', 'payment', 'cash_advance', 'fee', "
    "'interest', 'income', 'adjustment', 'unknown')"
)
_STATUS_IN = (
    "categorization_status IN ('suggested', 'confirmed', 'rule_applied', "
    "'manual', 'uncategorized')"
)
_SOURCE_IN = "source IN ('pdf_import', 'csv_import', 'manual')"


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("raw_description", sa.String(length=500), nullable=False),
        sa.Column("merchant", sa.String(length=200), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("direction", sa.String(length=6), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("categorization_status", sa.String(length=16), nullable=False),
        sa.Column("included_in_spending", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.String(length=200), nullable=True),
        sa.Column("recurring_series_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("currency = 'CAD'", name="ck_transactions_currency_cad"),
        sa.CheckConstraint(
            "direction IN ('debit', 'credit')",
            name="ck_transactions_direction_supported",
        ),
        sa.CheckConstraint(_TYPE_IN, name="ck_transactions_type_supported"),
        sa.CheckConstraint(
            _STATUS_IN, name="ck_transactions_categorization_status_supported"
        ),
        sa.CheckConstraint(_SOURCE_IN, name="ck_transactions_source_supported"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"],
            name="fk_transactions_profile_id_profiles", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"],
            name="fk_transactions_account_id_accounts", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"],
            name="fk_transactions_category_id_categories", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )
    op.create_index(
        "ix_transactions_profile_id_account_id",
        "transactions", ["profile_id", "account_id"], unique=False,
    )
    op.create_index(
        "ix_transactions_profile_id_date",
        "transactions", ["profile_id", "date"], unique=False,
    )

    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"],
            name="fk_transaction_splits_transaction_id_transactions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"],
            name="fk_transaction_splits_category_id_categories", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_splits"),
    )
    op.create_index(
        "ix_transaction_splits_transaction_id",
        "transaction_splits", ["transaction_id"], unique=False,
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
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
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_tags_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"],
            name="fk_tags_profile_id_profiles", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tags"),
        sa.UniqueConstraint("profile_id", "name", name="uq_tags_profile_id_name"),
    )

    op.create_table(
        "transaction_tags",
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"],
            name="fk_transaction_tags_transaction_id_transactions", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"],
            name="fk_transaction_tags_tag_id_tags", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "transaction_id", "tag_id", name="pk_transaction_tags"
        ),
    )


def downgrade() -> None:
    op.drop_table("transaction_tags")
    op.drop_table("tags")
    op.drop_index(
        "ix_transaction_splits_transaction_id", table_name="transaction_splits"
    )
    op.drop_table("transaction_splits")
    op.drop_index("ix_transactions_profile_id_date", table_name="transactions")
    op.drop_index("ix_transactions_profile_id_account_id", table_name="transactions")
    op.drop_table("transactions")
