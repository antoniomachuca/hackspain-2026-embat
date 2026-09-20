"""Attach factor reparto to DuckDB history without rewriting scores."""
from datetime import date

from algorithm.test_score_decompose import SHOCK, case_collect_early
from backend.routes.companies import _as_of_key, _reparto_lookup


def _months(start, n):
    year, month = start.year, start.month
    rows = []
    for _ in range(n):
        rows.append({"as_of": date(year, month, 1), "score": 99.0})
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return rows


def test_reparto_lookup_labels_with_duckdb_as_of():
    _, bank, _ = case_collect_early()
    rows = _months(date(2024, 10, 1), 24)
    lookup = _reparto_lookup("COMP_0010", rows, banks={"COMP_0010": (bank, 0)})

    first = lookup[_as_of_key(rows[0]["as_of"])]
    assert first["drivers"] == []
    assert first["pct_tendencia"] == 0
    assert first["pct_bache"] == 0

    shock = lookup[_as_of_key(rows[SHOCK]["as_of"])]
    assert shock["pct_bache"] == 100
    cobros = next(item for item in shock["drivers"] if item["field"] == "receipts")
    assert cobros["reason"] == "pulso_cobros"
    assert cobros["kind"] == "coyuntural"


def test_reparto_lookup_crop_does_not_reset_month_zero():
    _, bank, _ = case_collect_early()
    rows = _months(date(2024, 10, 1), 24)
    lookup = _reparto_lookup("COMP_0010", rows, banks={"COMP_0010": (bank, 0)})
    cropped = rows[-12:]
    first = lookup[_as_of_key(cropped[0]["as_of"])]
    assert cropped[0]["as_of"] == rows[SHOCK]["as_of"]
    assert first["drivers"]
    assert cropped[0]["score"] == 99.0
