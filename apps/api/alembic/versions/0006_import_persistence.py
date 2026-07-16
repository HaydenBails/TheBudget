"""Add privacy-safe import staging and final transaction provenance.

Revision ID: 0006_import_persistence
Revises: 0005_transaction_transfer_type
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_import_persistence"
down_revision: str | None = "0005_transaction_transfer_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MAX_SAFE_CENTS = (1 << 53) - 1


def _backup_transaction_children() -> None:
    """Protect child rows from SQLite batch-table rebuild cascades."""

    connection = op.get_bind()
    connection.exec_driver_sql("DROP TABLE IF EXISTS temp.be12_transaction_splits")
    connection.exec_driver_sql("DROP TABLE IF EXISTS temp.be12_transaction_tags")
    connection.exec_driver_sql(
        "CREATE TEMP TABLE be12_transaction_splits AS "
        "SELECT id, transaction_id, category_id, amount_cents, created_at, updated_at "
        "FROM transaction_splits"
    )
    connection.exec_driver_sql(
        "CREATE TEMP TABLE be12_transaction_tags AS "
        "SELECT transaction_id, tag_id FROM transaction_tags"
    )


def _restore_transaction_children() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        "INSERT INTO transaction_splits "
        "(id, transaction_id, category_id, amount_cents, created_at, updated_at) "
        "SELECT id, transaction_id, category_id, amount_cents, created_at, updated_at "
        "FROM temp.be12_transaction_splits"
    )
    connection.exec_driver_sql(
        "INSERT INTO transaction_tags (transaction_id, tag_id) "
        "SELECT transaction_id, tag_id FROM temp.be12_transaction_tags"
    )
    connection.exec_driver_sql("DROP TABLE temp.be12_transaction_splits")
    connection.exec_driver_sql("DROP TABLE temp.be12_transaction_tags")


def _safe_cents(column: str, *, nullable: bool = True) -> str:
    range_check = f"{column} BETWEEN {-MAX_SAFE_CENTS} AND {MAX_SAFE_CENTS}"
    return f"{column} IS NULL OR {range_check}" if nullable else range_check


def upgrade() -> None:
    # Revision 0005 exposed import_id as an unconstrained placeholder. Those
    # values cannot identify a real pre-import-framework batch, so discard them
    # deterministically before adding provenance foreign keys.
    op.execute(sa.text("UPDATE transactions SET import_id = NULL WHERE import_id IS NOT NULL"))
    invalid_ownership_count = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM transactions AS transaction_row "
            "JOIN accounts AS account_row "
            "ON account_row.id = transaction_row.account_id "
            "WHERE transaction_row.profile_id != account_row.profile_id"
        )
    )
    if invalid_ownership_count:
        raise RuntimeError(
            "revision 0006 requires every transaction account to belong to its profile"
        )

    op.create_index(
        "ux_accounts_profile_id_id",
        "accounts",
        ["profile_id", "id"],
        unique=True,
    )

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("issuer", sa.String(length=20), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("logical_statement_key", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=50), nullable=False),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column("statement_start_date", sa.Date(), nullable=True),
        sa.Column("statement_end_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("duplicate_decision", sa.String(length=32), nullable=False),
        sa.Column("duplicate_of_import_id", sa.Integer(), nullable=True),
        sa.Column("transaction_count", sa.Integer(), nullable=False),
        sa.Column("purchase_count", sa.Integer(), nullable=False),
        sa.Column("credit_count", sa.Integer(), nullable=False),
        sa.Column("payment_count", sa.Integer(), nullable=False),
        sa.Column("fee_interest_count", sa.Integer(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.Column("expected_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("parsed_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("reconciliation_delta_cents", sa.BigInteger(), nullable=True),
        sa.Column("purchase_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("credit_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("payment_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("fee_interest_total_cents", sa.BigInteger(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('staged', 'ready', 'committed', 'cancelled', 'failed')",
            name="ck_import_batches_status_supported",
        ),
        sa.CheckConstraint(
            "validation_status IN ('validated', 'validated_with_warnings', "
            "'needs_review', 'failed')",
            name="ck_import_batches_validation_status_supported",
        ),
        sa.CheckConstraint(
            "duplicate_decision IN ('new', 'blocked_file_hash', "
            "'blocked_logical_key', 'potential_overlap')",
            name="ck_import_batches_duplicate_decision_supported",
        ),
        sa.CheckConstraint("length(trim(issuer)) > 0", name="ck_import_batches_issuer_not_blank"),
        sa.CheckConstraint(
            "length(trim(parser_name)) > 0",
            name="ck_import_batches_parser_name_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(parser_version)) > 0",
            name="ck_import_batches_parser_version_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(source_filename)) > 0 "
            "AND instr(source_filename, '/') = 0 "
            "AND instr(source_filename, char(92)) = 0 "
            "AND instr(source_filename, char(0)) = 0 "
            "AND source_filename NOT GLOB "
            "('*[' || char(1) || '-' || char(31) || char(127) || '-' || "
            "char(159) || ']*') "
            "AND instr(source_filename, char(1564)) = 0 "
            "AND instr(source_filename, char(8206)) = 0 "
            "AND instr(source_filename, char(8207)) = 0 "
            "AND instr(source_filename, char(8234)) = 0 "
            "AND instr(source_filename, char(8235)) = 0 "
            "AND instr(source_filename, char(8236)) = 0 "
            "AND instr(source_filename, char(8237)) = 0 "
            "AND instr(source_filename, char(8238)) = 0 "
            "AND instr(source_filename, char(8294)) = 0 "
            "AND instr(source_filename, char(8295)) = 0 "
            "AND instr(source_filename, char(8296)) = 0 "
            "AND instr(source_filename, char(8297)) = 0",
            name="ck_import_batches_source_filename_sanitized",
        ),
        sa.CheckConstraint(
            "length(file_sha256) = 64 AND file_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_import_batches_file_sha256_hex",
        ),
        sa.CheckConstraint(
            "length(logical_statement_key) = 64 AND logical_statement_key NOT GLOB '*[^0-9a-f]*'",
            name="ck_import_batches_logical_statement_key_hex",
        ),
        sa.CheckConstraint("currency = 'CAD'", name="ck_import_batches_currency_cad"),
        sa.CheckConstraint(
            "transaction_count >= 0 AND purchase_count >= 0 "
            "AND credit_count >= 0 AND payment_count >= 0 "
            "AND fee_interest_count >= 0 AND unresolved_count >= 0",
            name="ck_import_batches_counts_nonnegative",
        ),
        *(
            sa.CheckConstraint(
                _safe_cents(column),
                name=f"ck_import_batches_{column}_safe_cents",
            )
            for column in (
                "expected_total_cents",
                "parsed_total_cents",
                "reconciliation_delta_cents",
                "purchase_total_cents",
                "credit_total_cents",
                "payment_total_cents",
                "fee_interest_total_cents",
            )
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_import_batches_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "account_id"],
            ["accounts.profile_id", "accounts.id"],
            name="fk_import_batches_profile_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "duplicate_of_import_id"],
            ["import_batches.profile_id", "import_batches.id"],
            name="fk_import_batches_profile_duplicate",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_batches"),
        sa.UniqueConstraint("profile_id", "id", name="uq_import_batches_profile_id_id"),
        sa.UniqueConstraint(
            "profile_id",
            "id",
            "account_id",
            name="uq_import_batches_profile_id_account_id",
        ),
    )
    op.create_index(
        "ix_import_batches_profile_file_sha256",
        "import_batches",
        ["profile_id", "file_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_import_batches_profile_logical_key",
        "import_batches",
        ["profile_id", "logical_statement_key"],
        unique=False,
    )

    op.create_table(
        "import_staged_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("source_row_reference", sa.String(length=100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("raw_description", sa.String(length=500), nullable=False),
        sa.Column("merchant", sa.String(length=200), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("direction", sa.String(length=6), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("included_in_spending", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.String(length=200), nullable=True),
        sa.Column("original_foreign_amount_cents", sa.BigInteger(), nullable=True),
        sa.Column("original_foreign_currency", sa.String(length=3), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("transaction_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("occurrence_index", sa.Integer(), nullable=False),
        sa.Column("duplicate_decision", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
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
        sa.CheckConstraint(
            "length(trim(source_row_reference)) > 0",
            name="ck_import_staged_transactions_row_ref_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(raw_description)) > 0",
            name="ck_import_staged_transactions_description_not_blank",
        ),
        sa.CheckConstraint("currency = 'CAD'", name="ck_import_staged_transactions_currency_cad"),
        sa.CheckConstraint(
            "direction IN ('debit', 'credit')",
            name="ck_import_staged_transactions_direction_supported",
        ),
        sa.CheckConstraint(
            "type IN ('purchase', 'refund', 'payment', 'transfer', "
            "'cash_advance', 'fee', 'interest', 'income', 'adjustment', 'unknown')",
            name="ck_import_staged_transactions_type_supported",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'skipped', 'needs_review')",
            name="ck_import_staged_transactions_status_supported",
        ),
        sa.CheckConstraint(
            "duplicate_decision IN ('new', 'skip_exact', 'potential_overlap', 'keep')",
            name="ck_import_staged_transactions_duplicate_decision_supported",
        ),
        sa.CheckConstraint(
            "occurrence_index >= 0",
            name="ck_import_staged_transactions_occurrence_index_nonnegative",
        ),
        sa.CheckConstraint(
            _safe_cents("amount_cents", nullable=False),
            name="ck_import_staged_transactions_amount_safe_cents",
        ),
        sa.CheckConstraint(
            _safe_cents("original_foreign_amount_cents"),
            name="ck_import_staged_transactions_foreign_amount_safe_cents",
        ),
        sa.CheckConstraint(
            "(original_foreign_amount_cents IS NULL) = (original_foreign_currency IS NULL)",
            name="ck_import_staged_transactions_foreign_amount_currency_together",
        ),
        sa.CheckConstraint(
            "exchange_rate IS NULL OR "
            "(exchange_rate > 0 AND original_foreign_amount_cents IS NOT NULL)",
            name="ck_import_staged_transactions_exchange_rate_positive",
        ),
        sa.CheckConstraint(
            "length(transaction_fingerprint) = 64 "
            "AND transaction_fingerprint NOT GLOB '*[^0-9a-f]*'",
            name="ck_import_staged_transactions_fingerprint_hex",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "import_batch_id", "account_id"],
            [
                "import_batches.profile_id",
                "import_batches.id",
                "import_batches.account_id",
            ],
            name="fk_import_staged_transactions_profile_batch_account",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_staged_transactions"),
        sa.UniqueConstraint(
            "profile_id",
            "import_batch_id",
            "account_id",
            "id",
            name="uq_import_staged_transactions_scope_id",
        ),
        sa.UniqueConstraint(
            "import_batch_id",
            "transaction_fingerprint",
            name="uq_import_staged_transactions_batch_fingerprint",
        ),
    )
    op.create_index(
        "ix_import_staged_transactions_profile_account_fingerprint",
        "import_staged_transactions",
        ["profile_id", "account_id", "transaction_fingerprint"],
        unique=False,
    )

    op.create_table(
        "import_warnings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("source_row_reference", sa.String(length=100), nullable=True),
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
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_import_warnings_code_not_blank"),
        sa.CheckConstraint(
            "length(trim(message)) > 0",
            name="ck_import_warnings_message_not_blank",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="ck_import_warnings_severity_supported",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_import_warnings_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "import_batch_id"],
            ["import_batches.profile_id", "import_batches.id"],
            name="fk_import_warnings_profile_batch",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_warnings"),
    )

    _backup_transaction_children()
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("source_row_reference", sa.String(100)))
        batch_op.add_column(sa.Column("transaction_fingerprint", sa.String(64)))
        batch_op.add_column(sa.Column("original_foreign_amount_cents", sa.BigInteger()))
        batch_op.add_column(sa.Column("original_foreign_currency", sa.String(3)))
        batch_op.add_column(sa.Column("exchange_rate", sa.Numeric(18, 8)))
        batch_op.drop_constraint("fk_transactions_account_id_accounts", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_transactions_profile_account",
            "accounts",
            ["profile_id", "account_id"],
            ["profile_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_transactions_profile_import_account",
            "import_batches",
            ["profile_id", "import_id", "account_id"],
            ["profile_id", "id", "account_id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_transactions_foreign_amount_safe_cents",
            _safe_cents("original_foreign_amount_cents"),
        )
        batch_op.create_check_constraint(
            "ck_transactions_foreign_amount_currency_together",
            "(original_foreign_amount_cents IS NULL) = (original_foreign_currency IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_transactions_exchange_rate_positive",
            "exchange_rate IS NULL OR "
            "(exchange_rate > 0 AND original_foreign_amount_cents IS NOT NULL)",
        )
    _restore_transaction_children()
    op.create_index(
        "ux_transactions_profile_account_fingerprint",
        "transactions",
        ["profile_id", "account_id", "transaction_fingerprint"],
        unique=True,
        sqlite_where=sa.text("transaction_fingerprint IS NOT NULL"),
    )
    op.create_index(
        "ux_transactions_profile_id_id",
        "transactions",
        ["profile_id", "id"],
        unique=True,
    )
    op.create_index(
        "ux_transactions_profile_account_id",
        "transactions",
        ["profile_id", "account_id", "id"],
        unique=True,
    )

    op.create_table(
        "import_transaction_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("staged_transaction_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
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
        sa.CheckConstraint(
            "decision IN ('created', 'linked_duplicate', 'skipped')",
            name="ck_import_transaction_links_decision_supported",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_import_transaction_links_profile_id_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "import_batch_id", "account_id"],
            [
                "import_batches.profile_id",
                "import_batches.id",
                "import_batches.account_id",
            ],
            name="fk_import_transaction_links_profile_batch_account",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "import_batch_id", "account_id", "staged_transaction_id"],
            [
                "import_staged_transactions.profile_id",
                "import_staged_transactions.import_batch_id",
                "import_staged_transactions.account_id",
                "import_staged_transactions.id",
            ],
            name="fk_import_transaction_links_staged_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "account_id", "transaction_id"],
            ["transactions.profile_id", "transactions.account_id", "transactions.id"],
            name="fk_import_transaction_links_transaction_account_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_transaction_links"),
        sa.UniqueConstraint(
            "staged_transaction_id",
            name="uq_import_transaction_links_staged_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("import_transaction_links")
    op.drop_index("ux_transactions_profile_account_id", table_name="transactions")
    op.drop_index("ux_transactions_profile_id_id", table_name="transactions")
    op.drop_index("ux_transactions_profile_account_fingerprint", table_name="transactions")
    _backup_transaction_children()
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint("ck_transactions_exchange_rate_positive", type_="check")
        batch_op.drop_constraint("ck_transactions_foreign_amount_currency_together", type_="check")
        batch_op.drop_constraint("ck_transactions_foreign_amount_safe_cents", type_="check")
        batch_op.drop_constraint("fk_transactions_profile_import_account", type_="foreignkey")
        batch_op.drop_constraint("fk_transactions_profile_account", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_transactions_account_id_accounts",
            "accounts",
            ["account_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("exchange_rate")
        batch_op.drop_column("original_foreign_currency")
        batch_op.drop_column("original_foreign_amount_cents")
        batch_op.drop_column("transaction_fingerprint")
        batch_op.drop_column("source_row_reference")
    _restore_transaction_children()
    op.drop_table("import_warnings")
    op.drop_index(
        "ix_import_staged_transactions_profile_account_fingerprint",
        table_name="import_staged_transactions",
    )
    op.drop_table("import_staged_transactions")
    op.drop_index("ix_import_batches_profile_logical_key", table_name="import_batches")
    op.drop_index("ix_import_batches_profile_file_sha256", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_index("ux_accounts_profile_id_id", table_name="accounts")
