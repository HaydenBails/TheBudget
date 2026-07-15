"""Establish the migration baseline.

Revision ID: 0001_migration_baseline
Revises: None
"""

from collections.abc import Sequence

revision: str = "0001_migration_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create no domain tables; BE-03 owns the initial domain schema."""


def downgrade() -> None:
    """Remove no domain tables from the empty baseline."""
