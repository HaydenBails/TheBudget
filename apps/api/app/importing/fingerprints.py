"""Non-reversible, deterministic statement and transaction fingerprints."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Iterable
from datetime import date
from typing import BinaryIO


def sha256_stream(stream: BinaryIO, *, chunk_size: int = 64 * 1024) -> str:
    """Hash a binary stream incrementally without retaining its bytes."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    while chunk := stream.read(chunk_size):
        digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(key: bytes, namespace: str, values: Iterable[object]) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("fingerprint key must contain at least 32 bytes")
    digest = hmac.new(key, namespace.encode("ascii"), hashlib.sha256)
    for value in values:
        encoded = str(value).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def statement_fingerprint(*, key: bytes, account_id: int, document_sha256: str) -> str:
    """Identify one account statement without exposing its source values."""

    if type(account_id) is not int or account_id <= 0:
        raise ValueError("account_id must be a positive integer")
    if re.fullmatch(r"[0-9a-fA-F]{64}", document_sha256) is None:
        raise ValueError("document_sha256 must be a hexadecimal SHA-256 digest")
    return _canonical_digest(key, "statement-v1", (account_id, document_sha256.lower()))


def transaction_fingerprint(
    *,
    key: bytes,
    account_id: int,
    transaction_date: date,
    posted_date: date | None,
    raw_description: str,
    amount_cents: int,
    occurrence_index: int,
) -> str:
    """Identify a row while preserving repeated legitimate occurrences."""

    if type(account_id) is not int or account_id <= 0:
        raise ValueError("account_id must be a positive integer")
    if type(amount_cents) is not int:
        raise TypeError("amount_cents must be integer cents")
    if type(occurrence_index) is not int or occurrence_index < 0:
        raise ValueError("occurrence_index must be a non-negative integer")
    normalized_description = " ".join(raw_description.casefold().split())
    return _canonical_digest(
        key,
        "transaction-v1",
        (
            account_id,
            transaction_date.isoformat(),
            posted_date.isoformat() if posted_date else "",
            normalized_description,
            amount_cents,
            occurrence_index,
        ),
    )
