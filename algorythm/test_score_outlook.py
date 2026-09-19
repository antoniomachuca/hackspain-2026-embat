import numpy as np

from algorythm.score_engine import calculate_scores
from algorythm.score_episodes import build_episodes
from algorythm.score_outlook import (
    CIRCULANTE_ADVERSO, COPY_HUECO, HORIZON, NINGUNA, SALUD_ADVERSA, associate_outlook,
    compute_outlook, expired_unassociated, fires,
)
from algorythm.score_project import LONG_WINDOW, RUN_WINDOW, scores_constant_regimes, _window_mean, _window_refund_rho
from algorythm.score_states import PENDING, classify_states
from algorythm.test_score_engine import bank_fixture
from algorythm.test_score_episodes import make_panels


def _as_of(months=24):
    return np.array([f'{2024 + (m // 12)}-{(m % 12) + 1:02d}-01' for m in range(months)])


def _panels_from_bank(bank):
    output = calculate_scores(bank)
    output.update(classify_states(output))
    months = output['score'].shape[1]
    return dict(output, company_id=np.array(['C0']), group_id=np.array(['G']), as_of=_as_of(months))


def test_fires_requires_all_three_conditions():
    assert fires(54.0, 78.0, 72.0)
    assert not fires(58.0, 78.0, 54.0)   # not worse than base by 3
    assert not fires(61.0, 78.0, 72.0)   # not below 60
    assert not fires(74.0, 75.0, 80.0)   # not 3 below observed


def test_salud_run_rate_is_worse_than_12m_but_3a_needs_drop_vs_today():
    """Persist-3m identifica el régimen; Ŝ ≤ S_t−3 no dispara si el crash ya está en el score."""
    bank = bank_fixture([160.] * 16 + [35.] * 8)
    panels = _panels_from_bank(bank)
    t = 18
    rows = np.array([0])
    r3 = _window_mean(bank['receipts'], rows, t, RUN_WINDOW)
    e3 = _window_mean(bank['expenses'], rows, t, RUN_WINDOW)
    h3 = _window_mean(bank['debt_service'], rows, t, RUN_WINDOW)
    r12 = _window_mean(bank['receipts'], rows, t, LONG_WINDOW)
    e12 = _window_mean(bank['expenses'], rows, t, LONG_WINDOW)
    h12 = _window_mean(bank['debt_service'], rows, t, LONG_WINDOW)
    rho = _window_refund_rho(bank['receipts'], bank['refunds'], rows, t, RUN_WINDOW)
    scored = scores_constant_regimes(bank, rows, t, HORIZON, {
        'salud': {'receipts': r3, 'expenses': e3, 'debt_service': h3, 'refund_rho': rho},
        'base': {'receipts': r12, 'expenses': e12, 'debt_service': h12, 'refund_rho': rho},
    })
    shat, base, observed = float(scored['salud'][0]), float(scored['base'][0]), float(panels['score'][0, t])
    assert shat <= base - 3 and shat < 60
    assert not fires(shat, observed, base)
    panels['state'][:] = 'ESTABLE'
    assert (compute_outlook(bank, panels)['outlook'][0] == NINGUNA).all()


def test_pending_and_negative_states_are_not_eligible():
    bank = bank_fixture([160.] * 24)
    panels = _panels_from_bank(bank)
    ap = np.array([8e6])
    assert compute_outlook(bank, panels, ap_pending=ap)['outlook'][0, -1] == CIRCULANTE_ADVERSO
    panels['state'][0, -1] = PENDING
    assert compute_outlook(bank, panels, ap_pending=ap)['outlook'][0, -1] == NINGUNA
    panels['state'][0, -1] = 'DETERIORO'
    assert compute_outlook(bank, panels, ap_pending=ap)['outlook'][0, -1] == NINGUNA
    panels['state'][0, -1] = 'BACHE'
    assert compute_outlook(bank, panels, ap_pending=ap)['outlook'][0, -1] == CIRCULANTE_ADVERSO


def test_circulante_only_on_live_cut_and_needs_ap():
    bank = bank_fixture([160.] * 24)
    panels = _panels_from_bank(bank)
    healthy = compute_outlook(bank, panels, ap_pending=np.array([0.0]))
    assert (healthy['outlook'][0] == NINGUNA).all()
    huge = compute_outlook(bank, panels, ap_pending=np.array([8e6]))
    assert CIRCULANTE_ADVERSO in huge['outlook'][0]
    assert huge['outlook'][0, -1] == CIRCULANTE_ADVERSO
    assert (huge['outlook'][0, :-1] != CIRCULANTE_ADVERSO).all()


def test_associate_streak_alive_at_momentum_start():
    outlook = np.array([NINGUNA] * 8 + [SALUD_ADVERSA] * 3 + [NINGUNA] * 13)
    score = np.full(24, 75.)
    projected = np.full(24, np.nan)
    projected[8:11] = 50.
    as_of = _as_of()
    ep = {'direccion': 'deterioro'}
    p, streak = associate_outlook(ep, 12, outlook, score, projected, as_of, 3)
    assert streak == (8, 10)
    assert p['as_of'] == '2024-09-01'
    assert p['meses_antes_deteccion'] == 4
    assert p['outlook'] == SALUD_ADVERSA
    dead = np.array([NINGUNA] * 4 + [SALUD_ADVERSA] * 3 + [NINGUNA] * 17)
    projected2 = np.full(24, np.nan)
    projected2[4:7] = 50.
    none, _ = associate_outlook(ep, 12, dead, score, projected2, as_of, 3)
    assert none is None


def test_expired_unassociated_needs_two_months_none():
    outlook = np.array([NINGUNA] * 4 + [SALUD_ADVERSA] * 3 + [NINGUNA] * 17)
    as_of = _as_of()
    rows = expired_unassociated(outlook, as_of, associated=[], gap=2)
    assert rows == [{'inicio': '2024-05-01', 'fin': '2024-07-01'}]
    assert expired_unassociated(outlook, as_of, associated=[(4, 6)]) == []


def test_build_episodes_attaches_outlook_and_camino():
    states = ['ESTABLE'] * 12 + ['TORCIENDOSE'] * 12
    panels = make_panels([states], [[75.] * 24])
    outlook_row = np.array([NINGUNA] * 8 + [SALUD_ADVERSA] * 3 + [NINGUNA] * 13)
    projected = np.full(24, np.nan)
    projected[8:11] = 50.
    outlook = {
        'outlook': outlook_row[None],
        'outlook_score': projected[None],
        'outlook_base_score': np.full((1, 24), 72.),
    }
    result = build_episodes(panels, outlook=outlook)
    ep = result['C0']['episodios'][0]
    assert ep['deteccion'] == '2025-01-01'
    assert ep['perspectiva']['as_of'] == '2024-09-01'
    assert ep['perspectiva']['meses_antes_deteccion'] == 4
    assert ep['familia'] == 'salud'
    assert ep['texto'] == COPY_HUECO['salud']
    assert result['C0']['trayectoria_marcas']['camino']['as_of'] == '2024-09-01'
    assert result['C0']['trayectoria_marcas']['texto'] == COPY_HUECO['salud']
