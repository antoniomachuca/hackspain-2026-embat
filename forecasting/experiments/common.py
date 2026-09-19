"""Shared helpers for the second batch of candidates: GroupKFold tuning inside train."""
import time

import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

from forecasting.data import INTERNAL_FEATURES
from forecasting.models import Forecaster, group_weights


def macro_group_mae(y, pred, groups):
    """Mean over groups of mean absolute error on the clipped score scale."""
    return float(np.mean([np.mean(np.abs(y[groups == g]-pred[groups == g])) for g in np.unique(groups)]))


def weight_param(model):
    step = model.steps[-1][0] if isinstance(model, Pipeline) else None
    return f'{step}__sample_weight' if step else 'sample_weight'


def group_cv_select(make_estimator, grid, x, y, current, groups, weights, seed):
    """Pick params by macro-group MAE over GroupKFold(5) on training groups only.

    `y` is the score target; estimators fit the delta `y-current`. GroupKFold
    holds out each group exactly once, so out-of-fold predictions are pooled and
    scored once as mean over groups of mean |y - clip(current+pred, 0, 100)| —
    every group weighs equally regardless of fold size.
    """
    folds = list(GroupKFold(n_splits=5).split(x, y, groups))
    table = []
    for params in grid:
        oof = np.empty(len(y))
        for train_idx, held_idx in folds:
            model = make_estimator(**params)
            model.fit(x[train_idx], y[train_idx]-current[train_idx],
                      **{weight_param(model): weights[train_idx]})
            oof[held_idx] = np.clip(current[held_idx]+model.predict(x[held_idx]), 0, 100)
        table.append({'params': dict(params), 'macro_group_mae': macro_group_mae(y, oof, groups)})
    best = min(table, key=lambda r: r['macro_group_mae'])
    return best['params'], table


class LinearForecaster(Forecaster):
    """Forecaster whose estimator is chosen by GroupKFold on train; exact linear explanation."""

    def __init__(self, name, horizon, make_estimator, grid, seed=419):
        super().__init__('ridge', horizon, seed)
        self.name = name
        self.make_estimator = make_estimator
        self.grid = grid
        self.width = INTERNAL_FEATURES
        self.linear_explanation = True

    def fit(self, samples):
        start = time.perf_counter()
        x = samples.x[:, :self.width]
        weights = group_weights(samples.group)
        self.reference = np.average(x, weights=weights, axis=0)
        self.selected_params, self.cv_table = group_cv_select(
            self.make_estimator, self.grid, x, samples.y, samples.current,
            samples.group, weights, self.seed)
        self.model = self.make_estimator(**self.selected_params)
        self.model.fit(x, samples.y-samples.current, **{weight_param(self.model): weights})
        self.fit_seconds = time.perf_counter()-start
        return self
