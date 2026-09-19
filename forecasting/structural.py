"""Project receipts, expenses and debt, then score the resulting account path.

Central path reverts the 3-month run-rate toward the company's 12-month mean,
then scales each month by last year's same calendar month when that month is
already observed (the PR #9 seasonal rule, on flows). Bands scale recent
volatility by sqrt(horizon step), with signs that help or hurt the score.
"""
import json
from pathlib import Path

import numpy as np

from algorythm.score_data import load_bank_panel, month_edges
from algorythm.score_engine import calculate_scores
from forecasting.stress import SCENARIOS

PHI = 0.8
LONG_WINDOW = 12
SEASONAL_LAG = 12
SEASONAL_CLIP = (0.5, 2.0)
M_MIN, M_MAX = 0.05, 0.25
BAND_WIDTH_CAP = 0.80
RUN_WINDOW = 3
SLOPE_WINDOW = 6
HOLD_FIELDS = ('quality', 'hhi', 'hhi_quality', 'funding_gap')


def default_dataset():
    root = Path(__file__).resolve().parents[1]
    for name in ('data', 'dataset'):
        if (root / name / 'companies.csv').exists():
            return root / name
    return root / 'data'


def run_rate(series, origin, window=RUN_WINDOW):
    start = max(0, origin - window + 1)
    block = np.nan_to_num(np.asarray(series[start:origin + 1], dtype=float), nan=0.0)
    return float(block.mean()) if len(block) else 0.0


def long_rate(series, origin, window=LONG_WINDOW):
    start = max(0, origin - window + 1)
    block = np.nan_to_num(np.asarray(series[start:origin + 1], dtype=float), nan=0.0)
    return float(block.mean()) if len(block) else 0.0


def mean_reverting_path(short, long, horizon, phi=PHI):
    short, long = max(float(short), 0.0), max(float(long), 0.0)
    gap = short - long
    return np.array([max(long + (phi ** step) * gap, 0.0) for step in range(1, horizon + 1)], dtype=float)


def seasonal_factors(series, origin, horizon, long_mean):
    """Same calendar month last year, only if that month is already observed.

    Matches PR #9: target month t+h uses the series at t+h-12 when that index
    is in [0, origin]; otherwise the factor is 1 (no seasonal information).
    """
    factors = np.ones(horizon, dtype=float)
    if long_mean <= 0:
        return factors
    values = np.nan_to_num(np.asarray(series, dtype=float), nan=0.0)
    for step in range(1, horizon + 1):
        lagged = origin + step - SEASONAL_LAG
        if 0 <= lagged <= origin and values[lagged] > 0:
            factors[step - 1] = float(np.clip(values[lagged] / long_mean, *SEASONAL_CLIP))
    return factors


def band_width(m, step):
    return float(min(m * np.sqrt(step), BAND_WIDTH_CAP))


def volatility_m(series, origin, lookback=SLOPE_WINDOW, window=RUN_WINDOW):
    first = max(window - 1, origin - lookback + 1)
    rates = np.array([run_rate(series, step, window) for step in range(first, origin + 1)], dtype=float)
    if len(rates) < 3:
        return M_MIN
    previous = np.maximum(rates[:-1], 1e-6)
    mom = np.diff(rates) / previous
    return float(np.clip(np.std(mom), M_MIN, M_MAX))


def refund_rate(receipts, refunds, origin, window=RUN_WINDOW):
    start = max(0, origin - window + 1)
    rec = np.nan_to_num(np.asarray(receipts[start:origin + 1], dtype=float), nan=0.0)
    ref = np.nan_to_num(np.asarray(refunds[start:origin + 1], dtype=float), nan=0.0)
    denom = rec.sum()
    return float(ref.sum() / denom) if denom > 0 else 0.0


def scenario_paths(receipts, expenses, debt, refunds, origin, horizon):
    """Return pessimistic, central and optimistic monthly paths for the three flows plus refunds."""
    specs = []
    for series, help_when_up in (
        (receipts, True),
        (expenses, False),
        (debt, False),
    ):
        short = run_rate(series, origin)
        long = long_rate(series, origin)
        width = volatility_m(series, origin)
        factors = seasonal_factors(series, origin, horizon, long)
        central = mean_reverting_path(short, long, horizon) * factors
        steps = np.arange(1, horizon + 1, dtype=float)
        scale = np.array([band_width(width, step) for step in steps])
        if help_when_up:
            optimistic, pessimistic = central * (1 + scale), central * (1 - scale)
        else:
            optimistic, pessimistic = central * (1 - scale), central * (1 + scale)
        specs.append((
            np.maximum(pessimistic, 0), np.maximum(central, 0), np.maximum(optimistic, 0),
            width, short, long, factors,
        ))
    rec_p, rec_c, rec_o, m_r, l_r, mu_r, f_r = specs[0]
    exp_p, exp_c, exp_o, m_e, l_e, mu_e, f_e = specs[1]
    deb_p, deb_c, deb_o, m_d, l_d, mu_d, f_d = specs[2]
    rate = refund_rate(receipts, refunds, origin)
    return {
        'pessimistic': {'receipts': rec_p, 'expenses': exp_p, 'debt_service': deb_p, 'refunds': rec_p * rate},
        'central': {'receipts': rec_c, 'expenses': exp_c, 'debt_service': deb_c, 'refunds': rec_c * rate},
        'optimistic': {'receipts': rec_o, 'expenses': exp_o, 'debt_service': deb_o, 'refunds': rec_o * rate},
        'diagnostics': {
            'receipts': {'level': l_r, 'long_mean': mu_r, 'm': m_r, 'seasonal': f_r.tolist()},
            'expenses': {'level': l_e, 'long_mean': mu_e, 'm': m_e, 'seasonal': f_e.tolist()},
            'debt_service': {'level': l_d, 'long_mean': mu_d, 'm': m_d, 'seasonal': f_d.tolist()},
            'refund_rate': rate,
            'phi': PHI,
        },
    }


_BANK_CACHE = {}


def load_company_banks(dataset=None):
    data_dir = Path(dataset) if dataset is not None else default_dataset()
    key = str(data_dir.resolve())
    if key in _BANK_CACHE:
        return _BANK_CACHE[key]
    tables = {}
    if (data_dir / 'companies.csv').exists():
        companies, _, bank, _ = load_bank_panel(data_dir)
        for i, company in enumerate(companies):
            tables[company['company_id']] = (bank, i)
    synthetic = Path(__file__).resolve().parent / 'datasets' / 'synthetic' / 'v1'
    if synthetic.exists():
        for name in SCENARIOS:
            archive = synthetic / f'{name}.npz'
            meta = synthetic / f'{name}.json'
            if not archive.exists() or not meta.exists():
                continue
            bank = dict(np.load(archive, allow_pickle=False))
            for i, company in enumerate(json.loads(meta.read_text())['companies']):
                tables[company['company_id']] = (bank, i)
    _BANK_CACHE[key] = tables
    return tables


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


def as_of_from_origin(origin, start='2024-09-01', end='2026-09-01'):
    from datetime import date
    edges = month_edges(start, end)
    if 0 <= origin < len(edges):
        return edges[origin].isoformat()
    first = date.fromisoformat(start)
    total = first.year * 12 + (first.month - 1) + int(origin)
    year, month = divmod(total, 12)
    return date(year, month + 1, 1).isoformat()


def _rounded(values):
    return [round(float(value), 2) for value in values]


def _named_flows(paths):
    return {name: {k: paths[name][k] for k in ('receipts', 'expenses', 'debt_service', 'refunds')}
            for name in ('pessimistic', 'central', 'optimistic')}


_PREVISION_CACHE = {}


def structural_prevision(company_id, meses=12, banks=None, dataset=None, origin=None):
    """Product payload: 12 (or `meses`) monthly scores per scenario, not a single horizon."""
    tables = banks if banks is not None else load_company_banks(dataset)
    if company_id not in tables:
        return None
    bank, row = tables[company_id]
    receipts = bank['receipts']
    last = int(receipts.shape[1] - 1)
    origin = last if origin is None else min(int(origin), last)
    meses = int(meses)
    if origin < RUN_WINDOW - 1 or meses < 1:
        return {
            'company_id': company_id,
            'model': 'structural_v2',
            'status': 'insufficient_history',
            'as_of': as_of_from_origin(max(origin, 0)),
            'meses': meses,
            'current_score': None,
            'alto': [],
            'medio': [],
            'bajo': [],
        }
    cache_key = (company_id, origin, meses, id(tables))
    if cache_key in _PREVISION_CACHE:
        return _PREVISION_CACHE[cache_key]
    refunds = bank['refunds'][row] if 'refunds' in bank else np.zeros(receipts.shape[1])
    paths = scenario_paths(
        receipts[row], bank['expenses'][row], bank['debt_service'][row],
        refunds, origin, meses)
    current, series = score_named_path_series(bank, row, origin, meses, _named_flows(paths))
    payload = {
        'company_id': company_id,
        'model': 'structural_v2',
        'status': 'available',
        'as_of': as_of_from_origin(origin),
        'meses': meses,
        'current_score': round(current, 2),
        'alto': _rounded(series['optimistic']),
        'medio': _rounded(series['central']),
        'bajo': _rounded(series['pessimistic']),
    }
    _PREVISION_CACHE[cache_key] = payload
    return payload


class StructuralForecaster:
    """Account-path forecaster. Does not learn the score formula."""

    def __init__(self, horizon, seed=419, banks=None, dataset=None):
        self.name = 'structural_v2'
        self.horizon = int(horizon)
        self.seed = seed
        self.linear_explanation = False
        self.banks = banks if banks is not None else load_company_banks(dataset)
        self.fit_seconds = 0.0
        self._score_cache = {}

    def fit(self, samples):
        return self

    def calibrate(self, samples):
        return self

    def _lookup(self, company_id):
        try:
            return self.banks[company_id]
        except KeyError as exc:
            raise KeyError(f'No bank panel for {company_id}') from exc

    def _paths(self, company_id, origin):
        bank, row = self._lookup(company_id)
        refunds = bank['refunds'][row] if 'refunds' in bank else np.zeros_like(bank['receipts'][row])
        return bank, row, scenario_paths(
            bank['receipts'][row], bank['expenses'][row], bank['debt_service'][row],
            refunds, origin, self.horizon)

    def _scores(self, company_id, origin):
        cache_key = (company_id, int(origin))
        if cache_key in self._score_cache:
            return self._score_cache[cache_key]
        bank, row, paths = self._paths(company_id, origin)
        named = _named_flows(paths)
        scored = score_named_paths(bank, row, origin, self.horizon, named)
        low, median, high = (np.clip(scored[name], 0, 100) for name in ('pessimistic', 'central', 'optimistic'))
        result = (np.array([min(low, median), median, max(high, median)], dtype=float), paths, bank, row)
        self._score_cache[cache_key] = result
        return result

    def predict(self, samples):
        output = np.zeros((len(samples.company), 3))
        for i, (company, origin) in enumerate(zip(samples.company, samples.origin)):
            output[i], *_ = self._scores(company, int(origin))
        return output

    def direction_probabilities(self, samples, deadband=3):
        preds = self.predict(samples)
        weights = np.array([0.25, 0.50, 0.25])
        delta = preds - samples.current[:, None]
        down = (delta < -deadband) @ weights
        up = (delta > deadband) @ weights
        return np.column_stack([down, 1 - down - up, up])

    def explain(self, sample):
        company, origin = sample.company[0], int(sample.origin[0])
        current = float(sample.current[0])
        scores, paths, bank, row = self._scores(company, origin)
        median = float(scores[1])
        persist = {
            'receipts': np.full(self.horizon, paths['diagnostics']['receipts']['level']),
            'expenses': np.full(self.horizon, paths['diagnostics']['expenses']['level']),
            'debt_service': np.full(self.horizon, paths['diagnostics']['debt_service']['level']),
        }
        persist['refunds'] = persist['receipts'] * paths['diagnostics']['refund_rate']
        frozen = np.clip(score_at_horizon(bank, row, origin, self.horizon, persist), 0, 100)
        rec_only = dict(persist)
        rec_only['receipts'] = paths['central']['receipts']
        rec_only['refunds'] = rec_only['receipts'] * paths['diagnostics']['refund_rate']
        after_rec = np.clip(score_at_horizon(bank, row, origin, self.horizon, rec_only), 0, 100)
        rec_exp = dict(rec_only)
        rec_exp['expenses'] = paths['central']['expenses']
        after_exp = np.clip(score_at_horizon(bank, row, origin, self.horizon, rec_exp), 0, 100)
        contributions = [
            {'feature': 'receipts_path', 'points': float(after_rec - frozen)},
            {'feature': 'expenses_path', 'points': float(after_exp - after_rec)},
            {'feature': 'debt_service_path', 'points': float(median - after_exp)},
        ]
        reference = float(frozen - current)
        explained = current + reference + sum(c['points'] for c in contributions)
        clipping = float(median - explained)
        return {
            'method': 'projected_account_then_score',
            'causal': False,
            'current_score': current,
            'reference_delta': reference,
            'contributions': contributions,
            'other_points': 0.0,
            'calibration_points': 0.0,
            'clipping_points': clipping,
            'predicted_score': median,
            'diagnostics': paths['diagnostics'],
            'reconstruction_error': median - (explained + clipping),
        }

    def prevision(self, company_id, origin=None):
        """Monthly alto/medio/bajo paths for the product chart."""
        return structural_prevision(
            company_id, meses=self.horizon, banks=self.banks, origin=origin)
