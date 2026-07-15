"""Validation and JSON serialization tests for profile/account schemas."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import Account, Profile
from app.schemas import AccountCreate, AccountRead, IssuerCode, ProfileCreate, ProfileRead


def test_create_schemas_normalize_names_and_validate_masked_fields() -> None:
    profile = ProfileCreate(name="  Personal  ")
    account = AccountCreate(
        issuer="AMEX",
        display_name="  Cobalt  ",
        color="#2f6FED",
        last4="71007",
    )

    assert profile.name == "Personal"
    assert profile.base_currency == "CAD"
    assert account.issuer is IssuerCode.AMEX
    assert account.display_name == "Cobalt"
    assert account.last4 == "71007"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("issuer", "VISA"),
        ("color", "blue"),
        ("last4", "123"),
        ("last4", "123456"),
        ("last4", "12X4"),
        ("currency", "USD"),
    ],
)
def test_account_create_rejects_invalid_values(field: str, value: str) -> None:
    values = {
        "issuer": "TD",
        "display_name": "Cash Back",
        "color": "#12805c",
        "last4": "4821",
        "currency": "CAD",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        AccountCreate.model_validate(values)


def test_read_schemas_serialize_orm_ids_enums_and_utc_timestamps() -> None:
    created_at = datetime(2026, 7, 15, 18, 30, tzinfo=UTC)
    profile = Profile(
        id=7,
        name="Personal",
        base_currency="CAD",
        is_archived=False,
        created_at=created_at,
        updated_at=created_at,
    )
    account = Account(
        id=11,
        profile_id=7,
        issuer="CIBC",
        display_name="Dividend",
        color="#4f6bff",
        last4="9876",
        currency="CAD",
        account_fingerprint=None,
        is_archived=False,
        created_at=created_at.replace(tzinfo=None),
        updated_at=created_at.replace(tzinfo=None),
    )

    profile_json = json.loads(ProfileRead.model_validate(profile).model_dump_json())
    account_json = json.loads(AccountRead.model_validate(account).model_dump_json())

    assert profile_json["id"] == 7
    assert profile_json["created_at"] == "2026-07-15T18:30:00Z"
    assert account_json["id"] == 11
    assert account_json["profile_id"] == 7
    assert account_json["issuer"] == "CIBC"
    assert account_json["updated_at"] == "2026-07-15T18:30:00Z"
