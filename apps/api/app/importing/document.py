"""Privacy-safe, bounded extraction of text-based statement PDFs."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import multiprocessing
import re
import tempfile
import time
import unicodedata
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from uuid import uuid4

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.psparser import PSException

from app.importing.contracts import ExtractedDocument
from app.importing.errors import (
    DocumentExtractionTimeoutError,
    DocumentPageLimitError,
    DocumentTooLargeError,
    ExtractedTextLimitError,
    ImportingError,
    ScannedDocumentError,
    UnsupportedDocumentError,
)

PDF_MIME_TYPE = "application/pdf"
PDF_MAGIC = b"%PDF-"


@dataclass(frozen=True, slots=True)
class DocumentLimits:
    """Resource limits applied before parser-specific work begins."""

    max_bytes: int = 15 * 1024 * 1024
    max_pages: int = 20
    max_extracted_chars: int = 2_000_000
    chunk_size: int = 64 * 1024
    extraction_timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        if (
            self.max_bytes <= 0
            or self.max_pages <= 0
            or self.max_extracted_chars <= 0
            or self.chunk_size <= 0
            or not math.isfinite(self.extraction_timeout_seconds)
            or self.extraction_timeout_seconds <= 0
        ):
            raise ValueError("document limits must be positive")


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


class Digest(Protocol):
    def update(self, value: bytes) -> None: ...


def sanitize_filename(filename: str) -> str:
    """Discard any client path and retain a display-safe basename only."""

    basename = PurePosixPath(filename.replace("\\", "/")).name.strip()
    cleaned = "".join(
        character
        for character in basename
        if character.isprintable() and unicodedata.category(character) != "Cf"
    )
    cleaned = re.sub(r"\d{6,}", "[redacted]", cleaned)
    return cleaned[:255] or "statement.pdf"


def _validate_boundary(filename: str, content_type: str) -> str:
    safe_name = sanitize_filename(filename)
    if Path(safe_name).suffix.casefold() != ".pdf":
        raise UnsupportedDocumentError("statement must use the .pdf extension")
    normalized_mime = content_type.partition(";")[0].strip().casefold()
    if normalized_mime != PDF_MIME_TYPE:
        raise UnsupportedDocumentError("statement content type must be application/pdf")
    return safe_name


def _extract_document(
    path: Path,
    *,
    document_id: str,
    sha256: str,
    sanitized_filename: str,
    byte_count: int,
    limits: DocumentLimits,
) -> ExtractedDocument:
    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            if page_count > limits.max_pages:
                raise DocumentPageLimitError(
                    f"statement has {page_count} pages; maximum is {limits.max_pages}"
                )
            extracted_pages: list[str] = []
            extracted_chars = 0
            for page in pdf.pages:
                text = (page.extract_text() or "").strip()
                extracted_chars += len(text)
                if extracted_chars > limits.max_extracted_chars:
                    raise ExtractedTextLimitError(
                        "statement extracted text exceeds the configured character limit"
                    )
                extracted_pages.append(text)
            pages = tuple(extracted_pages)
    except DocumentPageLimitError:
        raise
    except ExtractedTextLimitError:
        raise
    except (PDFSyntaxError, PSException, OSError) as exc:
        del exc
        raise UnsupportedDocumentError("statement PDF is malformed or unreadable") from None
    if not any(pages):
        raise ScannedDocumentError(
            "statement contains no extractable text; export a text-based PDF instead of a scan"
        )
    return ExtractedDocument(
        document_id=document_id,
        sha256=sha256,
        sanitized_filename=sanitized_filename,
        byte_count=byte_count,
        page_count=page_count,
        pages=pages,
    )


def _write_chunk(
    destination: BinaryIO,
    chunk: bytes,
    *,
    digest: Digest,
    byte_count: int,
    limits: DocumentLimits,
) -> int:
    if not isinstance(chunk, bytes):
        raise UnsupportedDocumentError("statement stream must provide bytes")
    byte_count += len(chunk)
    if byte_count > limits.max_bytes:
        raise DocumentTooLargeError(
            f"statement exceeds the configured {limits.max_bytes}-byte limit"
        )
    destination.write(chunk)
    digest.update(chunk)
    return byte_count


def _validate_magic(path: Path) -> None:
    with path.open("rb") as stream:
        if stream.read(len(PDF_MAGIC)) != PDF_MAGIC:
            raise UnsupportedDocumentError("statement content is not a PDF")


def _extraction_worker(connection: Connection, kwargs: dict[str, object]) -> None:
    try:
        connection.send(("ok", _extract_document(**kwargs)))
    except ImportingError as exc:
        connection.send(("import_error", exc))
    except BaseException:
        connection.send(("error", None))
    finally:
        connection.close()


def _start_extraction_process(
    kwargs: dict[str, object],
) -> tuple[BaseProcess, Connection]:
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=_extraction_worker, args=(sending, kwargs), daemon=True)
    process.start()
    sending.close()
    return process, receiving


def _stop_process(process: BaseProcess) -> None:
    if process.is_alive():
        process.terminate()
    process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join(timeout=1)


def _receive_extraction(connection: Connection) -> ExtractedDocument:
    status, payload = connection.recv()
    if status == "ok" and isinstance(payload, ExtractedDocument):
        return payload
    if status == "import_error" and isinstance(payload, ImportingError):
        raise payload
    raise UnsupportedDocumentError("statement PDF could not be safely extracted")


def _extract_document_bounded(**kwargs: object) -> ExtractedDocument:
    limits = kwargs["limits"]
    assert isinstance(limits, DocumentLimits)
    process, connection = _start_extraction_process(dict(kwargs))
    deadline = time.monotonic() + limits.extraction_timeout_seconds
    try:
        while time.monotonic() < deadline:
            if connection.poll(0.01):
                return _receive_extraction(connection)
            if not process.is_alive():
                break
        raise DocumentExtractionTimeoutError(
            "statement PDF extraction exceeded the configured time limit"
        )
    finally:
        connection.close()
        _stop_process(process)


async def _extract_document_bounded_async(**kwargs: object) -> ExtractedDocument:
    limits = kwargs["limits"]
    assert isinstance(limits, DocumentLimits)
    process, connection = _start_extraction_process(dict(kwargs))
    deadline = time.monotonic() + limits.extraction_timeout_seconds
    try:
        while time.monotonic() < deadline:
            if connection.poll():
                return _receive_extraction(connection)
            if not process.is_alive():
                break
            await asyncio.sleep(0.01)
        raise DocumentExtractionTimeoutError(
            "statement PDF extraction exceeded the configured time limit"
        )
    finally:
        connection.close()
        _stop_process(process)


@contextmanager
def stage_pdf(
    stream: BinaryIO,
    *,
    filename: str,
    content_type: str,
    limits: DocumentLimits | None = None,
    temp_root: Path | None = None,
    logger: logging.Logger | None = None,
) -> Iterator[ExtractedDocument]:
    """Stage and extract a synchronous upload, deleting raw bytes on every exit."""

    effective_limits = limits or DocumentLimits()
    safe_name = _validate_boundary(filename, content_type)
    document_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="statement-", dir=temp_root) as directory:
        path = Path(directory) / "upload.pdf"
        digest = hashlib.sha256()
        byte_count = 0
        with path.open("wb") as destination:
            while chunk := stream.read(effective_limits.chunk_size):
                byte_count = _write_chunk(
                    destination,
                    chunk,
                    digest=digest,
                    byte_count=byte_count,
                    limits=effective_limits,
                )
        _validate_magic(path)
        document = _extract_document_bounded(
            path=path,
            document_id=document_id,
            sha256=digest.hexdigest(),
            sanitized_filename=safe_name,
            byte_count=byte_count,
            limits=effective_limits,
        )
        if logger is not None:
            logger.info(
                "statement_document_staged",
                extra={
                    "document_id": document_id,
                    "byte_count": byte_count,
                    "page_count": document.page_count,
                },
            )
        yield document


@asynccontextmanager
async def stage_pdf_async(
    stream: AsyncReadable,
    *,
    filename: str,
    content_type: str,
    limits: DocumentLimits | None = None,
    temp_root: Path | None = None,
    logger: logging.Logger | None = None,
) -> AsyncIterator[ExtractedDocument]:
    """Stage an async upload with cleanup on success, failure, or cancellation."""

    effective_limits = limits or DocumentLimits()
    safe_name = _validate_boundary(filename, content_type)
    document_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="statement-", dir=temp_root) as directory:
        path = Path(directory) / "upload.pdf"
        digest = hashlib.sha256()
        byte_count = 0
        try:
            with path.open("wb") as destination:
                while chunk := await stream.read(effective_limits.chunk_size):
                    byte_count = _write_chunk(
                        destination,
                        chunk,
                        digest=digest,
                        byte_count=byte_count,
                        limits=effective_limits,
                    )
        except asyncio.CancelledError:
            raise
        _validate_magic(path)
        document = await _extract_document_bounded_async(
            path=path,
            document_id=document_id,
            sha256=digest.hexdigest(),
            sanitized_filename=safe_name,
            byte_count=byte_count,
            limits=effective_limits,
        )
        if logger is not None:
            logger.info(
                "statement_document_staged",
                extra={
                    "document_id": document_id,
                    "byte_count": byte_count,
                    "page_count": document.page_count,
                },
            )
        yield document
