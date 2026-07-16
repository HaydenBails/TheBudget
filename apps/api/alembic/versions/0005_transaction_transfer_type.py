"""Add transfer to the supported transaction types.

Revision ID: 0005_transaction_transfer_type
Revises: 0004_transaction_models
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_transaction_transfer_type"
down_revision: str | None = "0004_transaction_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_TYPE_IN = (
    "type IN ('purchase', 'refund', 'payment', 'cash_advance', 'fee', "
    "'interest', 'income', 'adjustment', 'unknown')"
)
_NEW_TYPE_IN = (
    "type IN ('purchase', 'refund', 'payment', 'transfer', 'cash_advance', "
    "'fee', 'interest', 'income', 'adjustment', 'unknown')"
)


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint("ck_transactions_type_supported", type_="check")
        batch_op.create_check_constraint(
            "ck_transactions_type_supported",
            _NEW_TYPE_IN,
        )


def downgrade() -> None:
    # Preserve excluded financial activity under the closest old supported type
    # before SQLite copies rows into the table carrying the old CHECK constraint.
    op.execute(
        "UPDATE transactions SET type = 'payment', included_in_spending = 0 "
        "WHERE type = 'transfer'"
    )
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint("ck_transactions_type_supported", type_="check")
        batch_op.create_check_constraint(
            "ck_transactions_type_supported",
            _OLD_TYPE_IN,
        )
