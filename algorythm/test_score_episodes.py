import json

import numpy as np

from algorythm.score_episodes import EpisodeConfig, SIGNAL_KEYS, build_episodes, episodes_for_company, month_diff


def make_panels(states_rows, base_health_rows, signals=None, months=24):
    """Paneles mínimos hechos a mano: estados fijados directamente, sin clasificador."""
    n = len(states_rows)
    as_of = np.array([f'{2024 + (m // 12)}-{(m % 12) + 1:02d}-01' for m in range(months)])
    panels = {
        'state': np.array(states_rows, dtype='<U24'),
        'state_eligible': np.ones((n, months), dtype=bool),
        'is_prior': np.zeros((n, months), dtype=bool),
        'score': np.array(base_health_rows, dtype=float),
        'base_health': np.array(base_health_rows, dtype=float),
        'as_of': as_of,
        'company_id': np.array([f'C{i}' for i in range(n)]),
        'group_id': np.array(['G'] * n),
    }
    for key in SIGNAL_KEYS:
        panels[key] = np.zeros((n, months))
    for key, rows in (signals or {}).items():
        panels[key] = np.array(rows, dtype=float)
    return panels


def truncate(panels, t):
    out = {}
    for key, value in panels.items():
        arr = np.asarray(value)
        out[key] = arr[:t] if key == 'as_of' else (arr[:, :t] if arr.ndim == 2 else arr)
    return out


def test_deterioro_ramp_with_escalada_and_delta_10():
    states = ['ESTABLE'] * 9 + ['TORCIENDOSE'] * 3 + ['DETERIORO'] * 5 + ['ESTABLE'] * 7
    base = [75.] * 10 + [70., 70., 64., 64., 63., 62., 62.] + [60.] * 7
    signals = {'liquidity_points': [[20.] * 6 + [14., 12., 10.] + [10.] * 15],
               'collections_points': [[15.] * 6 + [12., 10., 9.] + [9.] * 15]}
    result = build_episodes(make_panels([states], [base], signals))
    ep = result['C0']['episodios'][0]
    assert ep['direccion'] == 'deterioro' and ep['estado'] == 'cerrado'
    assert ep['deteccion'] == '2024-10-01' and ep['estado_deteccion'] == 'TORCIENDOSE'
    assert ep['escaladas'] == [{'as_of': '2025-01-01', 'estado': 'DETERIORO'}]
    assert ep['inicio_estimado'] == '2024-08-01'
    assert ep['referencia_base_health'] == 75. and ep['referencia_as_of'] == '2024-07-01'
    assert ep['cambio_material'] == '2025-02-01' and ep['criterio'] == 'delta_10'
    assert ep['meses_anticipacion'] == 4
    assert ep['estado_confirmacion'] == 'confirmado'
    assert ep['cierre'] == '2025-07-01' and ep['motivo_cierre'] == 'estabilizacion'
    assert ep['senales'][0]['senal'] == 'liquidez' and ep['senales'][0]['delta_puntos'] == -4.
    assert ep['texto'] == 'Giro persistente de salud (cobros, gastos o deuda).'
    assert 'cambio material' not in ep['texto']
    assert result['C0']['episodio_destacado'] == 0
    assert result['C0']['trayectoria_marcas']['deteccion']['as_of'] == '2024-10-01'


def test_mejora_with_positive_signals_and_banda_70():
    states = ['ESTABLE'] * 9 + ['MEJORANDO'] * 6 + ['ESTABLE'] * 9
    base = [62.] * 9 + [65., 68., 71., 71.] + [71.] * 11
    signals = {'growth_points': [[2.] * 6 + [5., 6., 7.] + [7.] * 15],
               'debt_points': [[8.] * 6 + [9., 10., 11.] + [11.] * 15],
               'fragility_points': [[-2.] * 6 + [-3., -4., -5.] + [-5.] * 15]}
    result = build_episodes(make_panels([states], [base], signals))
    ep = result['C0']['episodios'][0]
    assert ep['direccion'] == 'mejora' and ep['criterio'] == 'banda_70'
    assert ep['cambio_material'] == '2025-01-01' and ep['meses_anticipacion'] == 3
    assert all(s['delta_puntos'] > 0 for s in ep['senales'])
    assert 'señales de mejora' in ep['texto']
    assert 'cambio material' not in ep['texto']


def test_closed_without_material_change_is_no_confirmado():
    states = ['ESTABLE'] * 9 + ['TORCIENDOSE'] * 3 + ['ESTABLE'] * 12
    base = [60.] * 24
    result = build_episodes(make_panels([states], [base]))
    ep = result['C0']['episodios'][0]
    assert ep['cierre'] == '2025-02-01' and ep['motivo_cierre'] == 'estabilizacion'
    assert ep['estado_confirmacion'] == 'no_confirmado' and ep['cambio_material'] is None
    assert ep['texto'] == 'Giro persistente de salud (cobros, gastos o deuda).'
    assert 'cambio material' not in ep['texto']


def test_late_detection_has_negative_anticipation():
    states = ['ESTABLE'] * 9 + ['TORCIENDOSE'] * 3 + ['ESTABLE'] * 12
    base = [75.] * 6 + [75., 64., 64., 62.] + [60.] * 14  # ref=75 at idx6; drop 2 months before detection
    result = build_episodes(make_panels([states], [base]))
    ep = result['C0']['episodios'][0]
    assert ep['cambio_material'] == '2024-09-01'  # second month of the 7-8 run
    assert ep['meses_anticipacion'] == -1
    assert 'detección tardía' not in ep['texto']
    assert 'cambio material' not in ep['texto']


def test_direction_flip_closes_and_opens_new_episode():
    states = (['ESTABLE'] * 6 + ['TORCIENDOSE'] * 4 + ['MEJORANDO'] * 6 + ['ESTABLE'] * 8)
    base = [50.] * 24
    result = build_episodes(make_panels([states], [base]))
    eps = result['C0']['episodios']
    assert len(eps) == 2
    assert eps[0]['motivo_cierre'] == 'cambio_direccion' and eps[0]['cierre'] == '2024-11-01'
    assert eps[1]['direccion'] == 'mejora' and eps[1]['estado'] == 'cerrado'
    # Con episodio activo, el destacado es el activo
    states2 = ['ESTABLE'] * 6 + ['TORCIENDOSE'] * 4 + ['MEJORANDO'] * 14
    res2 = build_episodes(make_panels([states2], [base]))
    assert res2['C0']['episodios'][1]['estado'] == 'activo'
    assert res2['C0']['episodio_destacado'] == 1


def test_point_in_time_invariance():
    states = ['ESTABLE'] * 9 + ['TORCIENDOSE'] * 3 + ['DETERIORO'] * 5 + ['ESTABLE'] * 7
    base = [75.] * 10 + [70., 68., 64., 64., 63., 62., 62.] + [60.] * 7
    signals = {'liquidity_points': [[20.] * 6 + [14., 12., 10.] + [10.] * 15]}
    panels = make_panels([states], [base], signals)
    full = build_episodes(panels)['C0']['episodios']
    for t in (12, 16, 24):
        partial = build_episodes(truncate(panels, t))['C0']['episodios']
        limit = str(panels['as_of'][t - 1])
        old = [e for e in full if e['deteccion'] <= limit]
        assert len(partial) == len(old)
        for a, b in zip(partial, old):
            for key in ('deteccion', 'estado_deteccion', 'inicio_estimado',
                        'referencia_base_health', 'referencia_as_of', 'senales'):
                assert a[key] == b[key]


def test_signals_respect_direction():
    states = ['ESTABLE'] * 9 + ['TORCIENDOSE'] * 3 + ['ESTABLE'] * 12
    signals = {'liquidity_points': [[20.] * 6 + [14., 12., 10.] + [10.] * 15],   # delta -6
               'growth_points': [[2.] * 6 + [5., 6., 7.] + [7.] * 15]}          # delta +5
    ep = build_episodes(make_panels([states], [[60.] * 24], signals))['C0']['episodios'][0]
    assert [s['senal'] for s in ep['senales']] == ['liquidez']


def test_output_is_json_serialisable_and_company_without_episodes():
    panels = make_panels([['ESTABLE'] * 24], [60.] * 24)
    result = build_episodes(panels)
    row = result['C0']
    assert row['episodios'] == [] and row['episodio_destacado'] is None
    assert row['trayectoria_marcas'] == {'deteccion': None, 'camino': None, 'texto': ''}
    assert row['perspectivas_sin_aviso'] == []
    json.dumps(result, allow_nan=False)
    assert month_diff('2026-03-01', '2025-12-01') == 3


def test_separated_neutral_months_do_not_close_and_reentry_is_not_escalada():
    # T T T | E | T T | E | T T | E E  -> un solo episodio, cierre en el segundo neutro consecutivo
    states = (['ESTABLE'] * 6 + ['TORCIENDOSE'] * 3 + ['ESTABLE'] + ['TORCIENDOSE'] * 2 + ['ESTABLE']
              + ['TORCIENDOSE'] * 2 + ['ESTABLE'] * 2 + ['ESTABLE'] * 7)
    base = [70.] * 24
    result = build_episodes(make_panels([states], [base]))
    episodios = result['C0']['episodios']
    assert len(episodios) == 1
    ep = episodios[0]
    assert ep['deteccion'] == '2024-07-01'
    assert ep['escaladas'] == []
    assert ep['cierre'] == '2025-05-01' and ep['motivo_cierre'] == 'estabilizacion'


def test_reentry_with_lower_severity_is_not_escalada():
    # DETERIORO -> neutro -> TORCIENDOSE: la gravedad baja, no hay escalada; el episodio sigue abierto.
    states = ['ESTABLE'] * 6 + ['DETERIORO'] * 3 + ['ESTABLE'] + ['TORCIENDOSE'] * 3 + ['DETERIORO'] * 2 + ['ESTABLE'] * 9
    result = build_episodes(make_panels([states], [[50.] * 24]))
    episodios = result['C0']['episodios']
    assert len(episodios) == 1
    assert episodios[0]['estado_deteccion'] == 'DETERIORO'
    assert episodios[0]['escaladas'] == [{'as_of': '2025-02-01', 'estado': 'DETERIORO'}]


def test_direct_mejorando_to_recuperacion_is_escalada():
    # El monitor no emite evento en MEJORANDO→RECUPERACION; la escalada se detecta dentro del episodio.
    states = ['ESTABLE'] * 6 + ['MEJORANDO'] * 3 + ['RECUPERACION'] * 3 + ['ESTABLE'] * 12
    result = build_episodes(make_panels([states], [[50.] * 24]))
    episodios = result['C0']['episodios']
    assert len(episodios) == 1
    assert episodios[0]['direccion'] == 'mejora' and episodios[0]['estado_deteccion'] == 'MEJORANDO'
    assert episodios[0]['escaladas'] == [{'as_of': '2024-10-01', 'estado': 'RECUPERACION'}]


def test_bache_does_not_increment_close_counter():
    # T T T | B B | E E  — dos baches no cierran; cierran los dos ESTABLE siguientes.
    states = ['ESTABLE'] * 6 + ['TORCIENDOSE'] * 3 + ['BACHE'] * 2 + ['ESTABLE'] * 13
    result = build_episodes(make_panels([states], [[70.] * 24]))
    ep = result['C0']['episodios'][0]
    assert ep['cierre'] == '2025-01-01' and ep['motivo_cierre'] == 'estabilizacion'
    assert ep['deteccion'] == '2024-07-01'


def test_two_consecutive_baches_do_not_close():
    states = ['ESTABLE'] * 6 + ['TORCIENDOSE'] * 16 + ['BACHE'] * 2
    result = build_episodes(make_panels([states], [[70.] * 24]))
    ep = result['C0']['episodios'][0]
    assert ep['estado'] == 'activo' and ep['cierre'] is None


def test_episodes_for_company_matches_full_build():
    states = ['ESTABLE'] * 9 + ['TORCIENDOSE'] * 3 + ['ESTABLE'] * 12
    panels = make_panels([states, ['ESTABLE'] * 24], [[60.] * 24, [70.] * 24])
    full = build_episodes(panels)
    one = episodes_for_company('C0', panels)
    assert one == full['C0']
    missing = episodes_for_company('NOPE', panels)
    assert missing['episodios'] == [] and missing['episodio_destacado'] is None
