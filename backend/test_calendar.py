"""Contrato de los tres relojes: corte, mes cerrado y foto parcial."""

from datetime import date

from backend.calendar import (
    DATA_CUTOFF,
    LAST_CLOSED_MONTH,
    PARTIAL_MONTH,
    PARTIAL_MONTH_DAYS,
    PARTIAL_MONTH_LABEL,
    calendar_fields,
    closed_month_from_as_of,
    closed_month_iso,
    parse_as_of,
)


def test_canonical_dates():
    assert DATA_CUTOFF == date(2026, 9, 1)
    assert LAST_CLOSED_MONTH == date(2026, 8, 1)
    assert PARTIAL_MONTH == date(2026, 9, 1)
    assert PARTIAL_MONTH_DAYS == 1
    assert "1-sep" in PARTIAL_MONTH_LABEL
    assert "1 día" in PARTIAL_MONTH_LABEL


def test_closed_month_is_the_month_before_as_of():
    assert closed_month_from_as_of("2026-09-01") == date(2026, 8, 1)
    assert closed_month_from_as_of("2024-10-01") == date(2024, 9, 1)
    assert closed_month_from_as_of(date(2025, 1, 1)) == date(2024, 12, 1)
    assert closed_month_iso("2026-09-01") == "2026-08-01"


def test_parse_as_of_accepts_date_and_datetime_strings():
    assert parse_as_of("2026-09-01T00:00:00") == date(2026, 9, 1)
    assert parse_as_of(date(2026, 8, 1)) == date(2026, 8, 1)


def test_calendar_fields_are_the_public_contract():
    clock = calendar_fields()
    assert clock["as_of"] == "2026-09-01"
    assert clock["last_closed_month"] == "2026-08-01"
    assert clock["partial_month"] == "2026-09-01"
    assert clock["partial_month_days"] == 1
    assert clock["partial_month_label"] == PARTIAL_MONTH_LABEL
