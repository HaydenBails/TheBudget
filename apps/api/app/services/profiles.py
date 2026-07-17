"""Profile persistence operations.

Services flush but do not commit. The API layer owns transaction boundaries.
Hard deletion is intentionally absent: the first release archives profiles.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Profile
from app.schemas import ProfileCreate, ProfileUpdate
from app.services.errors import InvalidUpdateError, ResourceNotFoundError

_REQUIRED_UPDATE_FIELDS = frozenset({"name", "is_archived"})


def create_profile(session: Session, values: ProfileCreate) -> Profile:
    """Create and flush a profile, seeding its default categories.

    The seed is idempotent; the local import avoids a module import cycle with
    the category service (which depends on ``require_profile`` here).
    """

    from app.services.categories import seed_default_categories
    from app.services.merchant_rules import seed_default_merchant_rules

    profile = Profile(**values.model_dump())
    session.add(profile)
    session.flush()
    seed_default_categories(session, profile.id)
    seed_default_merchant_rules(session, profile.id)
    return profile


def list_profiles(session: Session, *, include_archived: bool = False) -> list[Profile]:
    """List profiles, excluding archived profiles by default."""

    statement = select(Profile).order_by(func.lower(Profile.name), Profile.id)
    if not include_archived:
        statement = statement.where(Profile.is_archived.is_(False))
    return list(session.scalars(statement))


def get_profile(session: Session, profile_id: int) -> Profile | None:
    """Return a profile by identifier, including an archived profile."""

    return session.get(Profile, profile_id)


def require_profile(session: Session, profile_id: int) -> Profile:
    """Return a profile or raise the service's non-disclosing missing error."""

    profile = get_profile(session, profile_id)
    if profile is None:
        raise ResourceNotFoundError("profile not found")
    return profile


def update_profile(
    session: Session,
    profile_id: int,
    values: ProfileUpdate,
) -> Profile:
    """Update mutable profile fields without exposing hard deletion."""

    profile = require_profile(session, profile_id)
    changes = values.model_dump(exclude_unset=True)
    _reject_null_required_fields(changes)
    for field, value in changes.items():
        setattr(profile, field, value)
    session.flush()
    return profile


def archive_profile(session: Session, profile_id: int) -> Profile:
    """Archive a profile while preserving all profile-owned history."""

    return update_profile(session, profile_id, ProfileUpdate(is_archived=True))


def restore_profile(session: Session, profile_id: int) -> Profile:
    """Restore an archived profile without rewriting its account states."""

    return update_profile(session, profile_id, ProfileUpdate(is_archived=False))


def _reject_null_required_fields(changes: dict[str, object]) -> None:
    null_fields = sorted(
        field for field in _REQUIRED_UPDATE_FIELDS if changes.get(field, object()) is None
    )
    if null_fields:
        joined = ", ".join(null_fields)
        raise InvalidUpdateError(f"required fields cannot be null: {joined}")
