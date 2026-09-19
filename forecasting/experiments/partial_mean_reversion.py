"""Reversión parcial a la media reciente: delta = lambda*(media - actual), (k, lambda) por GroupKFold."""
import time

import numpy as np

from forecasting.data import INTERNAL_FEATURES
from forecasting.experiments.common import group_cv_select
from forecasting.models import Forecaster, group_weights

MODEL_INFO = {
    'name': 'partial_mean_reversion',
    'approach': 'Delta = lambda*(media_3m|media_6m - score_actual); (k, lambda) por GroupKFold(5) en train.',
    'complexity_rank': 2,
    'complexity_reason': 'Regla lineal en dos features; complejidad similar a tendencia amortiguada.',
}

GRID = [{'k': k, 'lam': lam} for k in (1, 2) for lam in np.linspace(0, 1, 11)]


class MeanReversion:
    def __init__(self, k=1, lam=0.):
        self.k, self.lam = k, lam

    def fit(self, x, y, sample_weight=None):
        return self

    def predict(self, x):
        return self.lam*(x[:, self.k]-x[:, 0])


def make_estimator(k, lam):
    return MeanReversion(k, lam)


class MeanReversionForecaster(Forecaster):
    def __init__(self, name, horizon, seed=419):
        super().__init__('damped_trend', horizon, seed)
        self.name = name
        self.width = INTERNAL_FEATURES
        self.linear_explanation = False

    def fit(self, samples):
        start = time.perf_counter()
        x = samples.x[:, :self.width]
        weights = group_weights(samples.group)
        self.reference = np.average(x, weights=weights, axis=0)
        self.selected_params, self.cv_table = group_cv_select(
            make_estimator, GRID, x, samples.y, samples.current, samples.group, weights, self.seed)
        self.model = make_estimator(**self.selected_params).fit(x, samples.y-samples.current)
        self.fit_seconds = time.perf_counter()-start
        return self


def make_model(horizon, seed):
    return MeanReversionForecaster(MODEL_INFO['name'], horizon, seed)
