"""Profile-isolated account persistence operations."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account
from app.schemas import AccountCreate, AccountUpdate
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.profiles import require_profile

_REQUIRED_UPDATE_FIELDS = frozenset(
    {"issuer", "display_name", "color", "is_archived"}
)


def create_account(
    session: Session,
    profile_id: int,
    values: AccountCreate,
) -> Account:
    """Create an account owned by an existing explicit profile."""

    require_profile(session, profile_id)
    account = Account(profile_id=profile_id, **values.model_dump())
    session.add(account)
    session.flush()
    return account


def list_accounts(
    session: Session,
    profile_id: int,
    *,
    include_archived: bool = False,
) -> list[Account]:
    """List only accounts owned by ``profile_id``."""

    require_profile(session, profile_id)
    statement = (
        select(Account)
        .where(Account.profile_id == profile_id)
        .order_by(func.lower(Account.display_name), Account.id)
    )
    if not include_archived:
        statement = statement.where(Account.is_archived.is_(False))
    return list(session.scalars(statement))


def get_account(session: Session, profile_id: int, account_id: int) -> Account | None:
    """Return an account only when both its ID and profile owner match."""

    statement = select(Account).where(
        Account.id == account_id,
        Account.profile_id == profile_id,
    )
    return session.scalar(statement)


def require_account(session: Session, profile_id: int, account_id: int) -> Account:
    """Return a scoped account or the same error used for missing records."""

    account = get_account(session, profile_id, account_id)
    if account is None:
        raise ResourceNotFoundError("account not found")
    return account


def update_account(
    session: Session,
    profile_id: int,
    account_id: int,
    values: AccountUpdate,
) -> Account:
    """Update an account only through its owning profile scope."""

    account = require_account(session, profile_id, account_id)
    changes = values.model_dump(exclude_unset=True)
    _reject_null_required_fields(changes)
    for field, value in changes.items():
        setattr(account, field, value)
    session.flush()
    return account


def archive_account(session: Session, profile_id: int, account_id: int) -> Account:
    """Archive a scoped account while preserving its history."""

    return update_account(
        session,
        profile_id,
        account_id,
        AccountUpdate(is_archived=True),
    )


def restore_account(session: Session, profile_id: int, account_id: int) -> Account:
    """Restore an archived account within its owning profile scope."""

    return update_account(
        session,
        profile_id,
        account_id,
        AccountUpdate(is_archived=False),
    )


def _reject_null_required_fields(changes: dict[str, object]) -> None:
    null_fields = sorted(
        field for field in _REQUIRED_UPDATE_FIELDS if changes.get(field, object()) is None
    )
    if null_fields:
        joined = ", ".join(null_fields)
        raise InvalidUpdateError(f"required fields cannot be null: {joined}")
