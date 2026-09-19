"""Boosting con restricciones monótonas en las features de nivel; test de hipótesis sin tuning."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from forecasting.adapters import EstimatorForecaster
from forecasting.data import INTERNAL_FEATURES

MODEL_INFO = {
    'name': 'monotone_boosting',
    'approach': 'Boosting MAE con monotonía: score_actual -1, medias y márgenes +1; sin tuning.',
    'complexity_rank': 7,
    'complexity_reason': 'Boosting con restricciones; explicación por sustitución, mismo rango que boosting.',
}

MONOTONIC = np.zeros(INTERNAL_FEATURES, dtype=int)
MONOTONIC[0] = -1   # score_actual
MONOTONIC[1] = 1    # score_media_3m
MONOTONIC[2] = 1    # score_media_6m
MONOTONIC[12] = 1   # margen_media_3m
MONOTONIC[13] = 1   # margen_media_6m


def make_model(horizon, seed):
    return EstimatorForecaster(MODEL_INFO['name'], horizon,
        HistGradientBoostingRegressor(loss='absolute_error', max_iter=80, max_leaf_nodes=7,
            min_samples_leaf=20, l2_regularization=10, early_stopping=False,
            monotonic_cst=MONOTONIC, random_state=seed), seed)
