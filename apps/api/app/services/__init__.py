"""Profile and account service boundary."""

from app.services.accounts import (
    archive_account,
    create_account,
    get_account,
    list_accounts,
    require_account,
    restore_account,
    update_account,
)
from app.services.categories import (
    archive_category,
    create_category,
    get_category,
    list_categories,
    require_category,
    restore_category,
    seed_default_categories,
    update_category,
)
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.profiles import (
    archive_profile,
    create_profile,
    get_profile,
    list_profiles,
    require_profile,
    restore_profile,
    update_profile,
)

__all__ = [
    "InvalidUpdateError",
    "ResourceNotFoundError",
    "archive_account",
    "archive_category",
    "archive_profile",
    "create_account",
    "create_category",
    "create_profile",
    "get_account",
    "get_category",
    "get_profile",
    "list_accounts",
    "list_categories",
    "list_profiles",
    "require_account",
    "require_category",
    "require_profile",
    "restore_account",
    "restore_category",
    "restore_profile",
    "seed_default_categories",
    "update_account",
    "update_category",
    "update_profile",
]
