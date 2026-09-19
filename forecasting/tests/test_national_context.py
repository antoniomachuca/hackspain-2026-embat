from pathlib import Path

import numpy as np

from algorythm.score_data import month_edges
from forecasting.context import INDICATORS, assumed_available_at, context_features, load_context
from forecasting.data import INTERNAL_FEATURES, feature_panel


def test_national_series_join_on_alias_not_missing_or_foreign():
    row = {'indicator': 'industrial_production', 'geo': 'ES', 'sector': '*', 'period': '2025-01-01',
           'available_at': '2025-03-18', 'availability_basis': 'assumed_lag', 'value': 101.5}
    companies = [{'country': 'España'}, {'country': ''}, {'country': 'NL'}, {'country': 'ES'}]
    dates = ['2025-04-01']
    missing = context_features(companies, dates, [row])
    assert missing[0, 0, 7] == 1
    assert missing[3, 0, 7] == 1
    joined = context_features(companies, dates, [row], allow_assumed=True)
    assert joined[0, 0, 6] == 101.5 and joined[0, 0, 7] == 0
    assert joined[3, 0, 6] == 101.5
    assert joined[1, 0, 7] == 1
    assert joined[2, 0, 7] == 1


def test_star_sector_does_not_require_company_sector():
    row = {'indicator': 'hicp', 'geo': 'ES', 'sector': '*', 'period': '2025-01-01',
           'available_at': '2025-03-18', 'availability_basis': 'verified_publication', 'value': 120}
    x = context_features([{'country': 'ES'}], ['2025-04-01'], [row])
    assert x[0, 0, 9] == 120
    sectoral = dict(row, indicator='industrial_production', sector='industry', value=90)
    y = context_features([{'country': 'ES'}], ['2025-04-01'], [sectoral])
    assert y[0, 0, 7] == 1
    z = context_features([{'country': 'ES', 'sector': 'industry'}], ['2025-04-01'], [sectoral])
    assert z[0, 0, 6] == 90


def test_assumed_eurostat_lag_is_next_month_plus_45_days():
    assert assumed_available_at('2025-01-01', 45) == '2025-03-18'
    assert assumed_available_at('2024-12-01', 7) == '2025-01-08'


def test_load_context_skips_retired_sectoral_indicators(tmp_path):
    path = tmp_path / 'ctx.csv'
    path.write_text(
        'indicator,geo,sector,period,available_at,value,availability_basis,source_url,retrieved_at\n'
        'policy_rate,*,*,2025-01-01,2025-01-01,3.0,official_effective_date,http://example,2026-09-19\n'
        'construction,ES,construction,2025-01-01,2025-03-01,100,verified_publication,http://example,2026-09-19\n'
    )
    rows = load_context(path)
    assert [r['indicator'] for r in rows] == ['policy_rate']


def test_pais_ausente_uses_normalized_country():
    companies = [{'company_id': 'A', 'group_id': 'G1', 'country': 'España'},
                 {'company_id': 'B', 'group_id': 'G2', 'country': ''}]
    months = 12
    r = np.ones((2, months))
    bank = {'receipts': r, 'expenses': r, 'debt_service': .1 * r, 'gross_receipts': r.copy(),
            'refunds': np.zeros_like(r), 'funding_gap': np.zeros_like(r), 'quality': np.ones_like(r)}
    dates = [d.isoformat() for d in month_edges('2024-09-01', '2025-09-01')[1:]]
    features, _, _ = feature_panel(bank, companies, dates)
    assert features[0, 6, 22] == 0
    assert features[1, 6, 22] == 1
    assert features.shape[-1] == INTERNAL_FEATURES + 15


def test_national_snapshot_joins_spain_under_conservative_lag():
    rows = load_context(Path('forecasting/datasets/external/external_context_national_v1.csv'))
    assert {r['indicator'] for r in rows} == set(INDICATORS)
    assert all(r['sector'] == '*' for r in rows)
    spain = context_features([{'country': 'España'}], ['2026-03-01'], rows, allow_assumed=True)
    empty = context_features([{'country': ''}], ['2026-03-01'], rows, allow_assumed=True)
    assert spain[0, 0, 1] == 0
    assert spain[0, 0, 7] == 0
    assert spain[0, 0, 10] == 0
    assert spain[0, 0, 13] == 0
    assert empty[0, 0, 7] == 1
    strict = context_features([{'country': 'ES'}], ['2026-03-01'], rows)
    assert strict[0, 0, 7] == 1
