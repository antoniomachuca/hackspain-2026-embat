import json

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from forecasting.benchmark import choose_model, export_forecasts, load_protocol, metrics
from forecasting.context import context_features
from forecasting.data import feature_panel, make_samples, partition_samples, split_groups
from forecasting.models import CANDIDATES, Forecaster
from forecasting.stress import generate_stress, stress_score_report, synthetic_erp
from algorythm.score_data import month_edges


@pytest.fixture
def fixture():
    rng = np.random.default_rng(77)
    n, months = 80, 24
    companies = [{'company_id': f'COMP_{i:04}', 'group_id': f'G_{i//2:03}',
                  'country': 'ES' if i % 2 else '', 'currency': 'EUR'} for i in range(n)]
    r = rng.lognormal(7, .2, (n, months))
    e = r*rng.uniform(.7, 1.15, (n, months))
    bank = {'receipts': r, 'expenses': e, 'debt_service': .08*e, 'gross_receipts': r.copy(),
            'refunds': np.zeros_like(r), 'funding_gap': .1*e, 'quality': np.ones_like(r)}
    dates = [d.isoformat() for d in month_edges()[1:]]
    return companies, bank, dates


def test_future_mutation_cannot_change_features_or_scores(fixture):
    companies, bank, dates = fixture
    x, score, eligible = feature_panel(bank, companies, dates)
    changed = {k: v.copy() for k, v in bank.items()}
    changed['receipts'][:, 12:] *= 100
    changed['expenses'][:, 12:] = 0
    xx, ss, ee = feature_panel(changed, companies, dates)
    np.testing.assert_allclose(x[:, :12], xx[:, :12], equal_nan=True)
    np.testing.assert_array_equal(score['score'][:, :12], ss['score'][:, :12])
    np.testing.assert_array_equal(eligible[:, :12], ee[:, :12])


@pytest.mark.parametrize('horizon', [1, 3, 6])
def test_group_and_time_separation(fixture, horizon):
    companies, bank, dates = fixture
    x, scores, eligible = feature_panel(bank, companies, dates)
    samples = make_samples(x, scores, eligible, companies, horizon)
    parts = partition_samples(samples, split_groups(companies), load_protocol())
    assert parts['train'].target_end.max() <= parts['calibration'].origin.min()
    assert parts['calibration'].target_end.max() <= parts['test'].origin.min()
    for name, part in parts.items():
        for other, other_part in parts.items():
            if name != other:
                assert not set(part.group) & set(other_part.group)
    assert parts['train'].origin.min() >= 5


def test_external_vintages_unknown_geography_and_revisions():
    companies = [{'country': 'ES'}, {'country': ''}]
    base = {'indicator': 'hicp', 'geo': 'ES', 'sector': '*', 'period': '2025-01-01',
            'available_at': '2025-03-01', 'availability_basis': 'verified_publication', 'value': 100}
    revision = dict(base, available_at='2025-06-01', value=500)
    rows = [base, revision, dict(base, indicator='usd_eur', geo='*', sector='*', availability_basis='assumed_lag')]
    x = context_features(companies, ['2025-02-01', '2025-03-01', '2025-04-01'], rows)
    assert x[0, 0, 10] == 1  # unavailable until publication
    assert x[0, 1, 9] == 100  # future revision cannot leak
    assert x[1, 1, 10] == 1  # unknown geography never inferred
    assert x[0, 1, 4] == 1  # assumed FX unavailable in strict run
    assert context_features(companies, ['2025-04-01'], rows, True)[0, 0, 4] == 0


@pytest.mark.parametrize('name', CANDIDATES)
def test_scenarios_probabilities_and_exact_explanations(fixture, name):
    companies, bank, dates = fixture
    x, scores, eligible = feature_panel(bank, companies, dates)
    samples = make_samples(x, scores, eligible, companies, 3)
    parts = partition_samples(samples, split_groups(companies), load_protocol())
    with threadpool_limits(limits=2):
        model = Forecaster(name, 3).fit(parts['train']).calibrate(parts['calibration'])
        pred = model.predict(parts['test'])
        assert np.isfinite(pred).all()
        assert ((0 <= pred) & (pred <= 100)).all()
        assert (np.diff(pred, axis=1) >= 0).all()
        probabilities = model.direction_probabilities(parts['test'])
        np.testing.assert_allclose(probabilities.sum(axis=1), 1)
        assert (probabilities >= -1e-12).all()
        exp = model.explain(parts['test'].take(np.array([0])))
        assert abs(exp['reconstruction_error']) < 1e-8
        assert exp['causal'] is False


def test_stress_reproducible_training_only_and_score_erp_bounds(fixture):
    companies, bank, _ = fixture
    protocol = load_protocol()
    protocol['stress_companies_per_case'] = 6
    groups = split_groups(companies)
    first = generate_stress(bank, companies, groups, protocol)
    changed = {k: v.copy() for k, v in bank.items()}
    for key in ('receipts', 'expenses', 'debt_service'):
        changed[key][:, 12:] *= 1000
        changed[key][[groups[c['group_id']] != 'train' for c in companies]] *= 1000
    second = generate_stress(changed, companies, groups, protocol)
    for (name, stressed, control, sc, oracle), (_, replicated, *_rest) in zip(first, second):
        for key in stressed:
            np.testing.assert_allclose(stressed[key], replicated[key], equal_nan=True)
        assert all(groups[next(c['group_id'] for c in companies if c['company_id'] == s['donor_id'])] == 'train' for s in sc)
        erp = synthetic_erp(stressed, name, oracle['change'])
        report = stress_score_report(stressed, control, oracle, erp, synthetic_erp(control, 'control', oracle['change']))
        assert report['finite_bounded_scores']
        assert report['erp_stress']['finite_bounded_scores']
        assert report['additive_max_error'] < 1e-8
        if name == 'temporary_dip':
            np.testing.assert_allclose(stressed['receipts'].sum(axis=1), control['receipts'].sum(axis=1))


def test_missing_and_zero_activity_abstain(fixture):
    companies, bank, dates = fixture
    for key in ('receipts', 'expenses', 'debt_service'):
        bank[key][0, -2:] = np.nan
        bank[key][1, -6:] = 0
    _, _, eligible = feature_panel(bank, companies, dates)
    assert not eligible[0, -1]
    assert not eligible[1, -1]
    assert eligible[2, -1]


def test_selection_prefers_simple_only_within_tolerance():
    scores = {n: {'macro_group_mae': 12.} for n in CANDIDATES}
    scores['ridge']['macro_group_mae'] = 10.1
    scores['boosting']['macro_group_mae'] = 10.
    assert choose_model(scores) == 'ridge'
    scores['ridge']['macro_group_mae'] = 10.3
    assert choose_model(scores) == 'boosting'


def test_export_reconstructs_forecast_and_dates(fixture, tmp_path):
    companies, bank, dates = fixture
    x, scores, eligible = feature_panel(bank, companies, dates)
    parts = partition_samples(make_samples(x, scores, eligible, companies, 6), split_groups(companies), load_protocol())
    with threadpool_limits(limits=2):
        model = Forecaster('ridge', 6).fit(parts['train']).calibrate(parts['calibration'])
        m = metrics(parts['test'], model.predict(parts['test']), model.direction_probabilities(parts['test']))
        export_forecasts(companies, dates, x, scores, eligible, {6: (model, m)}, 'test', tmp_path)
    artifact = json.loads((tmp_path/'forecasts.json').read_text())
    item = artifact['companies'][companies[0]['company_id']]
    point = item['points'][0]
    assert point['as_of'] == '2027-03-01'
    e = point['explanation']
    assert point['conservative'] == pytest.approx(e['current_score']+e['reference_delta']+
        sum(c['points'] for c in e['contributions'])+e['other_points']+e['calibration_points']+e['clipping_points'])
