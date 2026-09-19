"""Regresión lineal robusta (Huber) con alpha y epsilon por GroupKFold(5) en train."""
from sklearn.linear_model import HuberRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from forecasting.experiments.common import LinearForecaster

MODEL_INFO = {
    'name': 'huber_linear',
    'approach': 'Lineal con pérdida Huber sobre delta de score; alpha y epsilon por GroupKFold(5) en train.',
    'complexity_rank': 4,
    'complexity_reason': 'Lineal con explicación exacta; mismo rango que ridge.',
}

GRID = [{'alpha': a, 'epsilon': e}
        for a in (1e-3, 1e-2, 0.1, 1, 10, 30, 100) for e in (1.35, 2.0)]


def make_estimator(alpha, epsilon):
    return Pipeline([('scale', StandardScaler()),
                     ('estimator', HuberRegressor(alpha=alpha, epsilon=epsilon, max_iter=1000))])


def make_model(horizon, seed):
    return LinearForecaster(MODEL_INFO['name'], horizon, make_estimator, GRID, seed)
