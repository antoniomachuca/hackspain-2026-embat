"""Decompose a monthly score move into structural vs circumstantial drivers.

The front today splits Δscore with an OLS slope on the score itself. That is a
property of the curve, not of the account. This module attributes the same Δ
by passing counterfactual bank panels through `calculate_scores`, then labels
each driver with the salud/circulante taxonomy already used by palancas.

It does not replace `classify_states`. A BACHE state is a persistence gate on
momentum. A 70/30 split of this month's points is a different question.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from algorythm.score_engine import calculate_scores


DEADBAND = 0.15
PULSE_RATIO = 0.25
REVERSAL_RATIO = 0.50
DSO_TIMING_DAYS = 5.0
YOY_DEADBAND = 0.06
OLS_WINDOW = 6
RUN_WINDOW = 3
LONG_WINDOW = 12

# Order is a declared sequential Shapley path, not a causal graph.
# Known level-setters first; mixed cobros after; timing stocks last.
SEQUENCE = (
    'expenses',
    'debt_service',
    'refunds',
    'hhi',
    'receipts',
    'funding_gap',
    'quality',
)

# Priors: what the number *is* when we only see a flow. Overridden by
# reversal, seasonality, DSO or a one-month pulse. See research note.
PRIOR_KIND = {
    'expenses': 'estructural',      # recortar opex se queda
    'debt_service': 'estructural',  # refi / tipo se queda
    'refunds': 'estructural',       # calidad de producto / política
    'hhi': 'estructural',           # mix de clientes
    'receipts': 'mixto',
    'funding_gap': 'coyuntural',    # hueco intradía, no el negocio
    'quality': 'coyuntural',        # cobertura de dato, no economía
}

FAMILY = {
    'expenses': 'salud',
    'debt_service': 'salud',
    'refunds': 'salud',
    'hhi': 'salud',
    'receipts': 'salud',
    'funding_gap': 'circulante',
    'quality': 'dato',
    'arrastre': 'formula',
    'residual': 'formula',
}


@dataclass(frozen=True)
class DriverMove:
    field: str
    points: float
    kind: str
    family: str
    reason: str


def copy_bank(bank):
    return {key: np.array(value, dtype=float, copy=True) for key, value in bank.items()}


def sync_derived(bank):
    if 'receipts' in bank and 'refunds' in bank:
        bank['gross_receipts'] = np.maximum(bank['receipts'], 0) + np.maximum(bank['refunds'], 0)
    return bank


def window_mean(series, origin, window):
    start = max(0, origin - window + 1)
    block = np.nan_to_num(np.asarray(series[start:origin + 1], dtype=float), nan=0.0)
    return float(block.mean()) if len(block) else 0.0


def freeze_month(bank, t):
    frozen = copy_bank(bank)
    if t <= 0:
        return frozen
    for key, values in frozen.items():
        if np.ndim(values) == 2 and values.shape[1] > t:
            values[:, t] = values[:, t - 1]
    return sync_derived(frozen)


def ols_slope(scores, t, window=OLS_WINDOW):
    ys = np.asarray(scores[max(0, t - window + 1):t + 1], dtype=float)
    n = len(ys)
    if n < 2:
        return 0.0
    xs = np.arange(n, dtype=float)
    mx, my = xs.mean(), ys.mean()
    den = float(((xs - mx) ** 2).sum())
    if den == 0:
        return 0.0
    return float(((xs - mx) * (ys - my)).sum() / den)


def percentages(struct_pts, circ_pts, delta):
    """Share of |contrib| so opposing signs do not invent a 100/0 split.

    Flat months stay 0/0, matching the front's `repartir`.
    """
    if not np.isfinite(delta) or abs(delta) < DEADBAND:
        return 0.0, 0.0
    mag_s, mag_c = abs(float(struct_pts)), abs(float(circ_pts))
    total = mag_s + mag_c
    if total < 1e-9:
        return 0.0, 0.0
    pct_t = 100.0 * mag_s / total
    return pct_t, 100.0 - pct_t


def ols_reparto(scores, t):
    """Current front rule, ported: slope of the score vs this month's Δ."""
    scores = np.asarray(scores, dtype=float)
    delta = float(scores[t] - scores[t - 1]) if t else 0.0
    if abs(delta) < DEADBAND:
        return {'method': 'ols_score', 'delta': delta, 'pct_tendencia': 0.0, 'pct_bache': 0.0,
                'struct_pts': 0.0, 'circ_pts': 0.0}
    slope = ols_slope(scores, t)
    explained = min(abs(slope), abs(delta)) if np.sign(delta) == np.sign(slope) else 0.0
    pct_t = 100.0 * explained / abs(delta)
    struct_pts = float(np.sign(delta) * explained)
    return {'method': 'ols_score', 'delta': delta, 'pct_tendencia': pct_t, 'pct_bache': 100.0 - pct_t,
            'struct_pts': struct_pts, 'circ_pts': delta - struct_pts}


def _series(bank, field, row=0):
    values = bank.get(field)
    if values is None:
        return None
    array = np.asarray(values, dtype=float)
    if array.ndim == 2:
        return array[row]
    return array


def _pair_conserves(first, second, baseline):
    move = first - baseline
    if abs(move) < 1e-9:
        return False
    return abs(0.5 * (first + second) - baseline) <= REVERSAL_RATIO * 0.5 * abs(move)


def _is_timing_shift(series, t):
    """Two consecutive months keep the same sum as the month before them.

    That is the accounting signature of 'cobré este mes lo de el que viene'
    or 'pagué este mes lo del siguiente'. A level shift does not conserve.
    """
    if series is None or t <= 0:
        return False
    prev = float(series[t - 1])
    now = float(series[t])
    if t + 1 < series.shape[0] and _pair_conserves(now, float(series[t + 1]), prev):
        return True
    if t >= 2 and _pair_conserves(prev, now, float(series[t - 2])):
        return True
    return False


def _is_live_pulse(series, t, expected):
    """Large deviation in the last observed month: bache pending confirmation."""
    if series is None or t <= 0 or t + 1 < series.shape[0]:
        return False
    irregular = float(series[t] - expected)
    return abs(irregular) > PULSE_RATIO * max(abs(expected), 1.0)


def stack_banks(panels):
    keys = list(panels[0])
    return {key: np.concatenate([np.asarray(panel[key], dtype=float) for panel in panels], axis=0)
            for key in keys}


def _seasonal_match(series, t):
    if series is None or t < 12:
        return False
    now, prev = float(series[t]), float(series[t - 1])
    if abs(now - prev) < 1e-9:
        return False
    lagged = float(series[t - 12])
    if lagged <= 0:
        return False
    if abs(now - lagged) > YOY_DEADBAND * lagged:
        return False
    if t >= 13:
        trend_now = now - prev
        trend_last = lagged - float(series[t - 13])
        if abs(trend_now - trend_last) > YOY_DEADBAND * lagged:
            return False
    return True


def classify_driver(field, bank, t, erp=None, row=0):
    """Label one field's month-t news. Prior first, data can override."""
    prior = PRIOR_KIND.get(field, 'coyuntural')
    series = _series(bank, field, row)
    expected = window_mean(series, t - 1, RUN_WINDOW) if series is not None and t else 0.0

    if field == 'funding_gap':
        return 'coyuntural', 'stock_timing'
    if field == 'quality':
        return 'coyuntural', 'cobertura_dato'

    if field == 'receipts':
        dso = _series(erp or {}, 'dso_days', row) if erp else None
        if dso is not None and t > 0 and np.isfinite(dso[t]) and np.isfinite(dso[t - 1]):
            if abs(float(dso[t] - dso[t - 1])) >= DSO_TIMING_DAYS:
                return 'coyuntural', 'dso'
        if _seasonal_match(series, t):
            return 'coyuntural', 'estacion'
        if _is_timing_shift(series, t):
            return 'coyuntural', 'pulso_cobros'
        if _is_live_pulse(series, t, expected):
            return 'coyuntural', 'cobros_sin_confirmar'
        return 'estructural', 'volumen'

    if field == 'expenses':
        if _is_timing_shift(series, t):
            return 'coyuntural', 'pulso_pagos'
        return 'estructural', 'opex'

    if field == 'refunds' and _is_timing_shift(series, t):
        return 'coyuntural', 'ola_puntual'

    return prior, 'prior'


def _row_bank(bank, row):
    return {key: (np.asarray(value, dtype=float)[row:row + 1].copy() if np.ndim(value) == 2
                  else np.asarray(value, dtype=float))
            for key, value in bank.items()}


def _repeat_erp(erp, n, row=0):
    if erp is None:
        return None
    single = _row_bank(erp, row)
    return {key: np.repeat(value, n, axis=0) if np.ndim(value) == 2 else value
            for key, value in single.items()}


def _run_panel(bank, origin, row=0):
    panel = copy_bank(bank)
    for field in ('receipts', 'expenses', 'debt_service'):
        if field in panel:
            panel[field][row, origin] = window_mean(panel[field][row], origin, RUN_WINDOW)
    if 'refunds' in panel and 'receipts' in panel:
        rec, ref = panel['receipts'][row], panel['refunds'][row]
        rate = window_mean(ref, origin, RUN_WINDOW) / max(window_mean(rec, origin, RUN_WINDOW), 1e-9)
        panel['refunds'][row, origin] = panel['receipts'][row, origin] * rate
    return sync_derived(panel)


def attribute_month(bank, t, erp=None, row=0, scored=None):
    """Sequential counterfactuals at month t through the frozen score formula."""
    if t <= 0:
        raise ValueError('attribution starts at month 1')
    if scored is None:
        scored = calculate_scores(bank, erp)
    delta = float(scored['score'][row, t] - scored['score'][row, t - 1])
    prev = float(scored['score'][row, t - 1])
    actual = float(scored['score'][row, t])

    local = _row_bank(bank, row)
    frozen = freeze_month(local, t)
    panels = [frozen]
    fields = [field for field in SEQUENCE if field in local]
    working = frozen
    for field in fields:
        nxt = copy_bank(working)
        nxt[field][:, t] = local[field][:, t]
        sync_derived(nxt)
        panels.append(nxt)
        working = nxt

    stacked = stack_banks(panels)
    path = calculate_scores(stacked, _repeat_erp(erp, len(panels), row=row))['score'][:, t]
    s_frozen = float(path[0])
    arrastre = s_frozen - prev

    drivers = [DriverMove('arrastre', arrastre, 'estructural', FAMILY['arrastre'],
                          'arrastre')]
    last = s_frozen
    for index, field in enumerate(fields, start=1):
        s_now = float(path[index])
        kind, reason = classify_driver(field, bank, t, erp=erp, row=row)
        drivers.append(DriverMove(field, s_now - last, kind, FAMILY[field], reason))
        last = s_now

    if any(d.field == 'receipts' and d.reason == 'estacion' for d in drivers):
        drivers = [
            DriverMove(d.field, d.points, 'coyuntural', d.family, 'estacion')
            if d.field in ('arrastre', 'refunds') and d.kind == 'estructural' else d
            for d in drivers
        ]

    residual = actual - last
    if abs(residual) >= 1e-6:
        drivers.append(DriverMove('residual', residual, 'coyuntural', FAMILY['residual'],
                                  'residual'))

    struct_pts = sum(d.points for d in drivers if d.kind == 'estructural')
    circ_pts = sum(d.points for d in drivers if d.kind == 'coyuntural')
    pct_t, pct_b = percentages(struct_pts, circ_pts, delta)
    return {
        'method': 'factor_formula',
        'delta': delta,
        'score': actual,
        'prev_score': prev,
        'pct_tendencia': pct_t,
        'pct_bache': pct_b,
        'struct_pts': float(struct_pts),
        'circ_pts': float(circ_pts),
        'drivers': drivers,
    }


def photocopy_reparto(bank, t, erp=None, row=0, scores=None):
    """Sibling of the forecast: 3m run-rate through f vs the observed month.

    Still a smoother, but it smooths the *inputs* and then uses the formula,
    which is what structural_v2 already does for the cone. Kept as a baseline
    so we can say whether 'just stop OLS-on-score' is enough.
    """
    if t <= 0:
        raise ValueError('photocopy starts at month 1')
    if scores is None:
        scores = calculate_scores(bank, erp)['score'][row]
    delta = float(scores[t] - scores[t - 1])
    local = _row_bank(bank, row)
    stacked = stack_banks([_run_panel(local, t), _run_panel(local, t - 1)])
    path = calculate_scores(stacked, _repeat_erp(erp, 2, row=row))['score']
    struct_pts = float(path[0, t] - path[1, t - 1])
    circ_pts = delta - struct_pts
    pct_t, pct_b = percentages(struct_pts, circ_pts, delta)
    return {
        'method': 'fotocopia_3m',
        'delta': delta,
        'pct_tendencia': pct_t,
        'pct_bache': pct_b,
        'struct_pts': float(struct_pts),
        'circ_pts': float(circ_pts),
    }


def decompose_series(bank, erp=None, row=0):
    """Month-by-month splits for the three approaches. No lookahead into labels."""
    n = np.asarray(bank['receipts']).shape[1]
    scored = calculate_scores(bank, erp)
    scores = scored['score'][row]
    rows = []
    for t in range(1, n):
        factor = attribute_month(bank, t, erp=erp, row=row, scored=scored)
        rows.append({
            't': t,
            'score': float(scores[t]),
            'delta': float(scores[t] - scores[t - 1]),
            'ols': ols_reparto(scores, t),
            'fotocopia': photocopy_reparto(bank, t, erp=erp, row=row, scores=scores),
            'factor': factor,
        })
    return rows


# ---------------------------------------------------------------------------
# Public JSON — GET /api/companies/{id}/history  (campo `reparto` por mes)
# El front no llama a este módulo. FastAPI serializa con history_with_reparto.
# ---------------------------------------------------------------------------

FIELD_ETIQUETA = {
    'expenses': 'Gastos',
    'debt_service': 'Deuda',
    'refunds': 'Devoluciones',
    'hhi': 'Concentración',
    'receipts': 'Cobros',
    'funding_gap': 'Hueco de caja',
    'quality': 'Cobertura del dato',
    'arrastre': 'Ventana 3 meses',
    'residual': 'Resto',
}

REASON_ETIQUETA = {
    'opex': 'se queda',
    'volumen': 'volumen',
    'pulso_cobros': 'timing de cobros',
    'pulso_pagos': 'timing de pagos',
    'estacion': 'calendario',
    'dso': 'plazos de cobro',
    'cobros_sin_confirmar': 'sin confirmar',
    'prior': 'nivel',
    'stock_timing': 'timing de caja',
    'ola_puntual': 'ola puntual',
    'cobertura_dato': 'cobertura del dato',
    'arrastre': 'ventana 3 meses',
    'residual': 'resto',
}

DRIVER_MIN_ABS = 0.05


def empty_reparto():
    return {
        'delta': 0.0,
        'pct_tendencia': 0,
        'pct_bache': 0,
        'struct_pts': 0.0,
        'circ_pts': 0.0,
        'drivers': [],
    }


def driver_to_api(d, min_abs=DRIVER_MIN_ABS):
    if abs(d.points) < min_abs:
        return None
    return {
        'field': d.field,
        'etiqueta': FIELD_ETIQUETA.get(d.field, d.field),
        'points': round(float(d.points), 2),
        'kind': d.kind,
        'family': d.family,
        'reason': d.reason,
        'razon': REASON_ETIQUETA.get(d.reason, d.reason),
    }


def factor_to_reparto(factor):
    drivers = [j for d in factor['drivers'] if (j := driver_to_api(d))]
    return {
        'delta': round(float(factor['delta']), 2),
        'pct_tendencia': int(round(factor['pct_tendencia'])),
        'pct_bache': int(round(factor['pct_bache'])),
        'struct_pts': round(float(factor['struct_pts']), 2),
        'circ_pts': round(float(factor['circ_pts']), 2),
        'drivers': drivers,
    }


def history_with_reparto(bank, as_of_dates, company_id='demo', erp=None, row=0):
    """Shape exacto del history una vez FastAPI anide `reparto` en cada mes.

    as_of_dates: lista ISO YYYY-MM-DD, misma longitud que el panel.
    El mes 0 no tiene anterior → `empty_reparto()`.
    """
    scored = calculate_scores(bank, erp)
    scores = scored['score'][row]
    n = len(as_of_dates)
    history = []
    for t in range(n):
        if t == 0:
            reparto = empty_reparto()
        else:
            factor = attribute_month(bank, t, erp=erp, row=row, scored=scored)
            reparto = factor_to_reparto(factor)
        history.append({
            'as_of': as_of_dates[t],
            'score': round(float(scores[t]), 1),
            'reparto': reparto,
        })
    return {
        'company_id': company_id,
        'months': n,
        'history': history,
    }
