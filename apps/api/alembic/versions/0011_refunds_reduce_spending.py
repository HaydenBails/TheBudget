"""Include existing refunds in spending so they reduce net spend.

Refunds were previously excluded from spending entirely; the product's net-spend
model treats them as negative amounts that offset purchases. This backfills the
flag on refund rows created before that change.

Revision ID: 0011_refunds_reduce_spending
Revises: 0010_merchant_rules
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_refunds_reduce_spending"
down_revision: str | None = "0010_merchant_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Mark non-deleted refunds as included so they offset spending."""

    op.execute(
        sa.text(
            "UPDATE transactions SET included_in_spending = 1 "
            "WHERE type = 'refund' AND deleted_at IS NULL AND included_in_spending = 0"
        )
    )


def downgrade() -> None:
    """Restore refunds to excluded from spending."""

    op.execute(
        sa.text(
            "UPDATE transactions SET included_in_spending = 0 WHERE type = 'refund'"
        )
    )
