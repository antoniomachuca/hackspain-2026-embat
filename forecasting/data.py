"""Causal supervised samples shared by benchmark and production export."""
import hashlib
from dataclasses import dataclass

import numpy as np

from forecasting.context import INDICATORS, context_features
from forecasting.country import known_country
from algorithm.score_engine import calculate_scores

FEATURE_NAMES = (
    'score_actual', 'score_media_3m', 'score_media_6m', 'pendiente_6m', 'volatilidad_6m',
    'liquidez', 'cobros', 'deuda', 'momentum', 'crecimiento', 'fragilidad',
    'margen_flujos', 'margen_media_3m', 'margen_media_6m', 'calidad',
    'log_cobros', 'log_pagos', 'carga_deuda', 'concentracion', 'concentracion_ausente',
    'mes_seno', 'mes_coseno', 'pais_ausente', 'sector_ausente',
) + tuple(f'{indicator}_{part}' for indicator in INDICATORS for part in ('valor', 'ausente', 'edad_dias'))
INTERNAL_FEATURES = 24


def split_groups(companies, seed=419):
    """Whole business groups: 60% train, 20% calibration, 10% validation, 10% test."""
    groups = sorted({c['group_id'] for c in companies})
    if len(groups) < 10:
        raise ValueError('At least 10 business groups required for four independent partitions')
    groups.sort(key=lambda g: hashlib.sha256(f'{seed}:{g}'.encode()).hexdigest())
    n = len(groups)
    return {g: ('train' if j < int(.6*n) else 'calibration' if j < int(.8*n)
                else 'validation' if j < int(.9*n) else 'test') for j, g in enumerate(groups)}


def feature_panel(bank, companies, as_of, context=(), allow_assumed=False):
    scores = calculate_scores(bank)
    score = scores['score']
    n, months = score.shape
    features = np.full((n, months, len(FEATURE_NAMES)), np.nan)
    external = context_features(companies, as_of, context, allow_assumed)
    r, e, d = (bank[k] for k in ('receipts', 'expenses', 'debt_service'))
    for t in range(5, months):
        history = score[:, t-5:t+1]
        hhi = bank.get('hhi', np.full_like(score, np.nan))[:, t]
        calendar_month = int(as_of[t][5:7])
        features[:, t, :INTERNAL_FEATURES] = np.column_stack([
            score[:, t], history[:, -3:].mean(axis=1), history.mean(axis=1),
            (history @ (np.arange(6)-2.5))/17.5, history.std(axis=1),
            *[scores[k][:, t] for k in ('liquidity_points', 'collections_points', 'debt_points',
                                      'momentum_points', 'growth_points', 'fragility_points')],
            scores['monthly_flow_margin'][:, t],
            scores['monthly_flow_margin'][:, t-2:t+1].mean(axis=1),
            scores['monthly_flow_margin'][:, t-5:t+1].mean(axis=1),
            scores['bank_quality'][:, t], np.log1p(np.nan_to_num(r[:, t])),
            np.log1p(np.nan_to_num(e[:, t])),
            np.nan_to_num(d[:, t]/np.maximum(r[:, t]+d[:, t], 1)),
            np.nan_to_num(hhi), ~np.isfinite(hhi),
            np.full(n, np.sin(2*np.pi*calendar_month/12)),
            np.full(n, np.cos(2*np.pi*calendar_month/12)),
            [not known_country(c.get('country')) for c in companies],
            [not bool(c.get('sector')) for c in companies],
        ])
    features[:, :, INTERNAL_FEATURES:] = external
    observed = (scores['monthly_data_quality'] >= .8) & (np.nan_to_num(r+e+d) > 0)
    eligible = np.zeros((n, months), dtype=bool)
    for t in range(5, months):
        eligible[:, t] = observed[:, t-5:t+1].all(axis=1) & ~scores['is_prior'][:, t]
    return features, scores, eligible


@dataclass
class Samples:
    x: np.ndarray
    y: np.ndarray
    current: np.ndarray
    seasonal: np.ndarray
    company: np.ndarray
    group: np.ndarray
    origin: np.ndarray
    target_end: np.ndarray

    def take(self, mask):
        return Samples(**{k: v[mask] for k, v in vars(self).items()})


def make_samples(features, scores, eligible, companies, horizon):
    n, months = eligible.shape
    if not 1 <= horizon < months:
        raise ValueError('Horizon must be positive and shorter than history')
    selected = eligible[:, :months-horizon].copy()
    # Low quality target histories are not valid labels, and are counted as exclusions.
    for t in range(months-horizon):
        selected[:, t] &= eligible[:, t+horizon]
    ci, origins = np.where(selected)
    ends = origins+horizon
    current = scores['score'][ci, origins]
    previous_year = ends-12
    known_season = (previous_year >= 0) & (previous_year <= origins)
    historical_index = np.maximum(previous_year, 0)
    known_season &= eligible[ci, historical_index]
    seasonal = np.where(known_season, scores['score'][ci, historical_index], current)
    return Samples(features[ci, origins], scores['score'][ci, ends], current, seasonal,
                   np.array([companies[i]['company_id'] for i in ci]),
                   np.array([companies[i]['group_id'] for i in ci]), origins, ends)


def partition_samples(samples, groups, protocol):
    labels = np.array([groups[g] for g in samples.group])
    masks = {
        'train': (labels == 'train') & (samples.target_end <= protocol['train_target_end_index']),
        'calibration': (labels == 'calibration') & (samples.origin == protocol['calibration_origin_index']),
        'validation': (labels == 'validation') & (samples.origin >= protocol['evaluation_origin_index']),
        'test': (labels == 'test') & (samples.origin >= protocol['evaluation_origin_index']),
    }
    result = {k: samples.take(mask) for k, mask in masks.items()}
    if any(len(s.y) == 0 for s in result.values()):
        raise ValueError('Empty partition: insufficient eligible history for this horizon')
    if result['train'].target_end.max() > result['calibration'].origin.min():
        raise ValueError('Training labels overlap calibration future')
    if result['calibration'].target_end.max() > result['validation'].origin.min():
        raise ValueError('Calibration labels overlap selection future')
    return result
