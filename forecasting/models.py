"""Small-data forecasting candidates, calibrated scenarios and additive explanations."""
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from forecasting.data import FEATURE_NAMES, INTERNAL_FEATURES

CANDIDATES = ('persistence', 'trailing_mean', 'damped_trend', 'seasonal', 'ridge',
              'ridge_context', 'random_forest', 'boosting', 'boosting_context', 'quantile_boosting')


def group_weights(groups):
    _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    weights = 1/counts[inverse]
    return weights/weights.mean()


def weighted_quantile(values, weights, q):
    order = np.argsort(values)
    return float(np.interp(q, (np.cumsum(weights[order])-.5*weights[order])/weights.sum(), values[order]))


class Forecaster:
    def __init__(self, name, horizon, seed=419):
        if name not in CANDIDATES:
            raise ValueError(name)
        self.name, self.horizon, self.seed = name, horizon, seed
        self.linear_explanation = name.startswith('ridge')
        self.width = len(FEATURE_NAMES) if name.endswith('_context') else INTERNAL_FEATURES
        self.model = None
        self.quantiles = []
        self.residual_quantiles = np.zeros(3)
        self.interval_adjustment = 0.
        self.calibration_residuals = np.array([])
        self.calibration_weights = np.array([])

    def fit(self, samples):
        start = time.perf_counter()
        x, y = samples.x[:, :self.width], samples.y-samples.current
        weights = group_weights(samples.group)
        self.reference = np.average(x, weights=weights, axis=0)
        if self.name.startswith('ridge'):
            self.model = make_pipeline(StandardScaler(), Ridge(alpha=30))
            self.model.fit(x, y, ridge__sample_weight=weights)
        elif self.name == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=80, max_depth=7, min_samples_leaf=15,
                                              max_features=.8, n_jobs=2, random_state=self.seed)
            self.model.fit(x, y, sample_weight=weights)
        elif 'boosting' in self.name:
            def booster(**kwargs):
                return HistGradientBoostingRegressor(max_iter=80, max_leaf_nodes=7,
                    min_samples_leaf=20, l2_regularization=10, early_stopping=False,
                    random_state=self.seed, **kwargs)
            self.model = booster(loss='absolute_error')
            self.model.fit(x, y, sample_weight=weights)
            if self.name == 'quantile_boosting':
                self.quantiles = [booster(loss='quantile', quantile=q).fit(x, y, sample_weight=weights)
                                  for q in (.1, .9)]
        self.fit_seconds = time.perf_counter()-start
        return self

    def raw_delta(self, x, seasonal=None):
        if self.model is not None:
            return self.model.predict(x[:, :self.width])
        if self.name == 'persistence':
            return np.zeros(len(x))
        if self.name == 'trailing_mean':
            return x[:, 1]-x[:, 0]
        if self.name == 'damped_trend':
            return x[:, 3]*sum(.8**j for j in range(1, self.horizon+1))
        return (x[:, 0] if seasonal is None else seasonal)-x[:, 0]

    def center(self, samples):
        return np.clip(samples.current+self.raw_delta(samples.x, samples.seasonal), 0, 100)

    def calibrate(self, samples):
        self.calibration_residuals = samples.y-self.center(samples)
        self.calibration_weights = group_weights(samples.group)
        self.residual_quantiles = np.array([weighted_quantile(self.calibration_residuals,
            self.calibration_weights, q) for q in (.1, .5, .9)])
        if self.quantiles:
            lo, hi = self._raw_bounds(samples)
            nonconformity = np.maximum(lo-samples.y, samples.y-hi)
            self.interval_adjustment = max(0., weighted_quantile(nonconformity, self.calibration_weights, .8))
        return self

    def _raw_bounds(self, samples):
        bounds = np.column_stack([samples.current + m.predict(samples.x[:, :self.width]) for m in self.quantiles])
        bounds.sort(axis=1)
        return np.clip(bounds[:, 0], 0, 100), np.clip(bounds[:, 1], 0, 100)

    def predict(self, samples):
        center = self.center(samples)
        median = np.clip(center+self.residual_quantiles[1], 0, 100)
        if self.quantiles:
            lo, hi = self._raw_bounds(samples)
            lo = np.minimum(lo-self.interval_adjustment, median)
            hi = np.maximum(hi+self.interval_adjustment, median)
        else:
            lo, hi = center+self.residual_quantiles[0], center+self.residual_quantiles[2]
        return np.clip(np.column_stack([lo, median, hi]), 0, 100)

    def direction_probabilities(self, samples, deadband=3):
        # Empirical residual distribution: probabilities are estimates, evaluated by Brier score.
        p = self.center(samples)
        possible = np.clip(p[:, None]+self.calibration_residuals[None, :], 0, 100)
        delta = possible-samples.current[:, None]
        w = self.calibration_weights/self.calibration_weights.sum()
        down = (delta < -deadband) @ w
        up = (delta > deadband) @ w
        return np.column_stack([down, 1-down-up, up])

    def explain(self, sample):
        """Exact additive accounting, not causal attribution.

        Trees: sequential replacement from training reference; explicitly order-dependent.
        All corrections (calibration, score bounds) appear in the sum.
        """
        x = sample.x[:1, :self.width]
        raw = float(self.raw_delta(sample.x[:1], sample.seasonal[:1])[0])
        contributions = []
        if self.model is not None:
            ref = self.reference[None, :].copy()
            if self.linear_explanation:
                scaler, ridge = self.model.steps[0][1], self.model.steps[1][1]
                baseline = float(self.model.predict(ref)[0])
                effects = ((x[0]-self.reference)/scaler.scale_)*ridge.coef_
                contributions = [{'feature': name, 'points': float(value)} for name, value in zip(FEATURE_NAMES, effects)]
                method = 'linear_exact'
            else:
                paths = np.repeat(ref, self.width+1, axis=0)
                for j in range(self.width):
                    paths[j+1:, j] = x[0, j]
                predictions = self.model.predict(paths)
                baseline = float(predictions[0])
                contributions = [{'feature': name, 'points': float(value)}
                                 for name, value in zip(FEATURE_NAMES, np.diff(predictions))]
                method = 'sequential_replacement_order_dependent'
        else:
            baseline = 0.
            contributions = [{'feature': self.name, 'points': raw}]
            method = 'baseline_formula'
        median = float(self.predict(sample.take(np.array([0])))[0, 1])
        current = float(sample.current[0])
        calibration = float(self.residual_quantiles[1])
        clipping = median-current-raw-calibration
        return {'method': method, 'causal': False, 'current_score': current,
                'reference_delta': baseline, 'contributions': contributions,
                'calibration_points': calibration, 'clipping_points': clipping,
                'predicted_score': median,
                'reconstruction_error': median-(current+baseline+sum(c['points'] for c in contributions)+calibration+clipping)}
