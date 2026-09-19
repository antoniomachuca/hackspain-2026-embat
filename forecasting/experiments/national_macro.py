"""Independent contribution: Ridge on score delta with national macro context."""
from forecasting.models import Forecaster

MODEL_INFO = {
    'name': 'ridge_national_v1',
    'approach': (
        'Ridge sobre delta de score, features bancarias internas más macro nacional '
        '(tipo BCE, USD/EUR, producción industrial, HICP y paro de España). '
        'No usa sector; el mismo join admitiría series NACE si hubiera CNAE.'
    ),
    'complexity_rank': 5,  # same declared complexity as ridge_context
    'complexity_reason': 'Ridge lineal con contexto; explicación aditiva exacta.',
}


def make_model(horizon, seed):
    return Forecaster('ridge_context', horizon, seed)
