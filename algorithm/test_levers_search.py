"""TDD: grid search + two rankings (salud vs circulante)."""

from algorithm.levers_catalog import RANK_TOP_N, SEARCH_BUDGET
from algorithm.levers_search import recommend_levers


def test_rankings_split_families():
    out = recommend_levers('COMP_0031')
    assert out['company_id'] == 'COMP_0031'
    assert out['n_sims'] <= SEARCH_BUDGET
    assert 'sugerencias' in out and 'opciones_circulante' in out
    for row in out['sugerencias']:
        assert row['familia'] == 'salud'
        assert row['delta_score'] is not None
    for row in out['opciones_circulante']:
        assert row['familia'] == 'circulante'
        assert row['delta_score'] is None
        assert 'caja_liberada_eur' in row


def test_sugerencias_sorted_by_delta():
    out = recommend_levers('COMP_0031')
    deltas = [r['delta_score'] for r in out['sugerencias']]
    assert deltas == sorted(deltas, reverse=True)
    assert len(out['sugerencias']) <= RANK_TOP_N


def test_circulante_sorted_by_cash():
    out = recommend_levers('COMP_0010')
    cash = [r['caja_liberada_eur'] for r in out['opciones_circulante']]
    assert cash == sorted(cash, reverse=True)


def test_does_not_rank_dpo_as_salud():
    out = recommend_levers('COMP_0031')
    ids = [r['id'] for r in out['sugerencias']]
    assert 'ampliar_dpo' not in ids
    assert 'usar_confirming' not in ids
    assert 'disponer_linea' not in ids


def test_recommended_is_from_salud_when_possible():
    out = recommend_levers('COMP_0031')
    assert out['recomendado'] is None or out['recomendado']['familia'] == 'salud'


def test_unknown_company():
    out = recommend_levers('COMP_9999')
    assert out['ok'] is False
