from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import threading
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import app.importing.document as document_module
from app.importing.contracts import (
    ExtractedDocument,
    ParserDetection,
    StatementMetadata,
    TransactionCandidate,
)
from app.importing.document import DocumentLimits, stage_pdf, stage_pdf_async
from app.importing.errors import (
    DocumentPageLimitError,
    DocumentTooLargeError,
    ExtractedTextLimitError,
    InvalidExchangeRateError,
    ScannedDocumentError,
    UnsupportedDocumentError,
)
from app.importing.fingerprints import (
    sha256_stream,
    statement_fingerprint,
    transaction_fingerprint,
)
from app.importing.reconciliation import parse_exchange_rate, reconcile_totals
from app.parsers import StatementParser


def _synthetic_pdf(*page_texts: str) -> bytes:
    """Create a tiny text PDF fixture without personal statement content."""

    page_count = len(page_texts)
    content_start = 3 + page_count
    font_object = content_start + page_count
    kids = " ".join(f"{3 + index} 0 R" for index in range(page_count))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode(),
    ]
    for index in range(page_count):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_object} 0 R >> >> "
                f"/Contents {content_start + index} 0 R >>"
            ).encode()
        )
    for text in page_texts:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode() if text else b""
        objects.append(
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(pdf)


def _candidate(amount_cents: int = 1234, *, index: int = 0) -> TransactionCandidate:
    return TransactionCandidate(
        source_index=index,
        occurrence_index=0,
        transaction_date=date(2026, 1, 2),
        posted_date=date(2026, 1, 3),
        raw_description="SYNTHETIC MERCHANT",
        amount_cents=amount_cents,
        txn_type="purchase",
        direction="debit" if amount_cents > 0 else "credit",
    )


def test_parser_contract_is_abstract_and_typed() -> None:
    with pytest.raises(TypeError):
        StatementParser()

    class SyntheticParser(StatementParser):
        parser_name = "synthetic"
        parser_version = "1"

        def detect(self, document: ExtractedDocument) -> ParserDetection:
            return ParserDetection(True, Decimal("1"), "synthetic_match")

        def extract_metadata(self, document: ExtractedDocument) -> StatementMetadata:
            return StatementMetadata("SYNTHETIC", "1234", None, None)

        def extract_transactions(
            self, document: ExtractedDocument
        ) -> tuple[TransactionCandidate, ...]:
            return (_candidate(),)

        def reconcile(self, metadata, transactions):  # type: ignore[no-untyped-def]
            return reconcile_totals(metadata.expected_activity_cents or 1234, transactions)

    document = ExtractedDocument("doc", "a" * 64, "safe.pdf", 10, 1, ("text",))
    parser = SyntheticParser()
    assert parser.detect(document).matched is True
    assert parser.extract_metadata(document).account_last4 == "1234"
    result = parser.reconcile(
        parser.extract_metadata(document), parser.extract_transactions(document)
    )
    assert result.status == "reconciled"

    with pytest.raises(TypeError, match="parser_name"):

        class InvalidParser(StatementParser):
            parser_name = ""
            parser_version = "1"


def test_contracts_reject_full_account_number_and_non_integer_money() -> None:
    with pytest.raises(ValueError, match="four digits"):
        StatementMetadata("SYNTHETIC", "1234567890123456", None, None)
    with pytest.raises(TypeError, match="integer cents"):
        _candidate(12.34)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Decimal"):
        ParserDetection(True, 1.0, "match")  # type: ignore[arg-type]
    assert "SYNTHETIC MERCHANT" not in repr(_candidate())
    assert "1234" not in repr(StatementMetadata("SYNTHETIC", "1234", None, None))
    assert "safe.pdf" not in repr(ExtractedDocument("doc", "a" * 64, "safe.pdf", 1, 1, ("x",)))


def test_candidate_validates_enums_and_coupled_fixed_precision_foreign_values() -> None:
    values = {
        "source_index": 0,
        "occurrence_index": 0,
        "transaction_date": date(2026, 1, 2),
        "posted_date": None,
        "raw_description": "SYNTHETIC",
        "amount_cents": 100,
        "txn_type": "purchase",
        "direction": "debit",
    }
    with pytest.raises(ValueError, match="txn_type"):
        TransactionCandidate(**(values | {"txn_type": "unknown"}))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="supplied together"):
        TransactionCandidate(**values, original_currency="USD")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at most 8"):
        TransactionCandidate(
            **values,
            original_currency="USD",
            original_amount_cents=75,
            exchange_rate=Decimal("1.123456789"),
        )  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", Decimal("1.00000000")),
        ("1.25", Decimal("1.25000000")),
        ("0.00000001", Decimal("0.00000001")),
    ],
)
def test_exchange_rates_use_fixed_decimal_precision(value: str, expected: Decimal) -> None:
    assert parse_exchange_rate(value) == expected


@pytest.mark.parametrize("value", [1.25, "1e-2", "1.123456789", "0", "-1", " 1.2"])
def test_exchange_rates_reject_float_ambiguous_or_excess_precision(value: object) -> None:
    with pytest.raises(InvalidExchangeRateError):
        parse_exchange_rate(value)  # type: ignore[arg-type]


def test_reconciliation_uses_exact_signed_integer_cents_and_one_cent_tolerance() -> None:
    exact = reconcile_totals(1200, (_candidate(1234), _candidate(-34, index=1)))
    within_tolerance = reconcile_totals(1199, (_candidate(1200),))
    mismatch = reconcile_totals(1198, (_candidate(1200),))
    assert (exact.status, exact.delta_cents, exact.transaction_count) == ("reconciled", 0, 2)
    assert (within_tolerance.status, within_tolerance.delta_cents) == ("reconciled", 1)
    assert (mismatch.status, mismatch.delta_cents) == ("needs_review", 2)
    with pytest.raises(TypeError, match="integer cents"):
        reconcile_totals(12.0, ())  # type: ignore[arg-type]


class _TrackedStream(io.BytesIO):
    def __init__(self, value: bytes) -> None:
        super().__init__(value)
        self.requested_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.requested_sizes.append(size)
        return super().read(size)


def test_sha256_is_streamed_in_bounded_chunks() -> None:
    content = b"abcdef" * 100
    stream = _TrackedStream(content)
    assert sha256_stream(stream, chunk_size=17) == hashlib.sha256(content).hexdigest()
    assert stream.requested_sizes
    assert set(stream.requested_sizes) == {17}


def test_fingerprints_are_deterministic_non_reversible_and_preserve_occurrences() -> None:
    key = b"local-test-key-material-is-at-least-32-bytes"
    statement = statement_fingerprint(key=key, account_id=7, document_sha256="a" * 64)
    first = transaction_fingerprint(
        key=key,
        account_id=7,
        transaction_date=date(2026, 1, 2),
        posted_date=None,
        raw_description="Synthetic   Merchant",
        amount_cents=1234,
        occurrence_index=0,
    )
    normalized = transaction_fingerprint(
        key=key,
        account_id=7,
        transaction_date=date(2026, 1, 2),
        posted_date=None,
        raw_description=" synthetic merchant ",
        amount_cents=1234,
        occurrence_index=0,
    )
    repeated = transaction_fingerprint(
        key=key,
        account_id=7,
        transaction_date=date(2026, 1, 2),
        posted_date=None,
        raw_description="Synthetic Merchant",
        amount_cents=1234,
        occurrence_index=1,
    )
    assert first == normalized
    assert repeated != first
    assert statement_fingerprint(
        key=b"another-local-key-material-at-least-32-bytes",
        account_id=7,
        document_sha256="a" * 64,
    ) != statement
    assert all(len(value) == 64 for value in (statement, first, repeated))
    assert "merchant" not in first
    with pytest.raises(ValueError, match="at least 32"):
        statement_fingerprint(key=b"short", account_id=7, document_sha256="a" * 64)


def test_text_pdf_is_server_staged_sanitized_logged_safely_and_cleaned(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pdf = _synthetic_pdf("SYNTHETIC STATEMENT TOTAL 12.34")
    logger = logging.getLogger("import-test")
    caplog.set_level(logging.INFO, logger="import-test")
    filename = r"C:\private\9999888877776666.pdf"
    with stage_pdf(
        io.BytesIO(pdf),
        filename=filename,
        content_type="application/pdf",
        temp_root=tmp_path,
        logger=logger,
    ) as document:
        assert document.sanitized_filename == "[redacted].pdf"
        assert document.pages == ("SYNTHETIC STATEMENT TOTAL 12.34",)
        assert document.sha256 == hashlib.sha256(pdf).hexdigest()
        staged_directories = tuple(tmp_path.iterdir())
        assert len(staged_directories) == 1
        assert staged_directories[0].is_dir()
    assert tuple(tmp_path.iterdir()) == ()
    assert "9999888877776666" not in caplog.text
    assert "SYNTHETIC STATEMENT" not in caplog.text
    assert "private" not in caplog.text


def test_filename_removes_bidi_controls_and_redacts_long_digit_runs(tmp_path: Path) -> None:
    with stage_pdf(
        io.BytesIO(_synthetic_pdf("SYNTHETIC")),
        filename="safe\u202e123456789.pdf",
        content_type="application/pdf",
        temp_root=tmp_path,
    ) as document:
        assert document.sanitized_filename == "safe[redacted].pdf"


def test_server_temp_path_is_cleaned_when_consumer_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="synthetic consumer failure"):
        with stage_pdf(
            io.BytesIO(_synthetic_pdf("SYNTHETIC TEXT")),
            filename="statement.pdf",
            content_type="application/pdf",
            temp_root=tmp_path,
        ):
            raise RuntimeError("synthetic consumer failure")
    assert tuple(tmp_path.iterdir()) == ()


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("statement.txt", "application/pdf", _synthetic_pdf("TEXT")),
        ("statement.pdf", "text/plain", _synthetic_pdf("TEXT")),
        ("statement.pdf", "application/pdf", b"not-a-pdf"),
        ("statement.pdf", "application/pdf", b"%PDF-1.4 malformed"),
    ],
)
def test_extension_mime_and_pdf_magic_are_required(
    tmp_path: Path, filename: str, content_type: str, content: bytes
) -> None:
    with pytest.raises(UnsupportedDocumentError):
        with stage_pdf(
            io.BytesIO(content),
            filename=filename,
            content_type=content_type,
            temp_root=tmp_path,
        ):
            pass
    assert tuple(tmp_path.iterdir()) == ()


def test_size_page_and_scanned_document_limits_are_actionable_and_cleaned(tmp_path: Path) -> None:
    pdf = _synthetic_pdf("PAGE ONE", "PAGE TWO")
    with pytest.raises(DocumentTooLargeError, match="byte limit"):
        with stage_pdf(
            io.BytesIO(pdf),
            filename="statement.pdf",
            content_type="application/pdf",
            limits=DocumentLimits(max_bytes=10),
            temp_root=tmp_path,
        ):
            pass
    with pytest.raises(DocumentPageLimitError, match="maximum is 1"):
        with stage_pdf(
            io.BytesIO(pdf),
            filename="statement.pdf",
            content_type="application/pdf",
            limits=DocumentLimits(max_pages=1),
            temp_root=tmp_path,
        ):
            pass
    with pytest.raises(ScannedDocumentError, match="text-based PDF"):
        with stage_pdf(
            io.BytesIO(_synthetic_pdf("")),
            filename="statement.pdf",
            content_type="application/pdf",
            temp_root=tmp_path,
        ):
            pass
    with pytest.raises(ExtractedTextLimitError, match="character limit"):
        with stage_pdf(
            io.BytesIO(_synthetic_pdf("EXPANDED SYNTHETIC TEXT")),
            filename="statement.pdf",
            content_type="application/pdf",
            limits=DocumentLimits(max_extracted_chars=5),
            temp_root=tmp_path,
        ):
            pass
    assert tuple(tmp_path.iterdir()) == ()


def test_async_staging_cleans_server_temp_path_on_cancellation(tmp_path: Path) -> None:
    class CancelledUpload:
        async def read(self, size: int = -1) -> bytes:
            raise asyncio.CancelledError

    async def run() -> None:
        async with stage_pdf_async(
            CancelledUpload(),
            filename="statement.pdf",
            content_type="application/pdf",
            temp_root=tmp_path,
        ):
            pytest.fail("cancelled upload must not yield a document")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run())
    assert tuple(tmp_path.iterdir()) == ()


def test_async_pdf_traversal_is_off_loop_and_cancellation_waits_for_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = threading.Event()
    processes: list[object] = []

    class NeverConnection:
        def poll(self, timeout: float = 0) -> bool:
            return False

        def close(self) -> None:
            pass

    def start_never_releasing_process(kwargs: dict[str, object]):
        context = document_module.multiprocessing.get_context("spawn")
        process = context.Process(target=time.sleep, args=(60,), daemon=True)
        process.start()
        processes.append(process)
        started.set()
        return process, NeverConnection()

    monkeypatch.setattr(
        document_module, "_start_extraction_process", start_never_releasing_process
    )

    class Upload:
        def __init__(self) -> None:
            self.stream = io.BytesIO(_synthetic_pdf("SYNTHETIC"))

        async def read(self, size: int = -1) -> bytes:
            return self.stream.read(size)

    async def run() -> None:
        async def consume() -> None:
            async with stage_pdf_async(
                Upload(),
                filename="statement.pdf",
                content_type="application/pdf",
                temp_root=tmp_path,
            ):
                pass

        task = asyncio.create_task(consume())
        while not started.is_set():
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not task.done()
        task.cancel()
        cancellation_started = time.monotonic()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=0.5)
        assert time.monotonic() - cancellation_started < 0.5

    asyncio.run(run())
    assert tuple(tmp_path.iterdir()) == ()
    assert processes and all(not process.is_alive() for process in processes)  # type: ignore[attr-defined]


def test_sync_extraction_timeout_terminates_never_releasing_worker_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    processes: list[object] = []

    class NeverConnection:
        def poll(self, timeout: float = 0) -> bool:
            if timeout:
                time.sleep(min(timeout, 0.01))
            return False

        def close(self) -> None:
            pass

    def start_never_releasing_process(kwargs: dict[str, object]):
        context = document_module.multiprocessing.get_context("spawn")
        process = context.Process(target=time.sleep, args=(60,), daemon=True)
        process.start()
        processes.append(process)
        return process, NeverConnection()

    monkeypatch.setattr(
        document_module, "_start_extraction_process", start_never_releasing_process
    )

    started_at = time.monotonic()
    with pytest.raises(document_module.DocumentExtractionTimeoutError):
        with stage_pdf(
            io.BytesIO(_synthetic_pdf("SYNTHETIC")),
            filename="statement.pdf",
            content_type="application/pdf",
            limits=DocumentLimits(extraction_timeout_seconds=0.05),
            temp_root=tmp_path,
        ):
            pytest.fail("timed-out extraction must not yield")
    # The bounded terminate/join cleanup path allows up to one second per join.
    # Keep a hard availability bound without making the test scheduler-sensitive.
    assert time.monotonic() - started_at < 2.5
    assert tuple(tmp_path.iterdir()) == ()
    assert processes and all(not process.is_alive() for process in processes)  # type: ignore[attr-defined]
