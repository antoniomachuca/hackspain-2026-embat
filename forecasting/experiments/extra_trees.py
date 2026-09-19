"""Working contribution example: copy this module and change the estimator."""
from sklearn.ensemble import ExtraTreesRegressor

from forecasting.adapters import EstimatorForecaster

MODEL_INFO = {
    'name': 'extra_trees_v1',
    'approach': 'ExtraTrees con profundidad limitada; target delta de score, features bancarias.',
    'complexity_rank': 6,
    'complexity_reason': 'Ensemble de árboles con explicación por sustitución, como random forest.',
}


def make_model(horizon, seed):
    return EstimatorForecaster(MODEL_INFO['name'], horizon,
        ExtraTreesRegressor(n_estimators=80, max_depth=7, min_samples_leaf=15,
                            max_features=.8, n_jobs=2, random_state=seed), seed)
