"""Centro Huber afinado + cuantiles 0.1/0.9 por QuantileRegressor con ajuste conformal."""
from sklearn.linear_model import QuantileRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from forecasting.experiments.common import weight_param
from forecasting.experiments.huber_linear import GRID, make_estimator
from forecasting.experiments.common import LinearForecaster
from forecasting.models import group_weights

MODEL_INFO = {
    'name': 'huber_cqr',
    'approach': 'Centro Huber (GroupKFold en train) + intervalos CQR con QuantileRegressor 0.1/0.9.',
    'complexity_rank': 5,
    'complexity_reason': 'Lineal con explicación exacta más dos modelos de cuantiles conformales.',
}


class HuberCQR(LinearForecaster):
    def fit(self, samples):
        super().fit(samples)
        x = samples.x[:, :self.width]
        delta = samples.y-samples.current
        weights = group_weights(samples.group)
        self.quantiles = []
        for q in (.1, .9):
            model = Pipeline([('scale', StandardScaler()),
                              ('estimator', QuantileRegressor(quantile=q, alpha=0.05, solver='highs'))])
            model.fit(x, delta, **{weight_param(model): weights})
            self.quantiles.append(model)
        return self


def make_model(horizon, seed):
    return HuberCQR(MODEL_INFO['name'], horizon, make_estimator, GRID, seed)
