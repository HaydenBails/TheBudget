from datetime import date, datetime

import pytest

from app.domain.dates import parse_iso_date, serialize_iso_date


def test_iso_date_round_trip() -> None:
    value = date(2026, 7, 15)

    assert parse_iso_date(serialize_iso_date(value)) == value


@pytest.mark.parametrize(
    "value",
    ["", "2026-7-15", "2026-07-15T00:00:00", " 2026-07-15", "2026/07/15", "2025-02-29"],
)
def test_parse_iso_date_rejects_noncanonical_or_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_iso_date(value)


def test_date_utilities_reject_wrong_types_and_datetime() -> None:
    with pytest.raises(TypeError):
        parse_iso_date(date(2026, 7, 15))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        serialize_iso_date(datetime(2026, 7, 15))
