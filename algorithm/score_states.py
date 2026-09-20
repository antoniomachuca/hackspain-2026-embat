from dataclasses import dataclass

import numpy as np

from algorithm.score_engine import available_median


PENDING = 'EVALUACION_PENDIENTE'
NEGATIVE_STATES = ('TORCIENDOSE', 'DETERIORO')
POSITIVE_STATES = ('MEJORANDO', 'RECUPERACION')


@dataclass(frozen=True)
class StateConfig:
    persistence_months: int = 3
    momentum_threshold: float = .10
    base_boundary: float = 60.0
    minimum_quality: float = .50
    minimum_observed_months: int = 6
    neutral_persistence_months: int = 2
    pulse_margin_drop: float = .12
    year_over_year_deadband: float = .06

    def __post_init__(self):
        for name in ('persistence_months', 'minimum_observed_months', 'neutral_persistence_months'):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 1:
                raise ValueError(f'{name} must be a positive integer')
        if not 0 <= self.minimum_quality <= 1 or not 0 <= self.base_boundary <= 100:
            raise ValueError('invalid quality or base threshold')
        for name in ('momentum_threshold', 'pulse_margin_drop', 'year_over_year_deadband'):
            value = getattr(self, name)
            if not np.isfinite(value) or not 0 < value <= 1:
                raise ValueError(f'{name} must lie in (0, 1]')


def annual_pattern_context(scores, config):
    margin = scores['monthly_flow_margin']
    valid = scores['flow_margin_available'] & (scores['monthly_data_quality'] >= config.minimum_quality)
    available = np.zeros_like(valid)
    matched = np.zeros_like(valid)
    for month in range(14, margin.shape[1]):
        w0_start, w0_stop = max(0, month - 2), month + 1
        w1_start, w1_stop = month - 14, month - 11
        m0 = available_median(np.where(valid[:, w0_start:w0_stop], margin[:, w0_start:w0_stop], np.nan))
        m1 = available_median(np.where(valid[:, w1_start:w1_stop], margin[:, w1_start:w1_stop], np.nan))
        comp0 = valid[:, w0_start:w0_stop].sum(axis=1) >= 2
        comp1 = valid[:, w1_start:w1_stop].sum(axis=1) >= 2
        level_match = np.abs(m0 - m1) <= config.year_over_year_deadband
        if month >= 17:
            w2_start, w2_stop = month - 5, month - 2
            w3_start, w3_stop = month - 17, month - 14
            m2 = available_median(np.where(valid[:, w2_start:w2_stop], margin[:, w2_start:w2_stop], np.nan))
            m3 = available_median(np.where(valid[:, w3_start:w3_stop], margin[:, w3_start:w3_stop], np.nan))
            comp2 = valid[:, w2_start:w2_stop].sum(axis=1) >= 2
            comp3 = valid[:, w3_start:w3_stop].sum(axis=1) >= 2
            avail = comp0 & comp1 & comp2 & comp3
            match = avail & level_match & (np.abs(m2 - m3) <= config.year_over_year_deadband)
        else:
            trend_now = margin[:, month] - margin[:, max(0, month - 3)]
            trend_last = margin[:, month - 12] - margin[:, max(0, month - 15)]
            trend_match = np.abs(trend_now - trend_last) <= config.year_over_year_deadband
            avail = comp0 & comp1
            match = avail & level_match & trend_match
        available[:, month] = avail
        matched[:, month] = match
    return available, matched


def classify_states(scores, config=None):
    config = config or StateConfig()
    required = ('score', 'base_health', 'momentum', 'bank_quality', 'is_prior', 'momentum_ready', 'observed_months',
                'monthly_flow_margin', 'monthly_data_quality', 'flow_margin_available')
    missing = [key for key in required if key not in scores]
    if missing:
        raise ValueError(f'Snapshot lacks trajectory inputs {missing}; rerun calc_score.')
    shape = scores['score'].shape
    if any(np.asarray(scores[key]).shape != shape for key in required):
        raise ValueError('trajectory inputs must share (companies, months) shape')
    state_quality = np.zeros(shape)
    state_quality[:, 3:] = np.minimum(scores['bank_quality'][:, 3:], scores['bank_quality'][:, :-3])
    eligible = scores['momentum_ready'] & ~scores['is_prior'] & (scores['observed_months'] >= config.minimum_observed_months) & (state_quality >= config.minimum_quality)
    states = np.full(shape, PENDING, dtype='<U24')
    provisional = np.ones(shape, dtype=bool)
    positive_streak = np.zeros(shape[0], dtype=int)
    negative_streak = positive_streak.copy()
    neutral_streak = positive_streak.copy()
    seasonality_available, annual_match = annual_pattern_context(scores, config)
    for month in range(shape[1]):
        valid = eligible[:, month]
        positive = valid & ~annual_match[:, month] & (scores['momentum'][:, month] > config.momentum_threshold)
        negative = valid & ~annual_match[:, month] & (scores['momentum'][:, month] < -config.momentum_threshold)
        positive_streak = np.where(positive, positive_streak + 1, 0)
        negative_streak = np.where(negative, negative_streak + 1, 0)
        neutral_streak = np.where(valid & ~positive & ~negative, neutral_streak + 1, 0)
        current = np.full(shape[0], 'ESTABLE', dtype='<U24')
        previous = states[:, month - 1] if month else np.full(shape[0], PENDING)
        directional_previous = np.isin(previous, NEGATIVE_STATES + POSITIVE_STATES)
        raw_negative = valid & (scores['momentum'][:, month] < -config.momentum_threshold)
        raw_positive = valid & (scores['momentum'][:, month] > config.momentum_threshold)
        score_drop = (scores['score'][:, month] < scores['score'][:, month - 1] - 3.0) if month else np.zeros(shape[0], dtype=bool)
        score_rise = (scores['score'][:, month] > scores['score'][:, month - 1] + 3.0) if month else np.zeros(shape[0], dtype=bool)
        opposing_negative = np.isin(previous, POSITIVE_STATES) & (raw_negative | score_drop)
        opposing_positive = np.isin(previous, NEGATIVE_STATES) & (raw_positive | score_rise)
        opposing = opposing_negative | opposing_positive
        hold = directional_previous & ~opposing & (neutral_streak < config.neutral_persistence_months)
        current[hold] = previous[hold]
        confirmed_negative = negative_streak >= config.persistence_months
        confirmed_positive = positive_streak >= config.persistence_months
        current[confirmed_negative] = np.where(scores['base_health'][confirmed_negative, month] >= config.base_boundary, 'TORCIENDOSE', 'DETERIORO')
        if month:
            recent_states = states[:, max(0, month - 6):month]
            previously_weak = np.isin(recent_states, NEGATIVE_STATES).any(axis=1)
            previously_weak |= np.median(scores['base_health'][:, max(0, month - 3):month], axis=1) < config.base_boundary
        else:
            previously_weak = np.zeros(shape[0], dtype=bool)
        current[confirmed_positive] = np.where(previously_weak[confirmed_positive], 'RECUPERACION', 'MEJORANDO')
        pulse = np.zeros(shape[0], dtype=bool)
        if month >= 3:
            history_valid = scores['flow_margin_available'][:, month - 3:month]
            old = available_median(np.where(history_valid, scores['monthly_flow_margin'][:, month - 3:month], np.nan))
            pulse = (history_valid.sum(axis=1) >= 2) & scores['flow_margin_available'][:, month] & (scores['monthly_data_quality'][:, month] >= config.minimum_quality)
            pulse &= scores['monthly_flow_margin'][:, month] < old - config.pulse_margin_drop
        pulse &= valid & ~confirmed_negative & ~confirmed_positive & ~directional_previous
        current[pulse] = 'BACHE'
        current[~valid] = PENDING
        states[:, month] = current
        provisional[:, month] = ~valid | (current == 'BACHE')
    health_band = np.where(scores['score'] >= 70, 'SOLIDA', np.where(scores['score'] < 40, 'DEBIL', 'INTERMEDIA'))
    health_band = np.where(scores['bank_quality'] < config.minimum_quality, 'COBERTURA_LIMITADA', health_band)
    health_band = np.where(scores['is_prior'], 'SIN_EVIDENCIA', health_band)
    reason = np.where(scores['is_prior'], 'sin_evidencia', np.where(~scores['momentum_ready'], 'historia_comparable_insuficiente', np.where(state_quality < config.minimum_quality, 'cobertura_limitada', 'evaluable')))
    return {'state': states, 'state_eligible': eligible, 'state_provisional': provisional, 'state_quality': state_quality,
            'health_band': health_band, 'state_evaluation_reason': reason,
            'seasonality_available': seasonality_available, 'annual_pattern_match': annual_match}
