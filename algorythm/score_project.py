"""Fotocopia del banco hasta un origen y proyección de flujos. Dominio puro.

El lab de previsión (`forecasting.structural`) reutiliza estas funciones. El motor
no importa `forecasting`. Los meses `origin+1…` nunca leen el futuro real.
"""
import numpy as np

from algorythm.score_engine import calculate_scores

HOLD_FIELDS = ('quality', 'hhi', 'hhi_quality', 'funding_gap')
RUN_WINDOW = 3
LONG_WINDOW = 12


def run_rate(series, origin, window=RUN_WINDOW):
    start = max(0, origin - window + 1)
    block = np.nan_to_num(np.asarray(series[start:origin + 1], dtype=float), nan=0.0)
    return float(block.mean()) if len(block) else 0.0


def long_rate(series, origin, window=LONG_WINDOW):
    return run_rate(series, origin, window=window)


def refund_rate(receipts, refunds, origin, window=RUN_WINDOW):
    start = max(0, origin - window + 1)
    rec = np.nan_to_num(np.asarray(receipts[start:origin + 1], dtype=float), nan=0.0)
    ref = np.nan_to_num(np.asarray(refunds[start:origin + 1], dtype=float), nan=0.0)
    denom = rec.sum()
    return float(ref.sum() / denom) if denom > 0 else 0.0


def _hold(value):
    if value is None or not np.isfinite(value):
        return 0.0
    return float(value)


def build_projected_bank(bank, row, origin, horizon, flows):
    """History through origin only; projected months never read the real future."""
    length = origin + 1 + horizon
    projected = {}
    keys = set(bank) | {'receipts', 'expenses', 'debt_service', 'refunds', 'gross_receipts', 'quality'}
    for key in keys:
        source = bank.get(key)
        panel = np.zeros((1, length))
        if source is not None and np.ndim(source) == 2:
            history = min(origin + 1, source.shape[1])
            panel[0, :history] = np.nan_to_num(source[row, :history], nan=0.0)
            last = _hold(source[row, origin] if origin < source.shape[1] else panel[0, history - 1])
            if key in HOLD_FIELDS or key not in flows:
                panel[0, origin + 1:] = last
        projected[key] = panel
    for key, path in flows.items():
        projected[key][0, origin + 1:] = path
    projected['gross_receipts'][0, origin + 1:] = (
        projected['receipts'][0, origin + 1:] + projected['refunds'][0, origin + 1:]
    )
    if 'quality' in projected:
        projected['quality'][0, origin + 1:] = 1.0
    return projected


def score_at_horizon(bank, row, origin, horizon, flows):
    panel = build_projected_bank(bank, row, origin, horizon, flows)
    return float(calculate_scores(panel)['score'][0, origin + horizon])


def score_named_paths(bank, row, origin, horizon, named):
    names = list(named)
    panels = [build_projected_bank(bank, row, origin, horizon, named[name]) for name in names]
    stacked = {key: np.concatenate([panel[key] for panel in panels], axis=0) for key in panels[0]}
    scores = calculate_scores(stacked)['score'][:, origin + horizon]
    return {name: float(score) for name, score in zip(names, scores)}


def score_named_path_series(bank, row, origin, horizon, named):
    """Score every projected month (t+1 … t+horizon), plus the observed score at origin."""
    names = list(named)
    panels = [build_projected_bank(bank, row, origin, horizon, named[name]) for name in names]
    stacked = {key: np.concatenate([panel[key] for panel in panels], axis=0) for key in panels[0]}
    scored = calculate_scores(stacked)['score']
    future = np.clip(scored[:, origin + 1: origin + 1 + horizon], 0, 100)
    current = float(np.clip(scored[0, origin], 0, 100))
    return current, {name: future[i] for i, name in enumerate(names)}


def _window_mean(panel, rows, origin, window):
    start = max(0, origin - window + 1)
    block = np.nan_to_num(np.asarray(panel)[rows, start:origin + 1], nan=0.0)
    return block.mean(axis=1) if block.size else np.zeros(len(rows))


def _window_refund_rho(receipts, refunds, rows, origin, window=RUN_WINDOW):
    start = max(0, origin - window + 1)
    rec = np.nan_to_num(np.asarray(receipts)[rows, start:origin + 1], nan=0.0).sum(axis=1)
    ref = np.nan_to_num(np.asarray(refunds)[rows, start:origin + 1], nan=0.0).sum(axis=1)
    rho = np.zeros(len(rows), dtype=float)
    np.divide(ref, rec, out=rho, where=rec > 0)
    return rho


def _batch_panel(bank, rows, origin, horizon):
    n = len(rows)
    length = origin + 1 + horizon
    rows = np.asarray(rows)
    projected = {}
    keys = set(bank) | {'receipts', 'expenses', 'debt_service', 'refunds', 'gross_receipts', 'quality'}
    for key in keys:
        source = bank.get(key)
        panel = np.zeros((n, length))
        if source is not None and np.ndim(source) == 2:
            history = min(origin + 1, source.shape[1])
            panel[:, :history] = np.nan_to_num(source[rows, :history], nan=0.0)
            if origin < source.shape[1]:
                last = source[rows, origin]
            else:
                last = panel[:, history - 1]
            last = np.where(np.isfinite(last), last, 0.0)
            if key in HOLD_FIELDS:
                panel[:, origin + 1:] = last[:, None]
        projected[key] = panel
    return projected


def _fill_constant_flows(projected, origin, receipts, expenses, debt_service, refund_rho):
    future = slice(origin + 1, None)
    projected['receipts'][:, future] = np.asarray(receipts, dtype=float)[:, None]
    projected['expenses'][:, future] = np.asarray(expenses, dtype=float)[:, None]
    projected['debt_service'][:, future] = np.asarray(debt_service, dtype=float)[:, None]
    projected['refunds'][:, future] = projected['receipts'][:, future] * np.asarray(refund_rho, dtype=float)[:, None]
    projected['gross_receipts'][:, future] = projected['receipts'][:, future] + projected['refunds'][:, future]
    projected['quality'][:, future] = 1.0
    return projected


def scores_constant_regimes(bank, rows, origin, horizon, regimes):
    """Score stacked companies under one or more constant-flow regimes.

    `regimes` maps a name to `{receipts, expenses, debt_service, refund_rho}`,
    each a 1-d array aligned with `rows`. Returns `{name: ndarray(n,)}` at
    `origin + horizon`.
    """
    if len(rows) == 0:
        return {name: np.zeros(0) for name in regimes}
    names = list(regimes)
    panels = []
    for name in names:
        spec = regimes[name]
        panel = _batch_panel(bank, rows, origin, horizon)
        _fill_constant_flows(panel, origin, spec['receipts'], spec['expenses'],
                             spec['debt_service'], spec['refund_rho'])
        panels.append(panel)
    stacked = {key: np.concatenate([panel[key] for panel in panels], axis=0) for key in panels[0]}
    scored = calculate_scores(stacked)['score'][:, origin + horizon]
    n = len(rows)
    return {name: scored[i * n:(i + 1) * n] for i, name in enumerate(names)}
