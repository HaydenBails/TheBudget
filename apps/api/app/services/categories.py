"""Profile-isolated category persistence and default seeding.

Services flush but do not commit; the API layer owns transaction boundaries.
Categories are archived, never hard-deleted.
"""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category
from app.schemas import CategoryCreate, CategoryUpdate
from app.services.category_defaults import DEFAULT_CATEGORIES
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.profiles import require_profile

_REQUIRED_UPDATE_FIELDS = frozenset(
    {"name", "color", "icon", "excluded_from_spending", "sort_order", "is_archived"}
)


def seed_default_categories(session: Session, profile_id: int) -> list[Category]:
    """Idempotently ensure the default categories exist for ``profile_id``.

    Existing slugs are left untouched, so re-seeding never duplicates.
    """

    existing = set(
        session.scalars(
            select(Category.slug).where(Category.profile_id == profile_id)
        )
    )
    created: list[Category] = []
    for order, default in enumerate(DEFAULT_CATEGORIES):
        if default.slug in existing:
            continue
        category = Category(
            profile_id=profile_id,
            slug=default.slug,
            name=default.name,
            color=default.color,
            icon=default.icon,
            excluded_from_spending=default.excluded_from_spending,
            is_default=True,
            sort_order=order,
        )
        session.add(category)
        created.append(category)
    if created:
        session.flush()
    return created


def create_category(
    session: Session,
    profile_id: int,
    values: CategoryCreate,
) -> Category:
    """Create a custom category owned by an existing explicit profile."""

    require_profile(session, profile_id)
    payload = values.model_dump()
    payload["slug"] = _unique_slug(session, profile_id, payload["name"])
    next_order = session.scalar(
        select(func.coalesce(func.max(Category.sort_order), -1)).where(
            Category.profile_id == profile_id
        )
    )
    category = Category(
        profile_id=profile_id,
        is_default=False,
        sort_order=(next_order or 0) + 1,
        **payload,
    )
    session.add(category)
    session.flush()
    return category


def list_categories(
    session: Session,
    profile_id: int,
    *,
    include_archived: bool = False,
) -> list[Category]:
    """List only categories owned by ``profile_id`` in display order."""

    require_profile(session, profile_id)
    statement = (
        select(Category)
        .where(Category.profile_id == profile_id)
        # "Uncategorized" always sorts last, regardless of its sort_order, so
        # user-created categories never appear beneath it.
        .order_by(
            (Category.slug == "uncategorized"),
            Category.sort_order,
            func.lower(Category.name),
            Category.id,
        )
    )
    if not include_archived:
        statement = statement.where(Category.is_archived.is_(False))
    return list(session.scalars(statement))


def get_category(session: Session, profile_id: int, category_id: int) -> Category | None:
    """Return a category only when both its ID and profile owner match."""

    statement = select(Category).where(
        Category.id == category_id,
        Category.profile_id == profile_id,
    )
    return session.scalar(statement)


def require_category(session: Session, profile_id: int, category_id: int) -> Category:
    """Return a scoped category or the same error used for missing records."""

    category = get_category(session, profile_id, category_id)
    if category is None:
        raise ResourceNotFoundError("category not found")
    return category


def update_category(
    session: Session,
    profile_id: int,
    category_id: int,
    values: CategoryUpdate,
) -> Category:
    """Update a category only through its owning profile scope."""

    category = require_category(session, profile_id, category_id)
    changes = values.model_dump(exclude_unset=True)
    _reject_null_required_fields(changes)
    for field, value in changes.items():
        setattr(category, field, value)
    session.flush()
    return category


def archive_category(session: Session, profile_id: int, category_id: int) -> Category:
    """Archive a scoped category while preserving references to it."""

    return update_category(
        session, profile_id, category_id, CategoryUpdate(is_archived=True)
    )


def restore_category(session: Session, profile_id: int, category_id: int) -> Category:
    """Restore an archived category within its owning profile scope."""

    return update_category(
        session, profile_id, category_id, CategoryUpdate(is_archived=False)
    )


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "category"


def _unique_slug(session: Session, profile_id: int, name: str) -> str:
    base = _slugify(name)
    taken = set(
        session.scalars(select(Category.slug).where(Category.profile_id == profile_id))
    )
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def _reject_null_required_fields(changes: dict[str, object]) -> None:
    null_fields = sorted(
        field for field in _REQUIRED_UPDATE_FIELDS if changes.get(field, object()) is None
    )
    if null_fields:
        joined = ", ".join(null_fields)
        raise InvalidUpdateError(f"required fields cannot be null: {joined}")
