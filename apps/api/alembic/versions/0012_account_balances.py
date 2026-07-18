"""Add account kind and current balance for net-worth tracking.

Revision ID: 0012_account_balances
Revises: 0011_refunds_reduce_spending
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_account_balances"
down_revision: str | None = "0011_refunds_reduce_spending"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add kind + current_balance_cents to accounts.

    Uses native SQLite ADD COLUMN (no table recreation): recreating ``accounts``
    while it has rows would trigger SQLite's implicit-DELETE-on-DROP, cascading
    into ``transactions``. The kind check is enforced by the ORM model and the
    Pydantic schema rather than a migration-added constraint.
    """

    op.add_column(
        "accounts",
        sa.Column("kind", sa.String(length=9), nullable=False, server_default="liability"),
    )
    op.add_column(
        "accounts",
        sa.Column("current_balance_cents", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    """Drop the account net-worth columns (native DROP COLUMN, no recreation)."""

    op.drop_column("accounts", "current_balance_cents")
    op.drop_column("accounts", "kind")
