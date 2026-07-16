"""Profile-isolated statement preview and atomic commit services."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.importing import (
    ExtractedDocument,
    StatementMetadata,
    TransactionCandidate,
    statement_fingerprint,
    transaction_fingerprint,
)
from app.models import (
    Account,
    ImportBatch,
    ImportStagedTransaction,
    ImportTransactionLink,
    ImportWarning,
    Profile,
    Transaction,
)
from app.parsers import StatementParser
from app.services.accounts import require_account
from app.services.errors import ResourceNotFoundError
from app.services.profiles import require_profile
from app.services.transactions import create_imported_transaction
from app.services.transactions_rules import default_included_for_type

Cleanup = Callable[[], None]


class ImportConflictError(ValueError):
    """An import cannot proceed because its persisted lifecycle conflicts."""


class ImportAcknowledgementRequiredError(ValueError):
    """A reviewed import requires an explicit commit acknowledgement."""


@dataclass(frozen=True, slots=True)
class ImportPreviewResult:
    batch: ImportBatch
    suggested_account_id: int | None


@dataclass(frozen=True, slots=True)
class ImportCommitResult:
    batch: ImportBatch
    transactions: tuple[Transaction, ...]
    created_count: int
    linked_duplicate_count: int
    failure_code: str | None = None


def suggest_import_account(
    session: Session,
    profile_id: int,
    metadata: StatementMetadata,
) -> Account | None:
    """Suggest a unique active profile account from issuer and masked digits."""

    require_profile(session, profile_id)
    statement = select(Account).where(
        Account.profile_id == profile_id,
        Account.is_archived.is_(False),
        func.upper(Account.issuer) == metadata.issuer.upper(),
    )
    if metadata.account_last4 is not None:
        statement = statement.where(Account.last4 == metadata.account_last4)
    matches = list(session.scalars(statement.order_by(Account.id)))
    return matches[0] if len(matches) == 1 else None


def preview_import(
    session: Session,
    profile_id: int,
    account_id: int,
    document: ExtractedDocument,
    parser: StatementParser,
    *,
    fingerprint_key: bytes,
    cleanup: Cleanup | None = None,
    logger: logging.Logger | None = None,
) -> ImportPreviewResult:
    """Parse and persist a structured preview without creating ledger rows."""

    try:
        detection = parser.detect(document)
        if not detection.matched:
            raise ImportConflictError("statement layout is not supported")
        metadata = parser.extract_metadata(document)
        candidates = tuple(parser.extract_transactions(document))
        reconciliation = parser.reconcile(metadata, candidates)
        _validate_parser_result(metadata, candidates, reconciliation)
        _claim_import_preview(session, profile_id)
        account = require_account(session, profile_id, account_id)
        suggestion = suggest_import_account(session, profile_id, metadata)
        logical_key = _logical_statement_key(fingerprint_key, account_id, metadata)
        file_duplicate = session.scalar(
            select(ImportBatch)
            .where(
                ImportBatch.profile_id == profile_id,
                ImportBatch.file_sha256 == document.sha256.lower(),
                ImportBatch.status.not_in(("cancelled", "failed")),
                ImportBatch.duplicate_decision.not_in(
                    ("blocked_file_hash", "blocked_logical_key")
                ),
            )
            .order_by(ImportBatch.id)
        )
        logical_duplicate = session.scalar(
            select(ImportBatch)
            .where(
                ImportBatch.profile_id == profile_id,
                ImportBatch.logical_statement_key == logical_key,
                ImportBatch.status.not_in(("cancelled", "failed")),
                ImportBatch.duplicate_decision.not_in(
                    ("blocked_file_hash", "blocked_logical_key")
                ),
            )
            .order_by(ImportBatch.id)
        )
        duplicate = file_duplicate or logical_duplicate
        duplicate_decision = (
            "blocked_file_hash"
            if file_duplicate is not None
            else "blocked_logical_key"
            if logical_duplicate is not None
            else "new"
        )
        warning_values = _metadata_warnings(account, metadata)
        if reconciliation.status == "needs_review":
            warning_values.append(
                (
                    "statement_reconciliation_needs_review",
                    "warning",
                    "Parsed statement totals require review before commit.",
                    None,
                )
            )
        validation_status = (
            "needs_review"
            if reconciliation.status == "needs_review"
            else "validated_with_warnings"
            if warning_values
            else "validated"
        )
        with session.begin_nested():
            batch = ImportBatch(
                profile_id=profile_id,
                account_id=account_id,
                issuer=metadata.issuer,
                source_filename=document.sanitized_filename,
                file_sha256=document.sha256.lower(),
                logical_statement_key=logical_key,
                parser_name=parser.parser_name,
                parser_version=parser.parser_version,
                statement_start_date=metadata.period_start,
                statement_end_date=metadata.period_end,
                currency=metadata.currency,
                status="staged" if duplicate is not None else "ready",
                validation_status=validation_status,
                duplicate_decision=duplicate_decision,
                duplicate_of_import_id=duplicate.id if duplicate is not None else None,
                transaction_count=len(candidates),
                expected_total_cents=reconciliation.expected_cents,
                parsed_total_cents=reconciliation.parsed_cents,
                reconciliation_delta_cents=reconciliation.delta_cents,
                **_summaries(candidates),
            )
            session.add(batch)
            session.flush()
            if duplicate is None:
                overlaps = _stage_candidates(
                    session,
                    batch,
                    candidates,
                    fingerprint_key=fingerprint_key,
                )
                if overlaps:
                    batch.validation_status = "needs_review"
                    batch.duplicate_decision = "potential_overlap"
                    batch.unresolved_count = overlaps
                    warning_values.append(
                        (
                            "potential_transaction_overlap",
                            "warning",
                            "One or more rows may overlap existing ledger transactions.",
                            None,
                        )
                    )
            for code, severity, message, row_reference in warning_values:
                session.add(
                    ImportWarning(
                        profile_id=profile_id,
                        import_batch_id=batch.id,
                        code=code,
                        severity=severity,
                        message=message,
                        source_row_reference=row_reference,
                    )
                )
            session.flush()
        _log(
            logger,
            "statement_import_previewed",
            import_id=batch.id,
            profile_id=profile_id,
            account_id=account_id,
            transaction_count=batch.transaction_count,
            warning_count=len(warning_values),
            duplicate_decision=batch.duplicate_decision,
        )
        return ImportPreviewResult(
            batch=batch,
            suggested_account_id=suggestion.id if suggestion is not None else None,
        )
    except Exception:
        _log(logger, "statement_import_preview_failed", profile_id=profile_id)
        raise
    finally:
        if cleanup is not None:
            cleanup()


def require_import_batch(
    session: Session, profile_id: int, import_id: int
) -> ImportBatch:
    batch = session.scalar(
        select(ImportBatch)
        .where(
            ImportBatch.id == import_id,
            ImportBatch.profile_id == profile_id,
        )
        .execution_options(populate_existing=True)
    )
    if batch is None:
        raise ResourceNotFoundError("import not found")
    return batch


def commit_import(
    session: Session,
    profile_id: int,
    import_id: int,
    *,
    acknowledge_needs_review: bool = False,
    cleanup: Cleanup | None = None,
    logger: logging.Logger | None = None,
) -> ImportCommitResult:
    """Atomically and idempotently converge one preview into ledger rows."""

    batch: ImportBatch | None = None
    try:
        if cleanup is not None:
            terminal_cleanup = cleanup
            cleanup = None
            terminal_cleanup()
        _claim_import_commit(session, profile_id, import_id)
        batch = require_import_batch(session, profile_id, import_id)
        if batch.status == "committed":
            return _commit_result(session, batch)
        if batch.status in {"cancelled", "failed"}:
            raise ImportConflictError("import is already terminal")
        if batch.duplicate_decision in {"blocked_file_hash", "blocked_logical_key"}:
            raise ImportConflictError(
                f"statement duplicates import {batch.duplicate_of_import_id}"
            )
        if batch.validation_status == "needs_review" and not acknowledge_needs_review:
            raise ImportAcknowledgementRequiredError(
                "import needs review acknowledgement before commit"
            )
        staged_rows = list(
            session.scalars(
                select(ImportStagedTransaction)
                .where(
                    ImportStagedTransaction.profile_id == profile_id,
                    ImportStagedTransaction.import_batch_id == batch.id,
                    ImportStagedTransaction.account_id == batch.account_id,
                )
                .order_by(ImportStagedTransaction.id)
            )
        )
        try:
            result = _commit_rows_atomic(session, batch, staged_rows)
        except IntegrityError:
            # A concurrent commit can win after this preview's last exact-match
            # check. The unique fingerprint index is the database-backed claim;
            # retry only when its winner is now visible as an exact target.
            if not any(_exact_duplicate_target(session, row) for row in staged_rows):
                raise
            result = _commit_rows_atomic(session, batch, staged_rows)
        _log(
            logger,
            "statement_import_committed",
            import_id=batch.id,
            profile_id=profile_id,
            created_count=result.created_count,
            linked_duplicate_count=result.linked_duplicate_count,
        )
        return result
    except (
        ResourceNotFoundError,
        ImportConflictError,
        ImportAcknowledgementRequiredError,
    ):
        raise
    except Exception:
        if batch is not None and session.is_active:
            batch.status = "failed"
            session.flush()
        _log(
            logger,
            "statement_import_commit_failed",
            import_id=batch.id if batch is not None else import_id,
            profile_id=profile_id,
        )
        if batch is None:
            raise
        return ImportCommitResult(
            batch=batch,
            transactions=(),
            created_count=0,
            linked_duplicate_count=0,
            failure_code="commit_failed",
        )
    finally:
        if cleanup is not None:
            cleanup()


def cancel_import(
    session: Session,
    profile_id: int,
    import_id: int,
    *,
    cleanup: Cleanup | None = None,
    logger: logging.Logger | None = None,
) -> ImportBatch:
    """Idempotently cancel an uncommitted preview and discard staged rows."""

    try:
        if cleanup is not None:
            terminal_cleanup = cleanup
            cleanup = None
            terminal_cleanup()
        batch = require_import_batch(session, profile_id, import_id)
        if batch.status == "committed":
            raise ImportConflictError("committed import cannot be cancelled")
        if batch.status != "cancelled":
            batch.status = "cancelled"
            batch.staged_transactions.clear()
            batch.warnings.clear()
            session.flush()
        _log(
            logger,
            "statement_import_cancelled",
            import_id=batch.id,
            profile_id=profile_id,
        )
        return batch
    finally:
        if cleanup is not None:
            cleanup()


def _logical_statement_key(
    key: bytes, account_id: int, metadata: StatementMetadata
) -> str:
    canonical = "|".join(
        (
            metadata.issuer.upper(),
            metadata.account_last4 or "",
            metadata.period_start.isoformat() if metadata.period_start else "",
            metadata.period_end.isoformat() if metadata.period_end else "",
            metadata.currency,
        )
    ).encode("utf-8")
    logical_sha256 = hashlib.sha256(canonical).hexdigest()
    return statement_fingerprint(
        key=key, account_id=account_id, document_sha256=logical_sha256
    )


def _claim_import_commit(session: Session, profile_id: int, import_id: int) -> None:
    """Acquire the database writer claim before reading commit decisions.

    SQLite permits one writer. Starting with this scoped no-op update makes
    concurrent commits wait before they establish a stale read snapshot; the
    unique transaction-fingerprint index remains the final cross-database guard.
    """

    session.execute(
        update(ImportBatch)
        .where(
            ImportBatch.id == import_id,
            ImportBatch.profile_id == profile_id,
        )
        .values(updated_at=ImportBatch.updated_at)
        .execution_options(synchronize_session=False)
    )


def _claim_import_preview(session: Session, profile_id: int) -> None:
    """Serialize duplicate decisions for previews belonging to one profile."""

    session.execute(
        update(Profile)
        .where(Profile.id == profile_id)
        .values(updated_at=Profile.updated_at)
        .execution_options(synchronize_session=False)
    )


def _validate_parser_result(
    metadata: StatementMetadata,
    candidates: Sequence[TransactionCandidate],
    reconciliation: object,
) -> None:
    """Fail closed when a parser returns an internally inconsistent summary."""

    if not candidates:
        raise ImportConflictError("statement contains no importable transactions")
    source_indexes = [candidate.source_index for candidate in candidates]
    if len(set(source_indexes)) != len(source_indexes):
        raise ImportConflictError("statement transaction references are not unique")
    required = (
        "status",
        "expected_cents",
        "parsed_cents",
        "delta_cents",
        "tolerance_cents",
        "transaction_count",
    )
    if any(not hasattr(reconciliation, name) for name in required):
        raise ImportConflictError("statement reconciliation result is invalid")
    status = reconciliation.status
    expected = reconciliation.expected_cents
    parsed = reconciliation.parsed_cents
    delta = reconciliation.delta_cents
    tolerance = reconciliation.tolerance_cents
    transaction_count = reconciliation.transaction_count
    if status not in {"reconciled", "needs_review"}:
        raise ImportConflictError("statement reconciliation status is invalid")
    integer_values = (expected, parsed, delta, tolerance, transaction_count)
    if any(type(value) is not int for value in integer_values):
        raise ImportConflictError("statement reconciliation cents and counts must be integers")
    actual_parsed = sum(candidate.amount_cents for candidate in candidates)
    expected_from_metadata = metadata.expected_activity_cents or 0
    if (
        transaction_count != len(candidates)
        or parsed != actual_parsed
        or expected != expected_from_metadata
        or delta != parsed - expected
        or tolerance < 0
        or tolerance > 1
        or (status == "reconciled" and abs(delta) > tolerance)
    ):
        raise ImportConflictError("statement reconciliation result is inconsistent")


def _metadata_warnings(
    account: Account, metadata: StatementMetadata
) -> list[tuple[str, str, str, str | None]]:
    warnings: list[tuple[str, str, str, str | None]] = []
    if account.issuer.upper() != metadata.issuer.upper():
        warnings.append(
            (
                "selected_account_issuer_mismatch",
                "warning",
                "The selected account issuer differs from the statement issuer.",
                None,
            )
        )
    if (
        metadata.account_last4 is not None
        and account.last4 is not None
        and metadata.account_last4 != account.last4
    ):
        warnings.append(
            (
                "selected_account_mask_mismatch",
                "warning",
                "The selected account digits differ from the statement metadata.",
                None,
            )
        )
    return warnings


def _summaries(candidates: Sequence[TransactionCandidate]) -> dict[str, int]:
    purchases = [
        row for row in candidates if row.txn_type in {"purchase", "cash_advance"}
    ]
    credits = [row for row in candidates if row.txn_type in {"refund", "income"}]
    payments = [row for row in candidates if row.txn_type == "payment"]
    fee_interest = [
        row for row in candidates if row.txn_type in {"fee", "interest"}
    ]
    return {
        "purchase_count": len(purchases),
        "credit_count": len(credits),
        "payment_count": len(payments),
        "fee_interest_count": len(fee_interest),
        "purchase_total_cents": sum(row.amount_cents for row in purchases),
        "credit_total_cents": sum(row.amount_cents for row in credits),
        "payment_total_cents": sum(row.amount_cents for row in payments),
        "fee_interest_total_cents": sum(row.amount_cents for row in fee_interest),
    }


def _stage_candidates(
    session: Session,
    batch: ImportBatch,
    candidates: Sequence[TransactionCandidate],
    *,
    fingerprint_key: bytes,
) -> int:
    overlaps = 0
    for candidate in candidates:
        fingerprint = transaction_fingerprint(
            key=fingerprint_key,
            account_id=batch.account_id,
            transaction_date=candidate.transaction_date,
            posted_date=candidate.posted_date,
            raw_description=candidate.raw_description,
            amount_cents=candidate.amount_cents,
            occurrence_index=candidate.occurrence_index,
        )
        exact = session.scalar(
            select(Transaction).where(
                Transaction.profile_id == batch.profile_id,
                Transaction.account_id == batch.account_id,
                Transaction.transaction_fingerprint == fingerprint,
            )
        )
        potential = False
        if exact is None:
            same_money_rows = list(
                session.scalars(
                    select(Transaction).where(
                        Transaction.profile_id == batch.profile_id,
                        Transaction.account_id == batch.account_id,
                        Transaction.date == candidate.transaction_date,
                        Transaction.amount_cents == candidate.amount_cents,
                    )
                )
            )
            normalized = " ".join(candidate.raw_description.casefold().split())
            potential = any(
                " ".join(row.raw_description.casefold().split()) == normalized
                for row in same_money_rows
            )
        if potential:
            overlaps += 1
        included = default_included_for_type(candidate.txn_type)
        session.add(
            ImportStagedTransaction(
                profile_id=batch.profile_id,
                import_batch_id=batch.id,
                account_id=batch.account_id,
                source_row_reference=f"{batch.parser_name}:{candidate.source_index}",
                date=candidate.transaction_date,
                posted_date=candidate.posted_date,
                raw_description=candidate.raw_description,
                merchant="",
                amount_cents=candidate.amount_cents,
                currency=batch.currency,
                direction=candidate.direction,
                type=candidate.txn_type,
                included_in_spending=included,
                exclusion_reason=None if included else "transaction_type_policy",
                original_foreign_amount_cents=candidate.original_amount_cents,
                original_foreign_currency=candidate.original_currency,
                exchange_rate=candidate.exchange_rate,
                transaction_fingerprint=fingerprint,
                occurrence_index=candidate.occurrence_index,
                duplicate_decision=(
                    "skip_exact"
                    if exact is not None
                    else "potential_overlap"
                    if potential
                    else "new"
                ),
                status=(
                    "skipped"
                    if exact is not None
                    else "needs_review"
                    if potential
                    else "pending"
                ),
            )
        )
    session.flush()
    return overlaps


def _exact_duplicate_target(
    session: Session, staged: ImportStagedTransaction
) -> Transaction | None:
    return session.scalar(
        select(Transaction)
        .where(
            Transaction.profile_id == staged.profile_id,
            Transaction.account_id == staged.account_id,
            Transaction.transaction_fingerprint == staged.transaction_fingerprint,
        )
        .order_by(Transaction.id)
    )


def _commit_rows_atomic(
    session: Session,
    batch: ImportBatch,
    staged_rows: Sequence[ImportStagedTransaction],
) -> ImportCommitResult:
    """Create/link every row and construct the result in one savepoint."""

    with session.begin_nested():
        for staged in staged_rows:
            target = _exact_duplicate_target(session, staged)
            if target is not None:
                staged.duplicate_decision = "skip_exact"
                staged.status = "skipped"
                session.add(
                    ImportTransactionLink(
                        profile_id=batch.profile_id,
                        import_batch_id=batch.id,
                        account_id=batch.account_id,
                        staged_transaction_id=staged.id,
                        transaction_id=target.id,
                        decision="linked_duplicate",
                    )
                )
                continue
            transaction = create_imported_transaction(
                session, batch.profile_id, batch, staged
            )
            session.add(
                ImportTransactionLink(
                    profile_id=batch.profile_id,
                    import_batch_id=batch.id,
                    account_id=batch.account_id,
                    staged_transaction_id=staged.id,
                    transaction_id=transaction.id,
                    decision="created",
                )
            )
            staged.status = "accepted"
        batch.status = "committed"
        session.flush()
        return _commit_result(session, batch)


def _commit_result(session: Session, batch: ImportBatch) -> ImportCommitResult:
    links = list(
        session.scalars(
            select(ImportTransactionLink)
            .where(ImportTransactionLink.import_batch_id == batch.id)
            .order_by(ImportTransactionLink.id)
        )
    )
    transaction_ids = [link.transaction_id for link in links]
    transactions_by_id = (
        {
            transaction.id: transaction
            for transaction in session.scalars(
                select(Transaction).where(Transaction.id.in_(transaction_ids))
            )
        }
        if transaction_ids
        else {}
    )
    return ImportCommitResult(
        batch=batch,
        transactions=tuple(
            transactions_by_id[link.transaction_id]
            for link in links
            if link.transaction_id in transactions_by_id
        ),
        created_count=sum(link.decision == "created" for link in links),
        linked_duplicate_count=sum(
            link.decision == "linked_duplicate" for link in links
        ),
    )


def _log(logger: logging.Logger | None, event: str, **values: object) -> None:
    if logger is not None:
        try:
            logger.info(event, extra=values)
        except Exception:
            # Observability must never change ledger transaction semantics.
            pass
