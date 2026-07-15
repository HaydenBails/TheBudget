import pytest

from app.domain.money import add_cents, parse_cents, sum_cents


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0", 0),
        ("12", 1200),
        ("12.3", 1230),
        ("12.34", 1234),
        ("+12.34", 1234),
        ("-0.05", -5),
    ],
)
def test_parse_cents_accepts_strict_decimal_text(text: str, expected: int) -> None:
    assert parse_cents(text) == expected


@pytest.mark.parametrize(
    "value",
    ["", " 12.34", "12.34 ", "$12.34", "1,234.56", "12.345", ".50", "01.00", "1e2"],
)
def test_parse_cents_rejects_ambiguous_or_invalid_text(value: str) -> None:
    with pytest.raises(ValueError):
        parse_cents(value)


@pytest.mark.parametrize("value", [12.34, 1234, True, None])
def test_parse_cents_rejects_non_string_inputs(value: object) -> None:
    with pytest.raises(TypeError):
        parse_cents(value)  # type: ignore[arg-type]


def test_cent_arithmetic_is_exact() -> None:
    assert add_cents(10, -3) == 7
    assert sum_cents([10, 20, -5]) == 25
    assert sum_cents([]) == 0


@pytest.mark.parametrize("value", [1.0, "1", True])
def test_cent_arithmetic_rejects_non_integer_amounts(value: object) -> None:
    with pytest.raises(TypeError):
        add_cents(0, value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sum_cents([0, value])  # type: ignore[list-item]
