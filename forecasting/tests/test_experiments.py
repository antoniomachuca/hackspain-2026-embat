import numpy as np
import pytest
from sklearn.model_selection import GroupKFold

from forecasting.data import Samples
from forecasting.experiment import check_explanations, local_dependencies
from forecasting.experiments import (huber_cqr, huber_linear, median_linear, monotone_boosting,
                                     partial_mean_reversion, ridge_groupcv, robust_ensemble)
from forecasting.experiments.common import group_cv_select, macro_group_mae

FACTORIES = [ridge_groupcv, huber_linear, median_linear, partial_mean_reversion,
             monotone_boosting, robust_ensemble, huber_cqr]


def synthetic(seed=0, n=120, groups=('a', 'b', 'c', 'd', 'e', 'f')):
    rng = np.random.default_rng(seed)
    x = rng.uniform(20, 80, (n, 24))
    current = x[:, 0]
    return Samples(x, np.clip(current+x[:, 1]*.3+rng.normal(0, 5, n), 0, 100), current,
                   current, np.array([f'c{i}' for i in range(n)]),
                   np.array([groups[i % len(groups)] for i in range(n)]),
                   np.full(n, 8), np.full(n, 11))


@pytest.mark.parametrize('module', FACTORIES, ids=[m.MODEL_INFO['name'] for m in FACTORIES])
def test_factory_fit_calibrate_predict(module):
    model = module.make_model(horizon=1, seed=419)
    train, calibration = synthetic(0), synthetic(1)
    model.fit(train).calibrate(calibration)
    samples = synthetic(2)
    predictions = model.predict(samples)
    assert predictions.shape == (len(samples.y), 3)
    assert np.isfinite(predictions).all()
    assert (predictions >= 0).all() and (predictions <= 100).all()
    assert (np.diff(predictions, axis=1) >= 0).all()
    probabilities = model.direction_probabilities(samples)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1)
    check_explanations(model, samples)


def test_group_cv_select_returns_grid_params():
    s = synthetic()
    weights = np.ones(len(s.y))
    params, table = group_cv_select(ridge_groupcv.make_estimator, ridge_groupcv.GRID,
                                    s.x, s.y, s.current, s.group, weights, 419)
    assert params in ridge_groupcv.GRID
    assert len(table) == len(ridge_groupcv.GRID)
    assert params == min(table, key=lambda r: r['macro_group_mae'])['params']


class ConstantDelta:
    def __init__(self, delta=0.):
        self.delta = delta

    def fit(self, x, y, sample_weight=None):
        return self

    def predict(self, x):
        return np.full(len(x), self.delta)


def test_group_cv_select_pools_out_of_fold_groups():
    """Unequal fold sizes: score is pooled macro-group MAE, not the mean of fold MAEs."""
    s = synthetic(n=140, groups=('a', 'b', 'c', 'd', 'e', 'f', 'g'))  # 7 groups -> folds of 2,2,1,1,1
    group_index = {g: i for i, g in enumerate(sorted(set(s.group)))}
    offsets = np.array([0., 0., 0., 0., 0., 10., 20.])
    s.y[:] = np.clip(s.current+np.array([offsets[group_index[g]] for g in s.group]), 0, 100)
    folds = list(GroupKFold(n_splits=5).split(s.x, s.y, s.group))
    oof = np.empty(len(s.y))
    for train_idx, held_idx in folds:
        oof[held_idx] = np.clip(s.current[held_idx]+0., 0, 100)
    pooled = macro_group_mae(s.y, oof, s.group)
    fold_mean = float(np.mean([macro_group_mae(s.y[h], oof[h], s.group[h]) for _, h in folds]))
    assert not np.isclose(pooled, fold_mean)  # the two aggregations genuinely differ here
    params, table = group_cv_select(lambda delta: ConstantDelta(delta), [{'delta': 0.}, {'delta': 4.}],
                                  s.x, s.y, s.current, s.group, np.ones(len(s.y)), 419)
    assert table[0]['macro_group_mae'] == pytest.approx(pooled)
    assert params == {'delta': 0.} and params == min(table, key=lambda r: r['macro_group_mae'])['params']


def test_local_dependencies_records_experiment_modules():
    deps = local_dependencies(robust_ensemble)
    assert set(deps) >= {'forecasting/experiments/common.py',
                         'forecasting/experiments/huber_linear.py',
                         'forecasting/experiments/ridge_groupcv.py'}
    assert 'forecasting/experiments/robust_ensemble.py' not in deps
    assert all('sha256' in d and 'source_code' in d for d in deps.values())
