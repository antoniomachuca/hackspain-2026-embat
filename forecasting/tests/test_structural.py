from types import SimpleNamespace

import numpy as np
import pytest

from forecasting.experiments.structural_v1 import MODEL_INFO, make_model
from forecasting.structural import (
    PHI, StructuralForecaster, as_of_from_origin, band_width, build_projected_bank, long_rate,
    mean_reverting_path, refund_rate, run_rate, scenario_paths, score_named_path_series,
    score_named_paths, seasonal_factors, structural_prevision, volatility_m,
)

ORIGIN, HORIZON, CID = 8, 3, 'c0'
FLOW_KEYS = ('receipts', 'expenses', 'debt_service', 'refunds')


def _series():
    receipts = 100. + 8. * np.arange(12)
    expenses, debt = np.full(12, 80.), np.full(12, 10.)
    return receipts, expenses, debt, 0.1 * receipts


def _bank():
    receipts, expenses, debt, refunds = _series()
    return {k: v[None].copy() for k, v in dict(
        receipts=receipts, expenses=expenses, debt_service=debt, refunds=refunds,
        quality=np.ones(12), gross_receipts=receipts + refunds,
    ).items()}


def _samples(current=50.):
    return SimpleNamespace(company=np.array([CID]), origin=np.array([ORIGIN]), current=np.array([current]))


def test_mean_reversion_pulls_rising_series_toward_long_mean():
    receipts, expenses, debt, refunds = _series()
    short, long = run_rate(receipts, ORIGIN), long_rate(receipts, ORIGIN)
    assert short > long
    expected = mean_reverting_path(short, long, HORIZON)
    paths = scenario_paths(receipts, expenses, debt, refunds, ORIGIN, HORIZON)
    rec = paths['central']['receipts']
    np.testing.assert_allclose(rec, expected)
    assert rec[-1] < rec[0] < short
    assert rec[-1] > long
    np.testing.assert_allclose(expected[0], long + PHI * (short - long))


def test_seasonal_factor_uses_same_month_last_year_only_if_observed():
    receipts = np.full(24, 100.)
    receipts[6] = 200.
    long = long_rate(receipts, 17)
    factors = seasonal_factors(receipts, origin=17, horizon=3, long_mean=long)
    assert factors[0] == pytest.approx(min(200. / long, 2.0))  # month 18 ← month 6
    assert factors[1] == pytest.approx(100. / long)  # month 19 ← month 7
    assert factors[2] == pytest.approx(100. / long)
    none = seasonal_factors(receipts, origin=8, horizon=3, long_mean=100.)
    np.testing.assert_allclose(none, 1)


def test_scenario_paths_signs_refunds_and_fan():
    receipts, expenses, debt, refunds = _series()
    paths = scenario_paths(receipts, expenses, debt, refunds, ORIGIN, HORIZON)
    rec = paths['central']['receipts']
    assert np.all(paths['optimistic']['receipts'] > rec)
    assert np.all(rec > paths['pessimistic']['receipts'])
    assert np.all(paths['optimistic']['expenses'] < paths['central']['expenses'])
    assert np.all(paths['central']['expenses'] < paths['pessimistic']['expenses'])
    assert np.all(paths['optimistic']['debt_service'] < paths['central']['debt_service'])
    assert np.all(paths['central']['debt_service'] < paths['pessimistic']['debt_service'])
    rec_width = paths['optimistic']['receipts'] - paths['pessimistic']['receipts']
    assert rec_width[-1] > rec_width[0]
    assert band_width(0.10, 4) == pytest.approx(0.20)
    rate = refund_rate(receipts, refunds, ORIGIN)
    for name in ('pessimistic', 'central', 'optimistic'):
        np.testing.assert_allclose(paths[name]['refunds'], paths[name]['receipts'] * rate)


def test_volatility_m_clipped():
    noisy = np.random.default_rng(0).normal(100, 40, 24)
    assert 0.05 <= volatility_m(noisy, 20) <= 0.25
    assert volatility_m(np.ones(24), 20) == pytest.approx(0.05)


def test_future_leak_ignored():
    receipts, expenses, debt, refunds = _series()
    before = scenario_paths(receipts, expenses, debt, refunds, ORIGIN, HORIZON)
    leaked = receipts.copy()
    leaked[ORIGIN + 1:] += 1e6
    after = scenario_paths(leaked, expenses, debt, refunds, ORIGIN, HORIZON)
    for name in ('pessimistic', 'central', 'optimistic'):
        for key in FLOW_KEYS:
            np.testing.assert_allclose(before[name][key], after[name][key])
    bank, flows = _bank(), {k: before['central'][k] for k in FLOW_KEYS}
    panel = build_projected_bank(bank, 0, ORIGIN, HORIZON, flows)
    bank['receipts'][0, ORIGIN + 1:] += 1e6
    leaked_panel = build_projected_bank(bank, 0, ORIGIN, HORIZON, flows)
    for key in panel:
        np.testing.assert_allclose(panel[key], leaked_panel[key])
    model = StructuralForecaster(HORIZON, 419, banks={CID: (_bank(), 0)})
    pred = model.predict(_samples())
    model.banks[CID][0]['receipts'][0, ORIGIN + 1:] += 1e6
    model._score_cache.clear()
    np.testing.assert_allclose(pred, model.predict(_samples()))


def test_forecaster_ordered_bounded_and_explain():
    model = StructuralForecaster(HORIZON, 419, banks={CID: (_bank(), 0)})
    assert model.fit(None) is model and model.calibrate(None) is model
    samples = _samples()
    pred = model.predict(samples)
    assert pred.shape == (1, 3)
    assert (np.diff(pred, axis=1) >= 0).all()
    assert ((0 <= pred) & (pred <= 100)).all()
    probs = model.direction_probabilities(samples)
    np.testing.assert_allclose(probs.sum(axis=1), 1)
    exp = model.explain(samples)
    assert abs(exp['reconstruction_error']) < 1e-8
    rebuilt = (exp['current_score'] + exp['reference_delta']
               + sum(c['points'] for c in exp['contributions'])
               + exp['other_points'] + exp['calibration_points'] + exp['clipping_points'])
    assert rebuilt == pytest.approx(exp['predicted_score'])
    assert rebuilt == pytest.approx(pred[0, 1])


def test_make_model_metadata():
    assert MODEL_INFO['name'] == 'structural_v2'
    assert MODEL_INFO['complexity_rank'] == 3
    assert make_model(3, 419).name == 'structural_v2'


def _named(paths):
    return {name: {k: paths[name][k] for k in FLOW_KEYS}
            for name in ('pessimistic', 'central', 'optimistic')}


def _long_bank():
    n = 24
    receipts = 100. + 4. * np.arange(n)
    expenses, debt = np.full(n, 80.), np.full(n, 10.)
    refunds = 0.1 * receipts
    return {k: v[None].copy() for k, v in dict(
        receipts=receipts, expenses=expenses, debt_service=debt, refunds=refunds,
        quality=np.ones(n), gross_receipts=receipts + refunds,
    ).items()}


def test_monthly_series_matches_horizon_score():
    bank = _bank()
    named = _named(scenario_paths(*_series(), ORIGIN, HORIZON))
    last = score_named_paths(bank, 0, ORIGIN, HORIZON, named)
    current, series = score_named_path_series(bank, 0, ORIGIN, HORIZON, named)
    assert 0 <= current <= 100
    for name in named:
        assert series[name].shape == (HORIZON,)
        assert ((0 <= series[name]) & (series[name] <= 100)).all()
        np.testing.assert_allclose(series[name][-1], last[name])


def test_structural_prevision_product_payload():
    banks = {CID: (_long_bank(), 0)}
    payload = structural_prevision(CID, meses=12, banks=banks)
    assert payload['model'] == 'structural_v2'
    assert payload['status'] == 'available'
    assert payload['meses'] == 12
    assert payload['as_of'] == '2026-08-01'
    for key in ('alto', 'medio', 'bajo'):
        assert len(payload[key]) == 12
        assert all(0 <= v <= 100 for v in payload[key])
    assert 0 <= payload['current_score'] <= 100
    assert structural_prevision('missing', banks=banks) is None
    short = structural_prevision(CID, meses=12, banks=banks, origin=0)
    assert short['status'] == 'insufficient_history'
    assert short['alto'] == []
    via_model = StructuralForecaster(12, 419, banks=banks).prevision(CID)
    assert via_model['medio'] == payload['medio']


def test_as_of_from_origin_calendar():
    assert as_of_from_origin(0) == '2024-09-01'
    assert as_of_from_origin(23) == '2026-08-01'
