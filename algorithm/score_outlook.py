"""Perspectiva a 6 meses: si el régimen de 3 meses se queda, ¿la nota cae?

Eje paralelo al monitor. No añade estados. No es PD. Ver
`research/dos_puntos_trayectoria.md` §5 y `algorithm/EPISODIOS.md`.
"""
import numpy as np

from algorithm.score_project import LONG_WINDOW, RUN_WINDOW, scores_constant_regimes, _window_mean, _window_refund_rho
from algorithm.score_states import NEGATIVE_STATES, PENDING

NINGUNA = 'NINGUNA'
SALUD_ADVERSA = 'SALUD_ADVERSA'
CIRCULANTE_ADVERSO = 'CIRCULANTE_ADVERSO'
HORIZON = 6
DROP = 3.0
BOUNDARY = 60.0
MIN_ORIGIN = 5
MIN_QUALITY = 0.50
MIN_OBSERVED = 6

COPY_HUECO = {
    'salud': 'Si esto sigue (cobros, gastos o deuda), a 6 meses la nota cae.',
    'circulante': 'Estás comprando tiempo; a 6 meses ese colchón vence.',
}
COPY_SOLO_ROJO = {
    'salud': 'Giro persistente de salud (cobros, gastos o deuda).',
    'circulante': 'Giro persistente: el colchón de circulante ya no basta.',
}


def fires(projected, observed, baseline):
    return (projected <= observed - DROP) and (projected < BOUNDARY) and (projected <= baseline - DROP)


def _eligible_mask(panels, t):
    state = panels['state'][:, t]
    quality = panels['state_quality'][:, t] if 'state_quality' in panels else panels['bank_quality'][:, t]
    return (
        (t >= MIN_ORIGIN)
        & ~panels['is_prior'][:, t]
        & (panels['observed_months'][:, t] >= MIN_OBSERVED)
        & (quality >= MIN_QUALITY)
        & (state != PENDING)
        & ~np.isin(state, NEGATIVE_STATES)
    )


def _pick_outlook(salud, circulante, observed, baseline, allow_circulante):
    salud_ok = fires(salud, observed, baseline)
    circ_ok = allow_circulante and fires(circulante, observed, baseline)
    if salud_ok and circ_ok:
        return (SALUD_ADVERSA if salud <= circulante else CIRCULANTE_ADVERSO,
                min(salud, circulante))
    if salud_ok:
        return SALUD_ADVERSA, salud
    if circ_ok:
        return CIRCULANTE_ADVERSO, circulante
    return NINGUNA, np.nan


def compute_outlook(bank, panels, ap_pending=None, horizon=HORIZON):
    """Matrices alineadas con `panels['score']`. Circulante solo en el último mes."""
    n, months = panels['score'].shape
    outlook = np.full((n, months), NINGUNA, dtype='<U20')
    projected = np.full((n, months), np.nan)
    baseline = np.full((n, months), np.nan)
    if months == 0:
        return {'outlook': outlook, 'outlook_score': projected, 'outlook_base_score': baseline}

    receipts = np.asarray(bank['receipts'], dtype=float)
    expenses = np.asarray(bank['expenses'], dtype=float)
    debt = np.asarray(bank['debt_service'], dtype=float)
    refunds = np.asarray(bank.get('refunds', np.zeros_like(receipts)), dtype=float)
    ap = np.zeros(n, dtype=float) if ap_pending is None else np.nan_to_num(np.asarray(ap_pending, dtype=float), nan=0.0)
    last = months - 1

    for t in range(MIN_ORIGIN, months):
        rows = np.flatnonzero(_eligible_mask(panels, t))
        if rows.size == 0:
            continue
        r3 = _window_mean(receipts, rows, t, RUN_WINDOW)
        e3 = _window_mean(expenses, rows, t, RUN_WINDOW)
        h3 = _window_mean(debt, rows, t, RUN_WINDOW)
        r12 = _window_mean(receipts, rows, t, LONG_WINDOW)
        e12 = _window_mean(expenses, rows, t, LONG_WINDOW)
        h12 = _window_mean(debt, rows, t, LONG_WINDOW)
        rho = _window_refund_rho(receipts, refunds, rows, t, RUN_WINDOW)
        regimes = {
            'salud': {'receipts': r3, 'expenses': e3, 'debt_service': h3, 'refund_rho': rho},
            'base': {'receipts': r12, 'expenses': e12, 'debt_service': h12, 'refund_rho': rho},
        }
        live_circulante = t == last and np.any(ap[rows] > 0)
        if live_circulante:
            regimes['circulante'] = {
                'receipts': r12, 'expenses': e12 + ap[rows] / horizon,
                'debt_service': h12, 'refund_rho': rho,
            }
        scored = scores_constant_regimes(bank, rows, t, horizon, regimes)
        s_hat = scored['salud']
        s_base = scored['base']
        s_circ = scored['circulante'] if live_circulante else s_base
        observed = panels['score'][rows, t]
        baseline[rows, t] = s_base
        for i, row in enumerate(rows):
            label, value = _pick_outlook(float(s_hat[i]), float(s_circ[i]), float(observed[i]),
                                         float(s_base[i]), live_circulante)
            outlook[row, t] = label
            if label != NINGUNA:
                projected[row, t] = value
    return {'outlook': outlook, 'outlook_score': projected, 'outlook_base_score': baseline}


def adverse_streaks(row):
    streaks = []
    start = None
    for t, value in enumerate(row):
        if value != NINGUNA:
            if start is None:
                start = t
        elif start is not None:
            streaks.append((start, t - 1))
            start = None
    if start is not None:
        streaks.append((start, len(row) - 1))
    return streaks


def associate_outlook(ep, detection_idx, outlook_row, score_row, projected_row, as_of, persistence_months):
    """Racha viva al inicio del momentum (último adverso ≥ detección − persistencia)."""
    if ep.get('direccion') != 'deterioro':
        return None, None
    threshold = detection_idx - persistence_months
    chosen = None
    for start, end in adverse_streaks(outlook_row):
        if end >= threshold and start < detection_idx and end < detection_idx:
            if chosen is None or end > chosen[1] or (end == chosen[1] and start > chosen[0]):
                chosen = (start, end)
    if chosen is None:
        return None, None
    start, end = chosen
    label = str(outlook_row[start])
    projected = projected_row[start]
    if label == NINGUNA or not np.isfinite(projected):
        return None, None
    perspectiva = {
        'as_of': str(as_of[start]),
        'outlook': label,
        'score_observado': round(float(score_row[start]), 2),
        'score_proyectado': round(float(projected), 2),
        'meses_antes_deteccion': int(detection_idx - start),
    }
    return perspectiva, (start, end)


def expired_unassociated(outlook_row, as_of, associated, gap=2):
    """Rachas que volvieron a NINGUNA `gap` meses sin detección asociada."""
    rows = []
    months = len(outlook_row)
    taken = set(associated)
    for start, end in adverse_streaks(outlook_row):
        if (start, end) in taken:
            continue
        if (months - 1) - end >= gap:
            rows.append({'inicio': str(as_of[start]), 'fin': str(as_of[end])})
    return rows


def familia_de(perspectiva):
    if perspectiva and perspectiva.get('outlook') == CIRCULANTE_ADVERSO:
        return 'circulante'
    return 'salud'


def texto_familia(direction, deteccion, senales, perspectiva, frases_mejora):
    if perspectiva:
        return COPY_HUECO[familia_de(perspectiva)]
    if direction == 'deterioro':
        return COPY_SOLO_ROJO['salud']
    return frases_mejora
