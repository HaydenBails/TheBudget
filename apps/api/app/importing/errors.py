"""Typed, user-actionable statement import errors."""

from __future__ import annotations


class ImportingError(ValueError):
    """Base class for safe statement-import failures."""

    code = "statement_import_error"


class UnsupportedDocumentError(ImportingError):
    """The supplied document is not a supported text PDF."""

    code = "unsupported_document"


class DocumentTooLargeError(ImportingError):
    """The supplied document exceeds the configured byte limit."""

    code = "document_too_large"


class DocumentPageLimitError(ImportingError):
    """The supplied document exceeds the configured page limit."""

    code = "document_page_limit"


class ExtractedTextLimitError(ImportingError):
    """Extracted text exceeds the configured expansion limit."""

    code = "extracted_text_limit"


class DocumentExtractionTimeoutError(ImportingError):
    """PDF traversal exceeded the configured processing time."""

    code = "document_extraction_timeout"


class ScannedDocumentError(ImportingError):
    """The PDF has no extractable text and is likely scanned/image-only."""

    code = "scanned_document"


class InvalidExchangeRateError(ImportingError):
    """An exchange-rate value is ambiguous or exceeds fixed precision."""

    code = "invalid_exchange_rate"


class ReconciliationError(ImportingError):
    """Statement and parsed transaction totals cannot be reconciled."""

    code = "reconciliation_error"
