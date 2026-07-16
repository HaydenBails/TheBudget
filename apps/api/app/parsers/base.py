"""Canonical interface implemented by issuer statement parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.importing.contracts import (
    ExtractedDocument,
    ParserDetection,
    ReconciliationResult,
    StatementMetadata,
    TransactionCandidate,
)


class StatementParser(ABC):
    """Typed lifecycle for detecting, extracting, and reconciling a statement."""

    parser_name: str
    parser_version: str

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for attribute in ("parser_name", "parser_version"):
            value = getattr(cls, attribute, None)
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"{attribute} must be a non-empty class string")

    @abstractmethod
    def detect(self, document: ExtractedDocument) -> ParserDetection:
        """Return whether this parser recognizes the validated document."""

    @abstractmethod
    def extract_metadata(self, document: ExtractedDocument) -> StatementMetadata:
        """Extract masked account and statement-period metadata."""

    @abstractmethod
    def extract_transactions(
        self, document: ExtractedDocument
    ) -> Sequence[TransactionCandidate]:
        """Extract canonical, ordered transactions from the document."""

    @abstractmethod
    def reconcile(
        self,
        metadata: StatementMetadata,
        transactions: Sequence[TransactionCandidate],
    ) -> ReconciliationResult:
        """Reconcile extracted rows against issuer-provided statement totals."""
