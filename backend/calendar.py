"""Tres relojes del dataset congelado.

El motor etiqueta cada score con el primer día *después* del mes de
transacciones (`as_of`). El último ciclo completo es agosto de 2026:
transacciones en `[2026-08-01, 2026-09-01)`, score `as_of=2026-09-01`.

El 1-sep aporta un día suelto (~9.200 movimientos). No es un mes cerrado
y no entra en medias ni comparativas mensuales.
"""

from datetime import date, datetime
from typing import Any


DATA_CUTOFF = date(2026, 9, 1)
LAST_CLOSED_MONTH = date(2026, 8, 1)
PARTIAL_MONTH = date(2026, 9, 1)
PARTIAL_MONTH_DAYS = 1
PARTIAL_MONTH_LABEL = "Foto de apertura 1-sep (1 día)"


def parse_as_of(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def previous_month_start(day: date) -> date:
    if day.month == 1:
        return date(day.year - 1, 12, 1)
    return date(day.year, day.month - 1, 1)


def closed_month_from_as_of(value: Any) -> date:
    """Mes de transacciones que cierra el corte `as_of` (fin exclusivo)."""
    return previous_month_start(parse_as_of(value))


def closed_month_iso(value: Any) -> str:
    return closed_month_from_as_of(value).isoformat()


def calendar_fields() -> dict[str, Any]:
    return {
        "as_of": DATA_CUTOFF.isoformat(),
        "last_closed_month": LAST_CLOSED_MONTH.isoformat(),
        "partial_month": PARTIAL_MONTH.isoformat(),
        "partial_month_label": PARTIAL_MONTH_LABEL,
        "partial_month_days": PARTIAL_MONTH_DAYS,
    }
