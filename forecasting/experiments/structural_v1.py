"""Project the bank account, then apply the frozen score engine."""
from forecasting.structural import StructuralForecaster

MODEL_INFO = {
    'name': 'structural_v2',
    'approach': (
        'Proyecta cobros, pagos y deuda revirtiendo el run-rate a 3 meses hacia la media a 12 de la empresa; '
        'estacionalidad del mismo mes del año pasado si ya está observado (regla del seasonal del laboratorio); '
        'bandas por volatilidad × √h (5-25% a 1 mes). Reembolsos a ratio constante. '
        'El score se calcula con calculate_scores, no se aprende.'
    ),
    'complexity_rank': 3,
    'complexity_reason': 'Regla de cuenta + fórmula de score ya existente; sin estimador supervisado.',
}


def make_model(horizon, seed):
    return StructuralForecaster(horizon, seed)
