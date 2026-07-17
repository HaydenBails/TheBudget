"""Issuer-detecting statement-parser resolver.

Given an extracted document, run each registered parser's deterministic
``detect`` and return the highest-confidence match. This replaces hardcoding a
single issuer at the API boundary so a preview auto-selects TD or Amex, and any
future issuer becomes a one-line registration.
"""

from __future__ import annotations

from app.importing.contracts import ExtractedDocument
from app.importing.errors import ScannedDocumentError, UnsupportedDocumentError
from app.parsers.amex import AmexCreditCardParser
from app.parsers.base import StatementParser
from app.parsers.td import TdCreditCardParser

# Registration order is the deterministic tie-breaker for equal confidence.
_PARSER_FACTORIES = (TdCreditCardParser, AmexCreditCardParser)


def available_parsers() -> tuple[StatementParser, ...]:
    """Instantiate every registered issuer parser."""

    return tuple(factory() for factory in _PARSER_FACTORIES)


def resolve_parser(document: ExtractedDocument) -> StatementParser:
    """Return the best-matching parser, or fail closed with a readable error.

    A document with no extractable text raises ``ScannedDocumentError``; a
    text document that no issuer parser recognises raises
    ``UnsupportedDocumentError``.
    """

    best: tuple[object, StatementParser] | None = None
    any_text = False
    for parser in available_parsers():
        detection = parser.detect(document)
        if detection.reason_code != "no_extractable_text":
            any_text = True
        if not detection.matched:
            continue
        if best is None or detection.confidence > best[0]:
            best = (detection.confidence, parser)
    if best is not None:
        return best[1]
    if not any_text:
        raise ScannedDocumentError(
            "statement contains no extractable text; use a text-based PDF"
        )
    raise UnsupportedDocumentError("statement issuer or layout is not supported")
