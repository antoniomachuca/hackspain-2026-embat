"""Ridge con alpha elegido por GroupKFold(5) dentro de train, métrica MAE macro por grupo."""
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from forecasting.experiments.common import LinearForecaster

MODEL_INFO = {
    'name': 'ridge_groupcv',
    'approach': 'Ridge sobre delta de score; alpha por GroupKFold(5) en train con MAE macro por grupo.',
    'complexity_rank': 4,
    'complexity_reason': 'Lineal con explicación exacta; mismo rango que ridge.',
}

GRID = [{'alpha': a} for a in (1, 3, 10, 30, 100, 300, 1000, 3000)]


def make_estimator(alpha):
    return Pipeline([('scale', StandardScaler()), ('estimator', Ridge(alpha=alpha))])


def make_model(horizon, seed):
    return LinearForecaster(MODEL_INFO['name'], horizon, make_estimator, GRID, seed)
