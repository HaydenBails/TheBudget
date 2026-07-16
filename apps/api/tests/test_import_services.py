"""BE-15 import preview, deduplication, and atomic commit regressions."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator, Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory
from app.importing import (
    ExtractedDocument,
    ParserDetection,
    ReconciliationResult,
    StatementMetadata,
    TransactionCandidate,
)
from app.models import Base, ImportStagedTransaction, ImportTransactionLink, Transaction
from app.parsers import StatementParser
from app.schemas import AccountCreate, ProfileCreate, TransactionCreate
from app.services import (
    ImportAcknowledgementRequiredError,
    ImportConflictError,
    ResourceNotFoundError,
    cancel_import,
    commit_import,
    create_account,
    create_profile,
    create_transaction,
    preview_import,
    suggest_import_account,
)

KEY = b"local-test-import-fingerprint-key-material"


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine: Engine = create_db_engine(tmp_path / "import-services.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as db:
            yield db
    finally:
        engine.dispose()


class SyntheticParser(StatementParser):
    parser_name = "synthetic_td"
    parser_version = "1.0"

    def __init__(
        self,
        candidates: Sequence[TransactionCandidate],
        *,
        period_start: date = date(2026, 6, 1),
        period_end: date = date(2026, 6, 30),
        status: str = "reconciled",
    ) -> None:
        self.candidates = tuple(candidates)
        self.metadata = StatementMetadata(
            issuer="TD",
            account_last4="4821",
            period_start=period_start,
            period_end=period_end,
            expected_activity_cents=sum(row.amount_cents for row in candidates),
        )
        self.status = status

    def detect(self, document: ExtractedDocument) -> ParserDetection:
        return ParserDetection(True, Decimal("1"), "synthetic_supported")

    def extract_metadata(self, document: ExtractedDocument) -> StatementMetadata:
        return self.metadata

    def extract_transactions(
        self, document: ExtractedDocument
    ) -> Sequence[TransactionCandidate]:
        return self.candidates

    def reconcile(
        self,
        metadata: StatementMetadata,
        transactions: Sequence[TransactionCandidate],
    ) -> ReconciliationResult:
        parsed = sum(row.amount_cents for row in transactions)
        expected = metadata.expected_activity_cents or 0
        return ReconciliationResult(
            status=self.status,  # type: ignore[arg-type]
            expected_cents=expected,
            parsed_cents=parsed,
            delta_cents=parsed - expected,
            tolerance_cents=1,
            transaction_count=len(transactions),
        )


def _candidate(
    source_index: int,
    *,
    occurrence_index: int = 0,
    description: str = "SYNTHETIC CAFE",
    amount_cents: int = 1234,
) -> TransactionCandidate:
    return TransactionCandidate(
        source_index=source_index,
        occurrence_index=occurrence_index,
        transaction_date=date(2026, 6, 10),
        posted_date=date(2026, 6, 11),
        raw_description=description,
        amount_cents=amount_cents,
        txn_type="purchase" if amount_cents > 0 else "refund",
        direction="debit" if amount_cents > 0 else "credit",
    )


def _document(seed: str = "a") -> ExtractedDocument:
    return ExtractedDocument(
        document_id=f"doc-{seed}",
        sha256=seed * 64,
        sanitized_filename="statement.pdf",
        byte_count=100,
        page_count=1,
        pages=("PRIVATE PAGE CONTENT",),
    )


def _profile_account(session: Session, name: str = "Owner"):
    profile = create_profile(session, ProfileCreate(name=name))
    account = create_account(
        session,
        profile.id,
        AccountCreate(
            issuer="TD",
            display_name=f"{name} card",
            color="#0ea5e9",
            last4="4821",
        ),
    )
    return profile, account


def test_preview_is_profile_scoped_suggests_but_requires_explicit_account(
    session: Session,
) -> None:
    owner, account = _profile_account(session)
    other, other_account = _profile_account(session, "Other")
    repeated = (_candidate(0), _candidate(1, occurrence_index=1))
    parser = SyntheticParser(repeated)

    assert suggest_import_account(session, owner.id, parser.metadata) is account
    assert suggest_import_account(session, other.id, parser.metadata) is other_account
    cleaned: list[bool] = []
    result = preview_import(
        session,
        owner.id,
        account.id,
        _document(),
        parser,
        fingerprint_key=KEY,
        cleanup=lambda: cleaned.append(True),
    )

    assert result.suggested_account_id == account.id
    assert result.batch.status == "ready"
    assert result.batch.transaction_count == 2
    assert cleaned == [True]
    assert session.scalar(select(func.count(Transaction.id))) == 0
    rows = list(
        session.scalars(
            select(ImportStagedTransaction).order_by(ImportStagedTransaction.id)
        )
    )
    assert [row.occurrence_index for row in rows] == [0, 1]
    assert rows[0].transaction_fingerprint != rows[1].transaction_fingerprint
    assert all("PRIVATE" not in repr(row) for row in rows)
    committed = commit_import(session, owner.id, result.batch.id)
    assert committed.created_count == 2
    assert session.scalar(select(func.count(Transaction.id))) == 2

    with pytest.raises(ResourceNotFoundError, match="account not found"):
        preview_import(
            session,
            owner.id,
            other_account.id,
            _document("b"),
            parser,
            fingerprint_key=KEY,
        )


def test_file_and_logical_duplicates_are_blocked_with_prior_reference(
    session: Session,
) -> None:
    profile, account = _profile_account(session)
    parser = SyntheticParser((_candidate(0),))
    first = preview_import(
        session, profile.id, account.id, _document("a"), parser, fingerprint_key=KEY
    ).batch
    file_duplicate = preview_import(
        session, profile.id, account.id, _document("a"), parser, fingerprint_key=KEY
    ).batch
    logical_duplicate = preview_import(
        session, profile.id, account.id, _document("b"), parser, fingerprint_key=KEY
    ).batch

    assert (file_duplicate.duplicate_decision, file_duplicate.duplicate_of_import_id) == (
        "blocked_file_hash",
        first.id,
    )
    assert (
        logical_duplicate.duplicate_decision,
        logical_duplicate.duplicate_of_import_id,
    ) == ("blocked_logical_key", first.id)
    with pytest.raises(ImportConflictError, match=f"duplicates import {first.id}"):
        commit_import(session, profile.id, logical_duplicate.id)


def test_commit_sets_provenance_is_idempotent_and_exact_overlap_auto_links(
    session: Session,
) -> None:
    profile, account = _profile_account(session)
    parser = SyntheticParser((_candidate(0),))
    first = preview_import(
        session, profile.id, account.id, _document("a"), parser, fingerprint_key=KEY
    ).batch
    committed = commit_import(session, profile.id, first.id)
    repeated = commit_import(session, profile.id, first.id)

    assert committed.created_count == repeated.created_count == 1
    assert committed.transactions[0].source == "pdf_import"
    assert committed.transactions[0].import_id == first.id
    assert committed.transactions[0].source_row_reference == "synthetic_td:0"
    assert session.scalar(select(func.count(Transaction.id))) == 1

    overlap_parser = SyntheticParser(
        (_candidate(0),),
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
    )
    overlap = preview_import(
        session,
        profile.id,
        account.id,
        _document("b"),
        overlap_parser,
        fingerprint_key=KEY,
    ).batch
    staged = overlap.staged_transactions[0]
    assert (staged.duplicate_decision, staged.status) == ("skip_exact", "skipped")
    linked = commit_import(session, profile.id, overlap.id)
    assert (linked.created_count, linked.linked_duplicate_count) == (0, 1)
    assert session.scalar(select(func.count(Transaction.id))) == 1
    link = session.scalar(
        select(ImportTransactionLink).where(
            ImportTransactionLink.import_batch_id == overlap.id
        )
    )
    assert link is not None and link.transaction_id == committed.transactions[0].id


def test_potential_overlap_needs_acknowledgement_and_is_not_auto_skipped(
    session: Session,
) -> None:
    profile, account = _profile_account(session)
    create_transaction(
        session,
        profile.id,
        TransactionCreate(
            account_id=account.id,
            date=date(2026, 6, 10),
            posted_date=date(2026, 6, 11),
            raw_description="  synthetic   cafe ",
            amount_cents=1234,
            direction="debit",
            type="purchase",
        ),
    )
    batch = preview_import(
        session,
        profile.id,
        account.id,
        _document(),
        SyntheticParser((_candidate(0),)),
        fingerprint_key=KEY,
    ).batch

    staged = batch.staged_transactions[0]
    assert batch.validation_status == "needs_review"
    assert batch.duplicate_decision == "potential_overlap"
    assert batch.unresolved_count == 1
    assert (staged.duplicate_decision, staged.status) == (
        "potential_overlap",
        "needs_review",
    )
    with pytest.raises(ImportAcknowledgementRequiredError, match="acknowledgement"):
        commit_import(session, profile.id, batch.id)
    committed = commit_import(
        session, profile.id, batch.id, acknowledge_needs_review=True
    )
    assert committed.created_count == 1
    assert session.scalar(select(func.count(Transaction.id))) == 2


def test_failed_commit_rolls_back_all_rows_and_marks_batch_failed(
    session: Session,
) -> None:
    profile, account = _profile_account(session)
    batch = preview_import(
        session,
        profile.id,
        account.id,
        _document(),
        SyntheticParser((_candidate(0), _candidate(1, description="SECOND ROW"))),
        fingerprint_key=KEY,
    ).batch
    from app.services import imports as import_services

    real_create = import_services.create_imported_transaction
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic commit failure")
        return real_create(*args, **kwargs)

    cleaned: list[bool] = []
    with patch(
        "app.services.imports.create_imported_transaction", side_effect=fail_second
    ):
        result = commit_import(
            session,
            profile.id,
            batch.id,
            cleanup=lambda: cleaned.append(True),
        )

    assert cleaned == [True]
    assert result.failure_code == "commit_failed"
    assert batch.status == "failed"
    assert session.scalar(select(func.count(Transaction.id))) == 0
    assert session.scalar(select(func.count(ImportTransactionLink.id))) == 0
    session.commit()
    assert session.get(type(batch), batch.id).status == "failed"


def test_needs_review_cancel_cleanup_and_logs_are_content_free(
    session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    profile, account = _profile_account(session)
    parser = SyntheticParser((_candidate(0),), status="needs_review")
    logger = logging.getLogger("import-service-test")
    cleaned: list[str] = []
    with caplog.at_level(logging.INFO, logger=logger.name):
        batch = preview_import(
            session,
            profile.id,
            account.id,
            _document(),
            parser,
            fingerprint_key=KEY,
            logger=logger,
        ).batch
        cancelled = cancel_import(
            session,
            profile.id,
            batch.id,
            cleanup=lambda: cleaned.append("cancel"),
            logger=logger,
        )
        cancel_import(session, profile.id, batch.id, logger=logger)

    assert cancelled.status == "cancelled"
    assert cleaned == ["cancel"]
    assert batch.staged_transactions == []
    assert "PRIVATE PAGE CONTENT" not in caplog.text
    assert "SYNTHETIC CAFE" not in caplog.text
    assert "statement.pdf" not in caplog.text


def test_cleanup_runs_for_missing_and_cross_profile_terminal_requests(
    session: Session,
) -> None:
    owner, account = _profile_account(session)
    other, _ = _profile_account(session, "Other")
    batch = preview_import(
        session,
        owner.id,
        account.id,
        _document(),
        SyntheticParser((_candidate(0),)),
        fingerprint_key=KEY,
    ).batch
    cleaned: list[str] = []

    with pytest.raises(ResourceNotFoundError, match="import not found"):
        commit_import(
            session,
            other.id,
            batch.id,
            cleanup=lambda: cleaned.append("commit"),
        )
    with pytest.raises(ResourceNotFoundError, match="import not found"):
        cancel_import(
            session,
            owner.id,
            batch.id + 999,
            cleanup=lambda: cleaned.append("cancel"),
        )
    assert cleaned == ["commit", "cancel"]


@pytest.mark.parametrize(
    "result",
    [
        ReconciliationResult("reconciled", 1234, 9999, 8765, 1, 1),
        ReconciliationResult("reconciled", 1234, 1234, 0, 1, 2),
        ReconciliationResult("reconciled", 0, 1234, 1234, 1, 1),
        ReconciliationResult("reconciled", 1234, 1234, 0, 100, 1),
    ],
)
def test_inconsistent_parser_reconciliation_fails_before_persistence(
    session: Session,
    result: ReconciliationResult,
) -> None:
    profile, account = _profile_account(session)
    parser = SyntheticParser((_candidate(0),))
    cleaned: list[bool] = []
    with patch.object(parser, "reconcile", return_value=result):
        with pytest.raises(ImportConflictError, match="reconciliation result"):
            preview_import(
                session,
                profile.id,
                account.id,
                _document(),
                parser,
                fingerprint_key=KEY,
                cleanup=lambda: cleaned.append(True),
            )
    assert cleaned == [True]
    assert session.scalar(select(func.count(ImportStagedTransaction.id))) == 0


def test_two_ready_previews_recheck_exact_target_at_commit(session: Session) -> None:
    profile, account = _profile_account(session)
    first = preview_import(
        session,
        profile.id,
        account.id,
        _document("a"),
        SyntheticParser(
            (_candidate(0),),
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
        ),
        fingerprint_key=KEY,
    ).batch
    second = preview_import(
        session,
        profile.id,
        account.id,
        _document("b"),
        SyntheticParser(
            (_candidate(0),),
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
        ),
        fingerprint_key=KEY,
    ).batch
    assert first.status == second.status == "ready"

    first_result = commit_import(session, profile.id, first.id)
    second_result = commit_import(session, profile.id, second.id)
    assert (first_result.created_count, second_result.linked_duplicate_count) == (1, 1)
    assert session.scalar(select(func.count(Transaction.id))) == 1


def test_post_flush_result_failure_rolls_back_savepoint_without_partial_rows(
    session: Session,
) -> None:
    profile, account = _profile_account(session)
    batch = preview_import(
        session,
        profile.id,
        account.id,
        _document(),
        SyntheticParser((_candidate(0),)),
        fingerprint_key=KEY,
    ).batch
    with patch("app.services.imports._commit_result", side_effect=RuntimeError("boom")):
        result = commit_import(session, profile.id, batch.id)

    assert result.failure_code == "commit_failed"
    assert batch.status == "failed"
    assert session.scalar(select(func.count(Transaction.id))) == 0
    assert session.scalar(select(func.count(ImportTransactionLink.id))) == 0


def test_concurrent_commits_use_unique_fingerprint_claim(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "concurrent-import.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory.begin() as seed:
            profile, account = _profile_account(seed)
            first = preview_import(
                seed,
                profile.id,
                account.id,
                _document("a"),
                SyntheticParser(
                    (_candidate(0),),
                    period_start=date(2026, 6, 1),
                    period_end=date(2026, 6, 30),
                ),
                fingerprint_key=KEY,
            ).batch
            second = preview_import(
                seed,
                profile.id,
                account.id,
                _document("b"),
                SyntheticParser(
                    (_candidate(0),),
                    period_start=date(2026, 7, 1),
                    period_end=date(2026, 7, 31),
                ),
                fingerprint_key=KEY,
            ).batch
            profile_id = profile.id
            import_ids = (first.id, second.id)

        barrier = threading.Barrier(2)
        results = []
        errors: list[BaseException] = []

        def worker(import_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                with session_factory.begin() as db:
                    results.append(commit_import(db, profile_id, import_id))
            except BaseException as exc:  # captured for an assertion in the parent thread
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(value,)) for value in import_ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        assert sorted(
            (result.created_count, result.linked_duplicate_count, result.failure_code)
            for result in results
        ) == [(0, 1, None), (1, 0, None)]
        with session_factory() as verify:
            assert verify.scalar(select(func.count(Transaction.id))) == 1
            assert verify.scalar(select(func.count(ImportTransactionLink.id))) == 2
    finally:
        engine.dispose()


def test_concurrent_previews_serialize_file_duplicate_decision(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "concurrent-preview.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory.begin() as seed:
            profile, account = _profile_account(seed)
            profile_id = profile.id
            account_id = account.id

        barrier = threading.Barrier(2)
        results = []
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                barrier.wait(timeout=5)
                with session_factory.begin() as db:
                    results.append(
                        preview_import(
                            db,
                            profile_id,
                            account_id,
                            _document(),
                            SyntheticParser((_candidate(0),)),
                            fingerprint_key=KEY,
                        ).batch
                    )
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        assert sorted(batch.duplicate_decision for batch in results) == [
            "blocked_file_hash",
            "new",
        ]
        blocked = next(batch for batch in results if batch.duplicate_of_import_id)
        original = next(batch for batch in results if batch.duplicate_of_import_id is None)
        assert blocked.duplicate_of_import_id == original.id
    finally:
        engine.dispose()
