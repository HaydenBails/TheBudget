"""Shared schema configuration and timestamp serialization."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class ORMReadModel(BaseModel):
    """Base for response schemas populated directly from ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMReadModel):
    """Response fields shared by timestamped persisted records."""

    id: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_timestamp(self, value: datetime) -> str:
        """Emit canonical UTC RFC 3339 timestamps, including SQLite values."""

        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        else:
            value = value.astimezone(UTC)
        return value.isoformat().replace("+00:00", "Z")
