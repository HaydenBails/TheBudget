"""Service tests for profile/account lifecycle and isolation."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory
from app.models import Base
from app.schemas import AccountCreate, AccountUpdate, ProfileCreate, ProfileUpdate
from app.services import (
    InvalidUpdateError,
    ResourceNotFoundError,
    archive_account,
    archive_profile,
    create_account,
    create_profile,
    get_account,
    list_accounts,
    list_profiles,
    restore_account,
    restore_profile,
    update_account,
    update_profile,
)


@pytest.fixture
def service_session(tmp_path: Path) -> Iterator[Session]:
    engine: Engine = create_db_engine(tmp_path / "services.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            yield session
    finally:
        engine.dispose()


def _account(name: str, *, last4: str | None = "1234") -> AccountCreate:
    return AccountCreate(
        issuer="TD",
        display_name=name,
        color="#4f6bff",
        last4=last4,
    )


def test_profile_lifecycle_uses_archive_instead_of_delete(
    service_session: Session,
) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))

    updated = update_profile(
        service_session,
        profile.id,
        ProfileUpdate(name="Household"),
    )
    archived = archive_profile(service_session, profile.id)

    assert updated.name == "Household"
    assert archived.is_archived is True
    assert list_profiles(service_session) == []
    assert list_profiles(service_session, include_archived=True) == [profile]

    restored = restore_profile(service_session, profile.id)
    assert restored.is_archived is False


def test_account_reads_are_always_profile_scoped(service_session: Session) -> None:
    owner = create_profile(service_session, ProfileCreate(name="Owner"))
    other = create_profile(service_session, ProfileCreate(name="Other"))
    account = create_account(service_session, owner.id, _account("Owner card"))
    create_account(service_session, other.id, _account("Other card", last4="9876"))

    assert get_account(service_session, owner.id, account.id) is account
    assert get_account(service_session, other.id, account.id) is None
    assert [item.display_name for item in list_accounts(service_session, owner.id)] == [
        "Owner card"
    ]
    assert [item.display_name for item in list_accounts(service_session, other.id)] == [
        "Other card"
    ]


def test_cross_profile_update_and_archive_are_rejected(
    service_session: Session,
) -> None:
    owner = create_profile(service_session, ProfileCreate(name="Owner"))
    other = create_profile(service_session, ProfileCreate(name="Other"))
    account = create_account(service_session, owner.id, _account("Original"))

    with pytest.raises(ResourceNotFoundError, match="account not found"):
        update_account(
            service_session,
            other.id,
            account.id,
            AccountUpdate(display_name="Leaked"),
        )
    with pytest.raises(ResourceNotFoundError, match="account not found"):
        archive_account(service_session, other.id, account.id)
    with pytest.raises(ResourceNotFoundError, match="account not found"):
        restore_account(service_session, other.id, account.id)

    assert account.display_name == "Original"
    assert account.is_archived is False


def test_account_archive_preserves_record_and_filters_default_list(
    service_session: Session,
) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))
    account = create_account(service_session, profile.id, _account("Card"))

    archived = archive_account(service_session, profile.id, account.id)

    assert archived.is_archived is True
    assert get_account(service_session, profile.id, account.id) is account
    assert list_accounts(service_session, profile.id) == []
    assert list_accounts(service_session, profile.id, include_archived=True) == [account]

    restored = restore_account(service_session, profile.id, account.id)
    assert restored.is_archived is False


def test_account_creation_requires_an_existing_profile(service_session: Session) -> None:
    with pytest.raises(ResourceNotFoundError, match="profile not found"):
        create_account(service_session, 999, _account("Orphan"))


@pytest.mark.parametrize(
    "values",
    [
        ProfileUpdate(name=None),
        ProfileUpdate(is_archived=None),
    ],
)
def test_profile_update_rejects_explicit_null_required_fields(
    service_session: Session,
    values: ProfileUpdate,
) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))

    with pytest.raises(InvalidUpdateError, match="cannot be null"):
        update_profile(service_session, profile.id, values)


@pytest.mark.parametrize(
    "values",
    [
        AccountUpdate(display_name=None),
        AccountUpdate(color=None),
        AccountUpdate(issuer=None),
        AccountUpdate(is_archived=None),
    ],
)
def test_account_update_rejects_explicit_null_required_fields(
    service_session: Session,
    values: AccountUpdate,
) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))
    account = create_account(service_session, profile.id, _account("Card"))

    with pytest.raises(InvalidUpdateError, match="cannot be null"):
        update_account(service_session, profile.id, account.id, values)


def test_account_update_can_clear_nullable_fields(service_session: Session) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))
    account = create_account(
        service_session,
        profile.id,
        AccountCreate(
            issuer="TD",
            display_name="Card",
            color="#4f6bff",
            last4="1234",
            account_fingerprint="issuer-token",
        ),
    )

    updated = update_account(
        service_session,
        profile.id,
        account.id,
        AccountUpdate(last4=None, account_fingerprint=None),
    )

    assert updated.last4 is None
    assert updated.account_fingerprint is None


def test_omitted_nullable_fields_are_preserved(service_session: Session) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))
    account = create_account(service_session, profile.id, _account("Original"))

    updated = update_account(
        service_session,
        profile.id,
        account.id,
        AccountUpdate(display_name="Renamed"),
    )

    assert updated.display_name == "Renamed"
    assert updated.last4 == "1234"


def test_invalid_patch_does_not_partially_mutate_account(service_session: Session) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))
    account = create_account(service_session, profile.id, _account("Original"))

    with pytest.raises(InvalidUpdateError):
        update_account(
            service_session,
            profile.id,
            account.id,
            AccountUpdate(display_name="Mutated", color=None),
        )

    assert account.display_name == "Original"
    assert account.color == "#4f6bff"


def test_profile_archive_preserves_individual_account_archive_states(
    service_session: Session,
) -> None:
    profile = create_profile(service_session, ProfileCreate(name="Personal"))
    active = create_account(service_session, profile.id, _account("Active"))
    archived = create_account(
        service_session,
        profile.id,
        _account("Archived", last4="5678"),
    )
    archive_account(service_session, profile.id, archived.id)

    archive_profile(service_session, profile.id)
    restore_profile(service_session, profile.id)

    assert active.is_archived is False
    assert archived.is_archived is True
