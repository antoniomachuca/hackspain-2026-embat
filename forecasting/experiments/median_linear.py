"""Regresión por la mediana (quantile 0.5) alineada con MAE; alpha por GroupKFold(5) en train."""
from sklearn.linear_model import QuantileRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from forecasting.experiments.common import LinearForecaster

MODEL_INFO = {
    'name': 'median_linear',
    'approach': 'Lineal por cuantil 0.5 (pérdida pinball = MAE) sobre delta; alpha por GroupKFold(5) en train.',
    'complexity_rank': 4,
    'complexity_reason': 'Lineal con explicación exacta; mismo rango que ridge.',
}

GRID = [{'alpha': a} for a in (0.001, 0.01, 0.05, 0.2, 1)]


def make_estimator(alpha):
    return Pipeline([('scale', StandardScaler()),
                     ('estimator', QuantileRegressor(quantile=.5, alpha=alpha, solver='highs'))])


def make_model(horizon, seed):
    return LinearForecaster(MODEL_INFO['name'], horizon, make_estimator, GRID, seed)
