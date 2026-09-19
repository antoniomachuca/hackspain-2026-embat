"""Adapter for independent sklearn-compatible regressors predicting score delta."""
import time

import numpy as np

from forecasting.models import Forecaster, group_weights
from forecasting.data import FEATURE_NAMES, INTERNAL_FEATURES


class EstimatorForecaster(Forecaster):
    def __init__(self, name, horizon, estimator, seed=419, use_context=False):
        super().__init__('random_forest', horizon, seed)
        self.name = name
        self.linear_explanation = False
        self.model = estimator
        self.width = len(FEATURE_NAMES) if use_context else INTERNAL_FEATURES

    def fit(self, samples):
        start = time.perf_counter()
        x = samples.x[:, :self.width]
        weights = group_weights(samples.group)
        self.reference = np.average(x, axis=0, weights=weights)
        self.model.fit(x, samples.y-samples.current, sample_weight=weights)
        self.fit_seconds = time.perf_counter()-start
        return self
