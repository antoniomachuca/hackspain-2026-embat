from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class ScoreConfig:
    base_weights: tuple[float, float, float] = (.50, .30, .20)
    momentum_weight: float = 8.0
    growth_weight: float = 6.0
    fragility_weight: float = 8.0
    momentum_mix: float = .50
    velocity_scale: float = 2.0
    ema_scale: float = 5.0
    persistence_deadband: float = .02
    liquidity_scale: float = .50
    refund_scale: float = .05
    debt_scale: float = .25
    hhi_scale: float = .25
    funding_gap_scale: float = .50
    growth_scale: float = .20
    dso_scale: float = 60.0
    dso_change_scale: float = 30.0
    erp_weight: float = .40

    def __post_init__(self):
        weights = np.asarray(self.base_weights, dtype=float)
        if weights.shape != (3,) or not np.isfinite(weights).all() or np.any(weights < 0) or not np.isclose(weights.sum(), 1, atol=1e-12, rtol=0):
            raise ValueError('base_weights must be three nonnegative finite values summing to one')
        for name, value in vars(self).items():
            if name == 'base_weights':
                continue
            if not np.isfinite(value) or value < 0:
                raise ValueError(f'{name} must be nonnegative and finite')
            if name.endswith('scale') and value == 0:
                raise ValueError(f'{name} must be positive')
        if not 0 <= self.momentum_mix <= 1 or not 0 <= self.erp_weight <= 1:
            raise ValueError('mixing weights must lie in [0, 1]')


def divide(numerator, denominator):
    numerator, denominator = np.broadcast_arrays(numerator, denominator)
    output = np.full(numerator.shape, np.nan)
    np.divide(numerator, denominator, out=output, where=denominator > 0)
    return output


def rolling_sum(values, window):
    values = np.asarray(values, dtype=float)
    output = np.full_like(values, np.nan)
    for month in range(window - 1, values.shape[1]):
        output[:, month] = values[:, month - window + 1:month + 1].sum(axis=1)
    return output


def available_median(values):
    output = np.full(values.shape[0], np.nan)
    valid = np.isfinite(values).any(axis=1)
    output[valid] = np.nanmedian(values[valid], axis=1)
    return output


def panel(source, name, shape, default=np.nan):
    values = np.asarray(source.get(name, default), dtype=float)
    if values.shape not in ((), shape):
        raise ValueError(f'{name}: expected shape {shape}, got {values.shape}')
    return np.broadcast_to(values, shape)


def validate_optional_fields(source, shape, bounds):
    for name, (lower, upper) in bounds.items():
        values = panel(source, name, shape)
        finite = values[np.isfinite(values)]
        if np.isinf(values).any() or np.any(finite < lower - 1e-12) or np.any(finite > upper + 1e-12):
            raise ValueError(f'{name} must lie in [{lower}, {upper}] or be NaN when unavailable')


def observed_blend(values, reliability, prior=.5):
    known = np.isfinite(values)
    return prior + np.where(known, reliability, 0) * (np.where(known, values, prior) - prior)


def hill(values, scale):
    values = np.asarray(values, dtype=float)
    if scale <= 0:
        raise ValueError('Hill scale must be positive')
    return 1 - scale / (np.maximum(values, 0) + scale)


def rolling_mean(values, window):
    return rolling_sum(values, window) / window


def rolling_cv(values, window=6):
    result = np.full_like(values, np.nan)
    for month in range(window - 1, values.shape[1]):
        block = values[:, month - window + 1:month + 1]
        result[:, month] = divide(np.std(block, axis=1), np.mean(block, axis=1))
    return result


def bounded_momentum(base, confirmation, quality, config):
    result = np.zeros_like(base)
    fast = base[:, 0].copy()
    slow = fast.copy()
    for month in range(1, base.shape[1]):
        fast = .5 * base[:, month] + .5 * fast
        slow = (2 / 7) * base[:, month] + (5 / 7) * slow
        if month < 5:
            continue
        previous = confirmation[:, month - 5:month - 2]
        recent = confirmation[:, month - 2:month + 1]
        old = available_median(previous)
        direction = np.sign(available_median(recent) - old)
        agreeing = np.sum(direction[:, None] * (recent - old[:, None]) > config.persistence_deadband, axis=1)
        persistence = np.clip((agreeing - 1) / 2, 0, 1)
        persistence *= np.min(quality[:, month - 5:month + 1], axis=1)
        velocity = (base[:, month] - base[:, month - 3]) / 3
        result[:, month] = persistence * (config.momentum_mix * np.tanh(velocity / config.velocity_scale)
                                           + (1 - config.momentum_mix) * np.tanh((fast - slow) / config.ema_scale))
    return result


def calculate_scores(bank: Mapping[str, np.ndarray], erp: Mapping[str, np.ndarray] | None = None,
                     config: ScoreConfig | None = None) -> dict[str, np.ndarray]:
    config = config or ScoreConfig()
    erp = erp or {}
    receipts = np.asarray(bank['receipts'], dtype=float)
    if receipts.ndim != 2 or receipts.shape[1] == 0:
        raise ValueError('financial panels must have shape (companies, months), with at least one month')
    shape = receipts.shape
    validate_optional_fields(bank, shape, {'gross_receipts': (0, np.inf), 'refunds': (0, np.inf),
                                          'funding_gap': (0, np.inf), 'hhi': (0, 1), 'hhi_quality': (0, 1),
                                          'cash_balance': (-np.inf, np.inf), 'commitments_30d': (0, np.inf),
                                          'negative_balance_fraction': (0, 1)})
    validate_optional_fields(erp, shape, {'dso_days': (0, np.inf), 'late_fraction': (0, 1), 'quality': (0, 1),
                                        'conversion': (0, 1), 'sales_growth': (-1, 1), 'hhi': (0, 1), 'hhi_quality': (0, 1)})
    expenses = panel(bank, 'expenses', shape)
    debt = panel(bank, 'debt_service', shape)
    valid = np.isfinite(receipts) & np.isfinite(expenses) & np.isfinite(debt)
    for name, values in (('receipts', receipts), ('expenses', expenses), ('debt_service', debt)):
        if np.isinf(values).any() or np.any(values[np.isfinite(values)] < 0):
            raise ValueError(f'{name} must contain nonnegative amounts or NaN for unavailable values')
    quality = np.nan_to_num(panel(bank, 'quality', shape, 1), nan=0)
    if np.any((quality < 0) | (quality > 1)):
        raise ValueError('quality must lie in [0, 1]')
    quality = quality * valid
    receipts, expenses, debt = [np.where(valid, values, 0) for values in (receipts, expenses, debt)]
    r3, e3, h3 = [rolling_sum(values, 3) for values in (receipts, expenses, debt)]
    q3 = np.nan_to_num(rolling_mean(quality, 3), nan=0)
    q6 = np.nan_to_num(rolling_mean(quality, 6), nan=0)
    flow_margin = divide(r3 - e3, r3 + e3)
    liquidity_bank = observed_blend(.5 + .5 * np.tanh(flow_margin / config.liquidity_scale), q3)
    gross = panel(bank, 'gross_receipts', shape)
    refunds = panel(bank, 'refunds', shape)
    refund_burden = divide(rolling_sum(refunds, 3), rolling_sum(gross, 3))
    refund_score = 1 - hill(refund_burden, config.refund_scale)
    regularity_score = 1 / (1 + rolling_cv(receipts))
    collections_bank = .5 * observed_blend(refund_score, q3) + .5 * observed_blend(regularity_score, np.minimum(q3, q6))
    debt_burden = divide(h3, r3 + h3)
    debt_health = observed_blend(.5 - .5 * np.tanh(debt_burden / config.debt_scale), q3)
    w_l, w_c, w_d = config.base_weights
    base_bank = 100 * (w_l * liquidity_bank + w_c * collections_bank + w_d * debt_health)
    monthly_confirmation = divide(receipts - expenses - debt, receipts + expenses + debt)
    momentum = bounded_momentum(base_bank, monthly_confirmation, quality, config)

    cash = panel(bank, 'cash_balance', shape)
    commitments = panel(bank, 'commitments_30d', shape)
    cash_known = np.isfinite(cash)
    commitments_known = np.isfinite(commitments)
    cash_positive = np.maximum(np.where(cash_known, cash, 0), 0)
    burn = np.maximum((e3 + h3 - r3) / 3, 0)
    runway_score = divide(cash_positive, cash_positive + 3 * burn)
    runway_score = np.where((cash_positive == 0) & np.isfinite(burn), 0, runway_score)
    runway_score = observed_blend(runway_score, q3)
    obligations = np.where(commitments_known, commitments, (e3 + h3) / 3)
    coverage_score = divide(cash_positive, cash_positive + obligations)
    coverage_score = np.where((cash_positive == 0) & np.isfinite(obligations), 0, coverage_score)
    cash_used = cash_known & np.isfinite(coverage_score)
    liquidity = np.where(cash_used, .5 * runway_score + .5 * np.nan_to_num(coverage_score, nan=.5), liquidity_bank)

    erp_quality = np.nan_to_num(panel(erp, 'quality', shape, 0), nan=0)
    if np.any((erp_quality < 0) | (erp_quality > 1)):
        raise ValueError('ERP quality must lie in [0, 1]')
    dso = panel(erp, 'dso_days', shape)
    late = panel(erp, 'late_fraction', shape)
    dso_score = 1 - hill(dso, config.dso_scale)
    dso_change_known = np.zeros(shape, dtype=bool)
    if shape[1] > 3:
        known = np.isfinite(dso[:, 3:]) & np.isfinite(dso[:, :-3]) & (erp_quality[:, 3:] > 0) & (erp_quality[:, :-3] > 0)
        change = dso[:, 3:] - dso[:, :-3]
        dso_score[:, 3:] = np.where(known, .75 * dso_score[:, 3:] + .25 * (.5 - .5 * np.tanh(change / config.dso_change_scale)), dso_score[:, 3:])
        dso_change_known[:, 3:] = known
    erp_collection_score = .5 * dso_score + .5 * (1 - late)
    erp_mix = config.erp_weight * erp_quality * np.isfinite(erp_collection_score)
    collections = collections_bank + erp_mix * (np.nan_to_num(erp_collection_score, nan=.5) - collections_bank)

    gap = panel(bank, 'funding_gap', shape)
    gap_ratio = divide(rolling_mean(gap, 3), (e3 + h3) / 3)
    timing_stress = np.nan_to_num(hill(gap_ratio, config.funding_gap_scale), nan=0)
    negative_fraction = panel(bank, 'negative_balance_fraction', shape)
    negative_fraction = np.where(np.isfinite(negative_fraction), negative_fraction, np.where(cash_known, cash < 0, np.nan))
    negative_stress = np.nan_to_num(hill(negative_fraction, .25), nan=0)
    stress = 1 - (1 - timing_stress) * (1 - negative_stress)
    hhi = panel(bank, 'hhi', shape)
    hhi_quality = np.nan_to_num(panel(bank, 'hhi_quality', shape, 0), nan=0)
    erp_hhi = panel(erp, 'hhi', shape)
    erp_hhi_quality = np.nan_to_num(panel(erp, 'hhi_quality', shape, 0), nan=0) * (erp_quality > 0)
    use_erp_hhi = np.isfinite(erp_hhi) & (erp_hhi_quality > hhi_quality)
    hhi = np.where(use_erp_hhi, erp_hhi, hhi)
    hhi_quality = np.where(use_erp_hhi, erp_hhi_quality, hhi_quality)
    hhi_mix = .5 * np.clip(hhi_quality, 0, 1) * np.isfinite(hhi)
    fragility = q3 * ((1 - hhi_mix) * stress + hhi_mix * np.nan_to_num(hill(hhi, config.hhi_scale), nan=0))

    cash_growth = np.zeros(shape)
    growth_reliability = np.zeros(shape)
    if shape[1] > 3:
        cash_growth[:, 3:] = np.nan_to_num(divide(r3[:, 3:] - r3[:, :-3], r3[:, 3:] + r3[:, :-3]), nan=0)
        growth_reliability[:, 3:] = np.minimum(q3[:, 3:], q3[:, :-3])
    growth_bank = np.tanh(np.maximum(cash_growth, 0) / config.growth_scale) * np.sqrt(liquidity_bank * collections_bank) * growth_reliability
    sales_growth = panel(erp, 'sales_growth', shape)
    conversion = panel(erp, 'conversion', shape)
    growth_erp = np.tanh(np.maximum(sales_growth, 0) / config.growth_scale) * np.sqrt(liquidity_bank) * np.clip(conversion, 0, 1)
    growth_mix = config.erp_weight * erp_quality * np.isfinite(growth_erp)
    growth = (1 - growth_mix) * growth_bank + growth_mix * np.nan_to_num(growth_erp, nan=0)

    liquidity_points = 100 * w_l * liquidity
    collection_points = 100 * w_c * collections
    debt_points = 100 * w_d * debt_health
    momentum_points = config.momentum_weight * momentum
    growth_points = config.growth_weight * growth
    fragility_points = -config.fragility_weight * fragility
    raw_score = liquidity_points + collection_points + debt_points + momentum_points + growth_points + fragility_points
    score = np.clip(raw_score, 0, 100)
    liquidity_available = (np.isfinite(flow_margin) & (q3 > 0)) | cash_used
    collections_available = (np.isfinite(refund_score) & (q3 > 0)) | (np.isfinite(regularity_score) & (np.minimum(q3, q6) > 0)) | (erp_mix > 0)
    fragility_evidence = (q3 > 0) & (np.isfinite(gap_ratio) | cash_known | (hhi_mix > 0))
    erp_used = (erp_mix > 0) | (growth_mix > 0) | (use_erp_hhi & (hhi_mix > 0) & (q3 > 0))
    evidence = liquidity_available | collections_available | (np.isfinite(debt_burden) & (q3 > 0)) | fragility_evidence | erp_used
    return {'score': score, 'base_health': liquidity_points + collection_points + debt_points,
            'L': liquidity, 'L_bank': liquidity_bank, 'C': collections, 'C_bank': collections_bank, 'D': debt_health,
            'momentum': momentum, 'growth_quality': growth, 'fragility': fragility,
            'liquidity_points': liquidity_points, 'collections_points': collection_points, 'debt_points': debt_points,
            'momentum_points': momentum_points, 'growth_points': growth_points, 'fragility_points': fragility_points,
            'clipping_points': score - raw_score, 'raw_score': raw_score,
            'erp_collection_adjustment_points': 100 * w_c * (collections - collections_bank),
            'bank_quality': q3, 'erp_weight_used': erp_mix, 'erp_growth_weight_used': growth_mix, 'erp_used': erp_used,
            'cash_known': cash_known, 'cash_used': cash_used, 'commitments_known': commitments_known, 'dso_change_known': dso_change_known,
            'hhi_used': hhi_mix > 0, 'liquidity_available': liquidity_available, 'collections_available': collections_available,
            'debt_service_observed': np.isfinite(h3) & (h3 > 0), 'fragility_evidence': fragility_evidence,
            'history_ready': np.broadcast_to(np.arange(shape[1]) >= 5, shape), 'is_prior': ~evidence}
