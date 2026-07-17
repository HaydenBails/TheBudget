"""Service-layer errors shared by profile-scoped operations."""


class ResourceNotFoundError(LookupError):
    """A requested resource is missing from the caller's allowed scope."""


class InvalidUpdateError(ValueError):
    """An update attempted to clear a required persisted field."""


class ResourceConflictError(ValueError):
    """A create/update conflicts with an existing uniquely constrained record."""


class SplitSumError(ValueError):
    """Transaction split amounts do not sum to the parent transaction amount."""
