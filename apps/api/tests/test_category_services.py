"""Service tests for category seeding, CRUD, and profile isolation."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory
from app.models import Base
from app.schemas import CategoryCreate, CategoryUpdate, ProfileCreate
from app.services import (
    InvalidUpdateError,
    ResourceNotFoundError,
    archive_category,
    create_category,
    create_profile,
    list_categories,
    require_category,
    restore_category,
    seed_default_categories,
    update_category,
)
from app.services.category_defaults import DEFAULT_CATEGORIES


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine: Engine = create_db_engine(tmp_path / "categories.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as db:
            yield db
    finally:
        engine.dispose()


def test_create_profile_seeds_default_categories(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    cats = list_categories(session, profile.id)
    assert len(cats) == len(DEFAULT_CATEGORIES) == 15
    assert all(c.is_default for c in cats)
    assert [c.slug for c in cats] == [d.slug for d in DEFAULT_CATEGORIES]
    # excluded flags carried through
    excluded = {c.slug for c in cats if c.excluded_from_spending}
    assert excluded == {"savings", "debt", "fees"}


def test_seeding_is_idempotent(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    created_again = seed_default_categories(session, profile.id)
    assert created_again == []  # nothing new on a second pass
    assert len(list_categories(session, profile.id)) == 15


def test_create_category_derives_unique_slug_and_appends(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    first = create_category(
        session, profile.id, CategoryCreate(name="Side Hustle", color="#4f6bff")
    )
    second = create_category(
        session, profile.id, CategoryCreate(name="Side Hustle!", color="#4f6bff")
    )
    assert first.slug == "side-hustle"
    assert second.slug == "side-hustle-2"
    assert first.is_default is False
    # new categories sort after the seeded defaults
    assert second.sort_order > max(d for d in range(len(DEFAULT_CATEGORIES)))
    # ...but never after Uncategorized, which always sorts last.
    assert list_categories(session, profile.id)[-1].slug == "uncategorized"


def test_uncategorized_is_always_listed_last(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    create_category(session, profile.id, CategoryCreate(name="Zephyr", color="#4f6bff"))
    create_category(session, profile.id, CategoryCreate(name="Aardvark", color="#4f6bff"))
    slugs = [c.slug for c in list_categories(session, profile.id)]
    assert slugs[-1] == "uncategorized"
    assert slugs.count("uncategorized") == 1


def test_profile_isolation(session: Session) -> None:
    a = create_profile(session, ProfileCreate(name="Alpha"))
    b = create_profile(session, ProfileCreate(name="Beta"))
    cat = create_category(session, a.id, CategoryCreate(name="Travel", color="#0ea5e9"))
    # visible under A, not under B
    assert any(c.id == cat.id for c in list_categories(session, a.id))
    assert all(c.id != cat.id for c in list_categories(session, b.id))
    # cross-profile access raises the same not-found used for missing rows
    with pytest.raises(ResourceNotFoundError):
        require_category(session, b.id, cat.id)


def test_archive_and_restore(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    cat = create_category(session, profile.id, CategoryCreate(name="Gifts", color="#ec4899"))
    archive_category(session, profile.id, cat.id)
    assert all(c.id != cat.id for c in list_categories(session, profile.id))
    assert any(c.id == cat.id for c in list_categories(session, profile.id, include_archived=True))
    restore_category(session, profile.id, cat.id)
    assert any(c.id == cat.id for c in list_categories(session, profile.id))


def test_update_rejects_null_required_field(session: Session) -> None:
    profile = create_profile(session, ProfileCreate(name="Personal"))
    cat = create_category(session, profile.id, CategoryCreate(name="Gifts", color="#ec4899"))
    with pytest.raises(InvalidUpdateError):
        update_category(session, profile.id, cat.id, CategoryUpdate(name=None))
