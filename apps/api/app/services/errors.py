"""Service-layer errors shared by profile-scoped operations."""


class ResourceNotFoundError(LookupError):
    """A requested resource is missing from the caller's allowed scope."""


class InvalidUpdateError(ValueError):
    """An update attempted to clear a required persisted field."""


class SplitSumError(ValueError):
    """Transaction split amounts do not sum to the parent transaction amount."""
