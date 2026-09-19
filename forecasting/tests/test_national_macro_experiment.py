from forecasting.data import INTERNAL_FEATURES
from forecasting.experiments.national_macro import MODEL_INFO, make_model


def test_national_macro_experiment_uses_linear_context_ridge():
    assert MODEL_INFO['name'] == 'ridge_national_v1'
    assert MODEL_INFO['complexity_rank'] == 5
    model = make_model(1, 419)
    assert model.name == 'ridge_context'
    assert model.linear_explanation is True
    assert model.width > INTERNAL_FEATURES
