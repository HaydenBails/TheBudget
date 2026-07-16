"""Persistence and ownership coverage for canonical import staging."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.db import create_db_engine, create_session_factory
from app.models import (
    Account,
    Base,
    ImportBatch,
    ImportStagedTransaction,
    ImportTransactionLink,
    ImportWarning,
    Profile,
    Transaction,
)


def _batch(profile_id: int, account_id: int) -> ImportBatch:
    return ImportBatch(
        profile_id=profile_id,
        account_id=account_id,
        issuer="TD",
        source_filename="statement.pdf",
        file_sha256="a" * 64,
        logical_statement_key="b" * 64,
        parser_name="td_pdf",
        parser_version="1.0",
        validation_status="validated",
    )


def test_import_graph_round_trips_exact_money_and_audit_link(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "imports.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            profile = Profile(name="Personal")
            account = Account(profile=profile, issuer="TD", display_name="Visa", color="#12805c")
            session.add(profile)
            session.flush()
            batch = _batch(profile.id, account.id)
            staged = ImportStagedTransaction(
                profile_id=profile.id,
                account_id=account.id,
                source_row_reference="page-1:row-2",
                date=date(2026, 7, 1),
                raw_description="COFFEE SHOP",
                merchant="Coffee Shop",
                amount_cents=425,
                direction="debit",
                type="purchase",
                included_in_spending=True,
                original_foreign_amount_cents=300,
                original_foreign_currency="USD",
                exchange_rate=Decimal("1.41666667"),
                transaction_fingerprint="c" * 64,
            )
            warning = ImportWarning(
                profile_id=profile.id,
                code="DATE_INFERRED",
                severity="warning",
                message="Statement year supplied the transaction year.",
            )
            batch.staged_transactions.append(staged)
            batch.warnings.append(warning)
            session.add(batch)
            session.flush()
            transaction = Transaction(
                profile_id=profile.id,
                account_id=account.id,
                import_id=batch.id,
                source_row_reference=staged.source_row_reference,
                transaction_fingerprint=staged.transaction_fingerprint,
                date=staged.date,
                raw_description=staged.raw_description,
                merchant=staged.merchant,
                amount_cents=staged.amount_cents,
                direction=staged.direction,
                type=staged.type,
                included_in_spending=True,
                source="pdf_import",
                original_foreign_amount_cents=300,
                original_foreign_currency="USD",
                exchange_rate=Decimal("1.41666667"),
            )
            session.add(transaction)
            session.flush()
            session.add(
                ImportTransactionLink(
                    profile_id=profile.id,
                    import_batch_id=batch.id,
                    account_id=account.id,
                    staged_transaction_id=staged.id,
                    transaction_id=transaction.id,
                    decision="created",
                )
            )
            session.flush()
            assert batch.transaction_links[0].transaction_id == transaction.id
        assert transaction.exchange_rate == Decimal("1.41666667")
        indexes = {index["name"] for index in inspect(engine).get_indexes("import_batches")}
        assert {
            "ix_import_batches_profile_file_sha256",
            "ix_import_batches_profile_logical_key",
        } <= indexes
    finally:
        engine.dispose()


def test_batch_account_must_belong_to_profile(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "ownership.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            first = Profile(name="First")
            second = Profile(name="Second")
            account = Account(profile=second, issuer="TD", display_name="Visa", color="#12805c")
            session.add_all([first, second])
            session.flush()
            session.add(_batch(first.id, account.id))
            with pytest.raises(IntegrityError):
                session.flush()
    finally:
        engine.dispose()


def test_staged_row_account_must_equal_its_batch_account(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "staged-account.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            profile = Profile(name="Personal")
            first = Account(profile=profile, issuer="TD", display_name="First", color="#12805c")
            second = Account(profile=profile, issuer="TD", display_name="Second", color="#0369a1")
            session.add(profile)
            session.flush()
            batch = _batch(profile.id, first.id)
            session.add(batch)
            session.flush()
            session.add(
                ImportStagedTransaction(
                    profile_id=profile.id,
                    import_batch_id=batch.id,
                    account_id=second.id,
                    source_row_reference="row-1",
                    date=date(2026, 7, 1),
                    raw_description="COFFEE",
                    amount_cents=425,
                    direction="debit",
                    type="purchase",
                    included_in_spending=True,
                    transaction_fingerprint="d" * 64,
                )
            )
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                session.flush()
    finally:
        engine.dispose()


@pytest.mark.parametrize("cross_profile", [False, True])
def test_imported_transaction_account_must_match_batch(tmp_path: Path, cross_profile: bool) -> None:
    engine = create_db_engine(tmp_path / f"transaction-account-{cross_profile}.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            owner = Profile(name="Owner")
            other = Profile(name="Other")
            batch_account = Account(
                profile=owner, issuer="TD", display_name="Batch", color="#12805c"
            )
            wrong_account = Account(
                profile=other if cross_profile else owner,
                issuer="TD",
                display_name="Wrong",
                color="#0369a1",
            )
            session.add_all([owner, other])
            session.flush()
            batch = _batch(owner.id, batch_account.id)
            session.add(batch)
            session.flush()
            session.add(
                Transaction(
                    profile_id=owner.id,
                    account_id=wrong_account.id,
                    import_id=batch.id,
                    date=date(2026, 7, 1),
                    raw_description="COFFEE",
                    amount_cents=425,
                    direction="debit",
                    type="purchase",
                    included_in_spending=True,
                    source="pdf_import",
                )
            )
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                session.flush()
    finally:
        engine.dispose()


def test_link_can_reference_prior_batch_transaction_on_same_account(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "link-batch.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            profile = Profile(name="Personal")
            account = Account(profile=profile, issuer="TD", display_name="Visa", color="#12805c")
            session.add(profile)
            session.flush()
            first_batch = _batch(profile.id, account.id)
            second_batch = _batch(profile.id, account.id)
            second_batch.file_sha256 = "e" * 64
            second_batch.logical_statement_key = "f" * 64
            session.add_all([first_batch, second_batch])
            session.flush()
            staged = ImportStagedTransaction(
                profile_id=profile.id,
                import_batch_id=second_batch.id,
                account_id=account.id,
                source_row_reference="row-1",
                date=date(2026, 7, 1),
                raw_description="COFFEE",
                amount_cents=425,
                direction="debit",
                type="purchase",
                included_in_spending=True,
                transaction_fingerprint="d" * 64,
            )
            transaction = Transaction(
                profile_id=profile.id,
                account_id=account.id,
                import_id=first_batch.id,
                date=date(2026, 7, 1),
                raw_description="COFFEE",
                amount_cents=425,
                direction="debit",
                type="purchase",
                included_in_spending=True,
                source="pdf_import",
            )
            session.add_all([staged, transaction])
            session.flush()
            session.add(
                ImportTransactionLink(
                    profile_id=profile.id,
                    import_batch_id=second_batch.id,
                    account_id=account.id,
                    staged_transaction_id=staged.id,
                    transaction_id=transaction.id,
                    decision="linked_duplicate",
                )
            )
            session.flush()
            assert staged.transaction_link is not None
            assert staged.transaction_link.transaction_id == transaction.id
    finally:
        engine.dispose()


@pytest.mark.parametrize("cross_profile", [False, True])
def test_link_rejects_transaction_from_wrong_account(tmp_path: Path, cross_profile: bool) -> None:
    engine = create_db_engine(tmp_path / f"link-account-{cross_profile}.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            owner = Profile(name="Owner")
            other = Profile(name="Other")
            batch_account = Account(
                profile=owner, issuer="TD", display_name="Batch", color="#12805c"
            )
            wrong_account = Account(
                profile=other if cross_profile else owner,
                issuer="TD",
                display_name="Wrong",
                color="#0369a1",
            )
            session.add_all([owner, other])
            session.flush()
            batch = _batch(owner.id, batch_account.id)
            staged = ImportStagedTransaction(
                profile_id=owner.id,
                account_id=batch_account.id,
                source_row_reference="row-1",
                date=date(2026, 7, 1),
                raw_description="COFFEE",
                amount_cents=425,
                direction="debit",
                type="purchase",
                included_in_spending=True,
                transaction_fingerprint="d" * 64,
            )
            batch.staged_transactions.append(staged)
            session.add(batch)
            session.flush()
            transaction = Transaction(
                profile_id=wrong_account.profile_id,
                account_id=wrong_account.id,
                date=date(2026, 6, 30),
                raw_description="EARLIER COFFEE",
                amount_cents=425,
                direction="debit",
                type="purchase",
                included_in_spending=True,
                source="manual",
            )
            session.add(transaction)
            session.flush()
            session.add(
                ImportTransactionLink(
                    profile_id=owner.id,
                    import_batch_id=batch.id,
                    account_id=batch_account.id,
                    staged_transaction_id=staged.id,
                    transaction_id=transaction.id,
                    decision="linked_duplicate",
                )
            )
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                session.flush()
    finally:
        engine.dispose()


def test_profile_delete_cascades_import_batches_without_nulling_ownership(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(tmp_path / "profile-delete.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            profile = Profile(name="Disposable")
            account = Account(profile=profile, issuer="TD", display_name="Visa", color="#12805c")
            session.add(profile)
            session.flush()
            session.add(_batch(profile.id, account.id))
        profile_id = profile.id
        with factory.begin() as session:
            persisted = session.get(Profile, profile_id)
            assert persisted is not None
            session.delete(persisted)
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(ImportBatch)) == 0
            assert session.scalar(select(func.count()).select_from(Account)) == 0
    finally:
        engine.dispose()


def test_account_and_batch_deletes_fail_closed_without_nulling_import_ownership(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(tmp_path / "restrict-delete.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            profile = Profile(name="Personal")
            account = Account(profile=profile, issuer="TD", display_name="Visa", color="#12805c")
            session.add(profile)
            session.flush()
            batch = _batch(profile.id, account.id)
            session.add(batch)
            session.flush()
            session.add(
                Transaction(
                    profile_id=profile.id,
                    account_id=account.id,
                    import_id=batch.id,
                    date=date(2026, 7, 1),
                    raw_description="COFFEE",
                    amount_cents=425,
                    direction="debit",
                    type="purchase",
                    included_in_spending=True,
                    source="pdf_import",
                )
            )
        account_id = account.id
        batch_id = batch.id
        with factory() as session:
            persisted_account = session.get(Account, account_id)
            assert persisted_account is not None
            assert len(persisted_account.import_batches) == 1
            session.delete(persisted_account)
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                session.flush()
            session.rollback()
        with factory() as session:
            persisted_batch = session.get(ImportBatch, batch_id)
            assert persisted_batch is not None
            assert len(persisted_batch.transactions) == 1
            session.delete(persisted_batch)
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                session.flush()
            session.rollback()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "filename", ["statement\ncopy.pdf", "statement\x00copy.pdf", "statement\u202ecopy.pdf"]
)
def test_database_rejects_control_and_bidi_filenames(tmp_path: Path, filename: str) -> None:
    engine = create_db_engine(tmp_path / "unsafe-filename.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            profile = Profile(name="Personal")
            account = Account(profile=profile, issuer="TD", display_name="Visa", color="#12805c")
            session.add(profile)
            session.flush()
            batch = _batch(profile.id, account.id)
            batch.source_filename = filename
            session.add(batch)
            with pytest.raises(IntegrityError, match="CHECK constraint failed"):
                session.flush()
    finally:
        engine.dispose()


def test_import_tables_do_not_store_statement_payloads_or_account_numbers() -> None:
    forbidden = {
        "pdf_bytes",
        "pdf_blob",
        "raw_pdf",
        "extracted_text",
        "page_text",
        "full_extracted_text",
        "client_path",
        "file_path",
        "full_account_number",
        "account_number",
        "pan",
    }
    for table in (ImportBatch, ImportStagedTransaction, ImportWarning, ImportTransactionLink):
        assert forbidden.isdisjoint(table.__table__.columns.keys())
