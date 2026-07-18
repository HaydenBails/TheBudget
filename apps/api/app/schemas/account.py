"""Validation and response schemas for credit-card accounts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import TimestampedRead

DisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
CardColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
LastDigits = Annotated[str, StringConstraints(pattern=r"^\d{4,5}$")]
AccountFingerprint = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class IssuerCode(StrEnum):
    """Supported statement issuers."""

    TD = "TD"
    AMEX = "AMEX"
    CIBC = "CIBC"
    OTHER = "OTHER"


AccountKind = Literal["asset", "liability"]
BalanceCents = Annotated[int, Field(ge=-(1 << 53) + 1, le=(1 << 53) - 1)]


class AccountCreate(BaseModel):
    """Fields accepted when creating an account under a scoped profile."""

    model_config = ConfigDict(extra="forbid")

    issuer: IssuerCode
    display_name: DisplayName
    color: CardColor
    last4: LastDigits | None = None
    currency: Literal["CAD"] = "CAD"
    account_fingerprint: AccountFingerprint | None = None
    kind: AccountKind = "liability"
    current_balance_cents: BalanceCents | None = None


class AccountUpdate(BaseModel):
    """Mutable account fields; omission leaves the stored value unchanged."""

    model_config = ConfigDict(extra="forbid")

    issuer: IssuerCode | None = None
    display_name: DisplayName | None = None
    color: CardColor | None = None
    last4: LastDigits | None = None
    account_fingerprint: AccountFingerprint | None = None
    kind: AccountKind | None = None
    current_balance_cents: BalanceCents | None = None
    is_archived: bool | None = None


class AccountRead(TimestampedRead):
    """Serialized persisted account with explicit profile ownership."""

    profile_id: int
    issuer: IssuerCode
    display_name: str
    color: str
    last4: str | None
    currency: Literal["CAD"]
    account_fingerprint: str | None
    kind: AccountKind
    current_balance_cents: int | None
    is_archived: bool
