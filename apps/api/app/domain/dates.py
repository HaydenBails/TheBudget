"""Strict calendar-date parsing and serialization."""

from __future__ import annotations

import re
from datetime import date

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_iso_date(value: str) -> date:
    """Parse a canonical ``YYYY-MM-DD`` calendar date."""

    if not isinstance(value, str):
        raise TypeError("date input must be a string")
    if _ISO_DATE.fullmatch(value) is None:
        raise ValueError("date input must use YYYY-MM-DD")

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("date input must be a valid calendar date") from error


def serialize_iso_date(value: date) -> str:
    """Serialize a calendar date, rejecting datetime-like subclasses."""

    if type(value) is not date:
        raise TypeError("value must be a date without a time component")
    return value.isoformat()
