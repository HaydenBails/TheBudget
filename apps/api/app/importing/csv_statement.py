"""Privacy-safe, bounded extraction of statement activity exports (.csv).

A bank CSV export is already structured, so extraction reads the delimited rows
into a bounded in-memory grid rather than pulling free text. Raw upload bytes
are written to a server-owned temp file and deleted on every exit, and only the
sha256 + a redacted filename outlive the request.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import logging
import tempfile
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.importing.document import (
    AsyncReadable,
    DocumentLimits,
    _write_chunk,
    sanitize_filename,
)
from app.importing.errors import UnsupportedDocumentError

CSV_MIME_TYPES = frozenset(
    {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        "text/plain",
        "",
    }
)
_MAX_ROWS = 20_000
_MAX_COLS = 24
# NUL bytes indicate a binary upload masquerading as .csv.
_NUL = b"\x00"


@dataclass(frozen=True, slots=True, repr=False)
class ExtractedCsv:
    """Ephemeral, bounded delimited grid extracted from one validated .csv."""

    document_id: str
    sha256: str
    sanitized_filename: str
    byte_count: int
    row_count: int
    rows: tuple[tuple[str, ...], ...] = field(repr=False)


def _validate_boundary(filename: str, content_type: str) -> str:
    safe_name = sanitize_filename(filename)
    if Path(safe_name).suffix.casefold() != ".csv":
        raise UnsupportedDocumentError("statement must use the .csv extension")
    normalized_mime = content_type.partition(";")[0].strip().casefold()
    if normalized_mime not in CSV_MIME_TYPES:
        raise UnsupportedDocumentError(
            "statement content type must be a comma-separated .csv export"
        )
    return safe_name


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    if _NUL in raw:
        raise UnsupportedDocumentError("statement content is not a text .csv export")
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnsupportedDocumentError("statement .csv is not decodable text")


def _extract_rows(
    path: Path,
    *,
    document_id: str,
    sha256: str,
    sanitized_filename: str,
    byte_count: int,
) -> ExtractedCsv:
    text = _decode(path)
    rows: list[tuple[str, ...]] = []
    reader = csv.reader(text.splitlines())
    try:
        for index, row in enumerate(reader):
            if index >= _MAX_ROWS:
                break
            trimmed = tuple(cell.strip() for cell in row[:_MAX_COLS])
            if any(trimmed):
                rows.append(trimmed)
    except csv.Error:
        raise UnsupportedDocumentError("statement .csv is malformed") from None
    if not rows:
        raise UnsupportedDocumentError("statement .csv has no readable rows")
    return ExtractedCsv(
        document_id=document_id,
        sha256=sha256,
        sanitized_filename=sanitized_filename,
        byte_count=byte_count,
        row_count=len(rows),
        rows=tuple(rows),
    )


def _stage(
    path: Path,
    *,
    filename: str,
    content_type: str,
    document_id: str,
    digest: hashlib._Hash,
    byte_count: int,
) -> ExtractedCsv:
    safe_name = _validate_boundary(filename, content_type)
    return _extract_rows(
        path,
        document_id=document_id,
        sha256=digest.hexdigest(),
        sanitized_filename=safe_name,
        byte_count=byte_count,
    )


@contextmanager
def stage_csv(
    stream: BinaryIO,
    *,
    filename: str,
    content_type: str,
    limits: DocumentLimits | None = None,
    temp_root: Path | None = None,
    logger: logging.Logger | None = None,
) -> Iterator[ExtractedCsv]:
    """Stage and extract a synchronous .csv upload, deleting bytes on exit."""

    effective_limits = limits or DocumentLimits()
    _validate_boundary(filename, content_type)
    document_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="statement-", dir=temp_root) as directory:
        path = Path(directory) / "upload.csv"
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
        extracted = _stage(
            path,
            filename=filename,
            content_type=content_type,
            document_id=document_id,
            digest=digest,
            byte_count=byte_count,
        )
        if logger is not None:
            logger.info(
                "statement_csv_staged",
                extra={
                    "document_id": document_id,
                    "byte_count": byte_count,
                    "row_count": extracted.row_count,
                },
            )
        yield extracted


@asynccontextmanager
async def stage_csv_async(
    stream: AsyncReadable,
    *,
    filename: str,
    content_type: str,
    limits: DocumentLimits | None = None,
    temp_root: Path | None = None,
    logger: logging.Logger | None = None,
) -> AsyncIterator[ExtractedCsv]:
    """Stage an async .csv upload with cleanup on success, failure, or cancel."""

    effective_limits = limits or DocumentLimits()
    _validate_boundary(filename, content_type)
    document_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="statement-", dir=temp_root) as directory:
        path = Path(directory) / "upload.csv"
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
        extracted = _stage(
            path,
            filename=filename,
            content_type=content_type,
            document_id=document_id,
            digest=digest,
            byte_count=byte_count,
        )
        if logger is not None:
            logger.info(
                "statement_csv_staged",
                extra={
                    "document_id": document_id,
                    "byte_count": byte_count,
                    "row_count": extracted.row_count,
                },
            )
        yield extracted
