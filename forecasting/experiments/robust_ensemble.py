"""Media simple de deltas: huber_lineal + ridge_groupcv + media reciente."""
import time

import numpy as np

from forecasting.data import FEATURE_NAMES, INTERNAL_FEATURES
from forecasting.experiments import huber_linear, ridge_groupcv
from forecasting.models import Forecaster, group_weights

MODEL_INFO = {
    'name': 'robust_ensemble',
    'approach': 'Media de deltas de huber_linear, ridge_groupcv y trailing_mean; explicación aditiva media.',
    'complexity_rank': 8,
    'complexity_reason': 'Combinación de tres predictores; más complejo que cada miembro.',
}


class RobustEnsemble(Forecaster):
    def __init__(self, name, horizon, seed=419):
        super().__init__('damped_trend', horizon, seed)
        self.name = name
        self.width = INTERNAL_FEATURES
        self.linear_explanation = False
        self.members = [huber_linear.make_model(horizon, seed), ridge_groupcv.make_model(horizon, seed)]

    def fit(self, samples):
        start = time.perf_counter()
        x = samples.x[:, :self.width]
        weights = group_weights(samples.group)
        self.reference = np.average(x, weights=weights, axis=0)
        for member in self.members:
            member.fit(samples)
        self.selected_params = {m.name: m.selected_params for m in self.members}
        self.fit_seconds = time.perf_counter()-start
        return self

    def raw_delta(self, x, seasonal=None):
        x = x[:, :self.width]
        deltas = [m.model.predict(x) for m in self.members]
        deltas.append(x[:, 1]-x[:, 0])  # trailing_mean
        return np.mean(deltas, axis=0)

    def explain(self, sample):
        """Exact additive accounting: mean of member baselines and per-feature contributions."""
        x = sample.x[:1, :self.width]
        raw = float(self.raw_delta(sample.x[:1])[0])
        ref = self.reference
        baseline = (ref[1]-ref[0])/3
        effects = np.zeros(self.width)
        effects[0] -= (x[0, 0]-ref[0])/3
        effects[1] += (x[0, 1]-ref[1])/3
        for member in self.members:
            scaler, est = member.model.steps[0][1], member.model.steps[1][1]
            baseline += float(member.model.predict(ref[None, :])[0])/3
            effects += ((x[0]-ref)/scaler.scale_)*est.coef_/3
        contributions = [{'feature': n, 'points': float(v)} for n, v in zip(FEATURE_NAMES, effects)]
        median = float(self.predict(sample.take(np.array([0])))[0, 1])
        current = float(sample.current[0])
        calibration = float(self.residual_quantiles[1])
        clipping = median-current-raw-calibration
        return {'method': 'mean_of_additive_members', 'causal': False, 'current_score': current,
                'reference_delta': float(baseline), 'contributions': contributions,
                'calibration_points': calibration, 'clipping_points': clipping,
                'predicted_score': median,
                'reconstruction_error': median-(current+baseline+sum(c['points'] for c in contributions)+calibration+clipping)}


def make_model(horizon, seed):
    return RobustEnsemble(MODEL_INFO['name'], horizon, seed)
