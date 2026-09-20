import numpy as np

from algorithm.score_engine import calculate_scores
from algorithm.score_project import build_projected_bank, score_at_horizon
from algorithm.test_score_engine import bank_fixture


def _flows(receipts=150., expenses=100., debt=5., horizon=6):
    return {
        'receipts': np.full(horizon, receipts),
        'expenses': np.full(horizon, expenses),
        'debt_service': np.full(horizon, debt),
        'refunds': np.zeros(horizon),
    }


def test_projection_never_reads_real_future():
    high = bank_fixture([150.] * 12)
    crash = bank_fixture([150.] * 12 + [10.] * 12)
    origin, horizon = 10, 6
    flows = _flows()
    a = score_at_horizon(high, 0, origin, horizon, flows)
    b = score_at_horizon(crash, 0, origin, horizon, flows)
    assert a == b


def test_build_projected_bank_history_stops_at_origin():
    bank = bank_fixture([150.] * 12 + [10.] * 12)
    panel = build_projected_bank(bank, 0, 10, 6, _flows(receipts=150.))
    np.testing.assert_allclose(panel['receipts'][0, :11], 150.)
    np.testing.assert_allclose(panel['receipts'][0, 11:], 150.)
    assert panel['receipts'].shape == (1, 17)


def test_score_at_horizon_is_finite():
    bank = bank_fixture([120.] * 18)
    value = score_at_horizon(bank, 0, 12, 6, _flows())
    assert np.isfinite(value) and 0 <= value <= 100
    observed = calculate_scores(bank)['score'][0, 12]
    assert abs(value - observed) < 15
