"""Episodios de cambio: cuándo se vio venir. Dominio puro, sin HTTP (ver EPISODIOS.md)."""
from dataclasses import dataclass

import numpy as np

from algorythm.score_monitor import POINTS, directional_event_matrix
from algorythm.score_states import NEGATIVE_STATES, POSITIVE_STATES, PENDING, StateConfig

MESES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
SIGNAL_KEYS = ('liquidity_points', 'collections_points', 'debt_points', 'growth_points', 'fragility_points')
SIGNAL_NAMES = {'liquidity_points': 'liquidez', 'collections_points': 'cobros', 'debt_points': 'deuda',
                'growth_points': 'crecimiento', 'fragility_points': 'fragilidad'}
PHRASES = {
    'deterioro': {'liquidez': 'cayó la liquidez de flujos', 'cobros': 'empeoraron los cobros',
                  'deuda': 'subió la carga de deuda', 'crecimiento': 'se frenó el crecimiento',
                  'fragilidad': 'aumentó la fragilidad'},
    'mejora': {'liquidez': 'mejoró la liquidez de flujos', 'cobros': 'mejoraron los cobros',
               'deuda': 'bajó la carga de deuda', 'crecimiento': 'repuntó el crecimiento',
               'fragilidad': 'se redujo la fragilidad'},
}


@dataclass(frozen=True)
class EpisodeConfig:
    material_delta: float = 10.0
    material_persistence: int = 2
    bands: tuple = (40.0, 70.0)


def month_diff(a_iso, b_iso):
    """Months between two first-of-month ISO dates (a - b)."""
    a, b = str(a_iso)[:7], str(b_iso)[:7]
    return (int(a[:4]) - int(b[:4])) * 12 + int(a[5:7]) - int(b[5:7])


def _mes(iso):
    iso = str(iso)
    return f'{MESES[int(iso[5:7]) - 1]} {iso[:4]}'


def _criteria(direction, value, reference, config):
    """Criteria satisfied at one month, in the episode direction."""
    low, high = config.bands
    if direction == 'deterioro':
        return {'banda_70': value < high <= reference, 'banda_40': value < low <= reference,
                'delta_10': reference - value >= config.material_delta}
    return {'banda_70': value >= high > reference, 'banda_40': value >= low > reference,
            'delta_10': value - reference >= config.material_delta}


def _material_change(base_health_row, direction, ref, start, end, config):
    """First run of material_persistence months sharing a criterion; returns (month_index, criterio)."""
    run = []
    for m in range(start, end + 1):
        met = {k for k, ok in _criteria(direction, float(base_health_row[m]), ref, config).items() if ok}
        run = run + [met] if met else []
        if len(run) >= config.material_persistence:
            common = set.intersection(*run[-config.material_persistence:])
            for criterio in ('delta_10', 'banda_70', 'banda_40'):
                if criterio in common:
                    return m, criterio
    return None, None


def _signals(panels, company, month, direction):
    base = max(0, month - 3)
    rows = []
    for key in SIGNAL_KEYS:
        delta = float(panels[key][company, month] - panels[key][company, base])
        rows.append({'senal': SIGNAL_NAMES[key], 'antes': round(float(panels[key][company, base]), 2),
                     'en_deteccion': round(float(panels[key][company, month]), 2),
                     'delta_puntos': round(delta, 2)})
    if direction == 'deterioro':
        kept = sorted((r for r in rows if r['delta_puntos'] < 0), key=lambda r: r['delta_puntos'])
    else:
        kept = sorted((r for r in rows if r['delta_puntos'] > 0), key=lambda r: -r['delta_puntos'])
    return kept[:2]


def _text(direction, deteccion, senales, estado_confirmacion, meses_anticipacion):
    frases = ', '.join(PHRASES[direction][s['senal']] for s in senales) or 'sin un bloque dominante'
    first = f'Detectamos señales de {direction} en {_mes(deteccion)}: {frases}.'
    if estado_confirmacion == 'confirmado':
        n = meses_anticipacion
        second = (f'El cambio material se confirmó {n} meses después.' if n > 0 else
                  'El cambio material se confirmó el mismo mes.' if n == 0 else
                  f'El cambio material se había producido {-n} meses antes: detección tardía.')
    elif estado_confirmacion == 'pendiente':
        second = 'Cambio material pendiente de confirmación.'
    else:
        second = 'No se confirmó un cambio material antes de cerrarse el episodio.'
    return f'{first} {second}'


def _company_episodes(panels, c, events, state_config, config):
    states = panels['state'][c]
    as_of = panels['as_of']
    months = len(as_of)
    direction_states = {'deterioro': NEGATIVE_STATES, 'mejora': POSITIVE_STATES}
    direction_of = {'deterioro': -1, 'mejora': 1}
    episodes = []
    open_ep = None
    neutral = 0
    for t in range(months):
        event = int(events[c, t])
        if open_ep is not None:
            # Escalada dentro del episodio (p. ej. TORCIENDOSE→DETERIORO)
            if event == direction_of[open_ep['direccion']]:
                open_ep['escaladas'].append({'as_of': str(as_of[t]), 'estado': str(states[t])})
            elif event == -direction_of[open_ep['direccion']]:
                open_ep['estado'] = 'cerrado'
                open_ep['cierre'] = str(as_of[t])
                open_ep['motivo_cierre'] = 'cambio_direccion'
                episodes.append(open_ep)
                open_ep = None
                neutral = 0
            else:
                if states[t] not in direction_states[open_ep['direccion']]:
                    neutral += 1
                    if neutral >= state_config.neutral_persistence_months:
                        open_ep['estado'] = 'cerrado'
                        open_ep['cierre'] = str(as_of[t])
                        open_ep['motivo_cierre'] = 'sin_evaluacion' if states[t] == PENDING else 'estabilizacion'
                        episodes.append(open_ep)
                        open_ep = None
                        neutral = 0
                else:
                    neutral = 0
        if event and open_ep is None:
            direction = 'deterioro' if event < 0 else 'mejora'
            open_ep = {'direccion': direction, 'estado': 'activo', 'cierre': None, 'motivo_cierre': None,
                       'deteccion': str(as_of[t]), 'estado_deteccion': str(states[t]),
                       'score_deteccion': float(panels['score'][c, t]),
                       'escaladas': [], '_t': t}
            neutral = 0
    if open_ep is not None:
        episodes.append(open_ep)
    result = []
    for ep in episodes:
        t = ep.pop('_t')
        inicio = max(0, t - state_config.persistence_months + 1)
        ref_idx = t - state_config.persistence_months
        if ref_idx < 0 or panels['is_prior'][c, ref_idx]:
            non_prior = np.nonzero(~panels['is_prior'][c, :t + 1])[0]
            ref_idx = int(non_prior[0]) if len(non_prior) else t
        ref = float(panels['base_health'][c, ref_idx])
        end_idx = next((i for i, a in enumerate(as_of) if str(a) == ep['cierre']), months - 1) if ep['cierre'] else months - 1
        cm_idx, criterio = _material_change(panels['base_health'][c], ep['direccion'], ref, inicio, end_idx, config)
        if cm_idx is not None:
            confirmacion = 'confirmado'
            anticipacion = month_diff(as_of[cm_idx], ep['deteccion'])
            cambio = str(as_of[cm_idx])
        else:
            confirmacion = 'pendiente' if ep['estado'] == 'activo' else 'no_confirmado'
            anticipacion = None
            cambio = None
        senales = _signals(panels, c, t, ep['direccion'])
        ep.update({
            'inicio_estimado': str(as_of[inicio]),
            'referencia_base_health': ref,
            'referencia_as_of': str(as_of[ref_idx]),
            'cambio_material': cambio,
            'criterio': criterio,
            'estado_confirmacion': confirmacion,
            'meses_anticipacion': anticipacion,
            'perspectiva': None,
            'senales': senales,
            'familia': 'salud',
            'texto': _text(ep['direccion'], ep['deteccion'], senales, confirmacion, anticipacion),
        })
        result.append((ep, t))
    return result


def build_episodes(panels, state_config=None, config=None):
    """dict[company_id -> contrato de episodios] a partir de los paneles de score + estados."""
    state_config = state_config or StateConfig()
    config = config or EpisodeConfig()
    events = directional_event_matrix(panels)
    parametros = {'persistence_months': state_config.persistence_months,
                  'neutral_persistence_months': state_config.neutral_persistence_months,
                  'material_delta': config.material_delta,
                  'material_persistence': config.material_persistence,
                  'bands': list(config.bands)}
    out = {}
    for c, company_id in enumerate(panels['company_id']):
        built = _company_episodes(panels, c, events, state_config, config)
        episodios = [ep for ep, _ in built]
        destacado = next((i for i, e in enumerate(episodios) if e['estado'] == 'activo'),
                         len(episodios) - 1 if episodios else None)
        if destacado is None:
            marcas = {'deteccion': None, 'camino': None, 'texto': ''}
        else:
            ep = episodios[destacado]
            marcas = {'deteccion': {'as_of': ep['deteccion'], 'state': ep['estado_deteccion'],
                                    'score': ep['score_deteccion'], 'direccion': ep['direccion']},
                      'camino': None, 'texto': ep['texto']}
        out[str(company_id)] = {'episodios': episodios, 'episodio_destacado': destacado,
                                'perspectivas_sin_aviso': [],
                                'trayectoria_marcas': marcas,
                                'parametros': parametros}
    return out
