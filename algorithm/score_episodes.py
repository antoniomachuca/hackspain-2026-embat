"""Episodios de cambio: cuándo se vio venir. Dominio puro, sin HTTP (ver EPISODIOS.md)."""
from dataclasses import dataclass

import numpy as np

from algorithm.score_monitor import directional_event_matrix
from algorithm.score_outlook import associate_outlook, expired_unassociated, familia_de, texto_familia
from algorithm.score_states import NEGATIVE_STATES, POSITIVE_STATES, PENDING, StateConfig

MESES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
SEVERITY = {'TORCIENDOSE': 1, 'DETERIORO': 2, 'MEJORANDO': 1, 'RECUPERACION': 2}
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


def _text(direction, deteccion, senales, perspectiva):
    frases = ', '.join(PHRASES[direction][s['senal']] for s in senales) or 'sin un bloque dominante'
    mejora = f'Detectamos señales de {direction} en {_mes(deteccion)}: {frases}.'
    return texto_familia(direction, deteccion, senales, perspectiva, mejora)


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
            if event == -direction_of[open_ep['direccion']]:
                open_ep['estado'] = 'cerrado'
                open_ep['cierre'] = str(as_of[t])
                open_ep['motivo_cierre'] = 'cambio_direccion'
                episodes.append(open_ep)
                open_ep = None
                neutral = 0
            elif states[t] in direction_states[open_ep['direccion']]:
                # Escalada = subida de gravedad dentro del episodio (TORCIENDOSE→DETERIORO,
                # MEJORANDO→RECUPERACION), se compara el estado mes a mes sin depender de los
                # eventos del monitor. Una reentrada igual o más leve tras un mes neutro no
                # escala, pero sí reinicia el contador de cierre.
                neutral = 0
                if SEVERITY.get(str(states[t]), 0) > SEVERITY.get(open_ep['_ultimo_estado'], 0):
                    open_ep['escaladas'].append({'as_of': str(as_of[t]), 'estado': str(states[t])})
                open_ep['_ultimo_estado'] = str(states[t])
            elif str(states[t]) == 'BACHE':
                # El pulso no cuenta para cerrar: no incrementa el contador ni lo reinicia.
                pass
            else:
                neutral += 1
                if neutral >= state_config.neutral_persistence_months:
                    open_ep['estado'] = 'cerrado'
                    open_ep['cierre'] = str(as_of[t])
                    open_ep['motivo_cierre'] = 'sin_evaluacion' if states[t] == PENDING else 'estabilizacion'
                    episodes.append(open_ep)
                    open_ep = None
                    neutral = 0
        if event and open_ep is None:
            direction = 'deterioro' if event < 0 else 'mejora'
            open_ep = {'direccion': direction, 'estado': 'activo', 'cierre': None, 'motivo_cierre': None,
                       'deteccion': str(as_of[t]), 'estado_deteccion': str(states[t]),
                       'score_deteccion': float(panels['score'][c, t]),
                       'escaladas': [], '_t': t, '_ultimo_estado': str(states[t])}
            neutral = 0
    if open_ep is not None:
        episodes.append(open_ep)
    result = []
    for ep in episodes:
        t = ep.pop('_t')
        ep.pop('_ultimo_estado')
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
            'texto': _text(ep['direccion'], ep['deteccion'], senales, None),
        })
        result.append((ep, t))
    return result


def _attach_outlook(built, panels, c, outlook, persistence_months):
    associated = []
    as_of = panels['as_of']
    outlook_row = outlook['outlook'][c]
    score_row = panels['score'][c]
    projected_row = outlook['outlook_score'][c]
    for ep, t in built:
        perspectiva, streak = associate_outlook(
            ep, t, outlook_row, score_row, projected_row, as_of, persistence_months)
        ep['perspectiva'] = perspectiva
        if perspectiva:
            ep['familia'] = familia_de(perspectiva)
            associated.append(streak)
        ep['texto'] = _text(ep['direccion'], ep['deteccion'], ep['senales'], perspectiva)
    return expired_unassociated(outlook_row, as_of, associated)


def _camino_marca(ep):
    p = ep.get('perspectiva')
    if not p or ep.get('direccion') != 'deterioro':
        return None
    return {
        'as_of': p['as_of'],
        'outlook': p['outlook'],
        'score_observado': p['score_observado'],
        'score_proyectado': p['score_proyectado'],
        'familia': ep.get('familia', 'salud'),
    }


def build_episodes(panels, state_config=None, config=None, bank=None, ap_pending=None, outlook=None):
    """dict[company_id -> contrato de episodios] a partir de los paneles de score + estados."""
    state_config = state_config or StateConfig()
    config = config or EpisodeConfig()
    events = directional_event_matrix(panels)
    parametros = {'persistence_months': state_config.persistence_months,
                  'neutral_persistence_months': state_config.neutral_persistence_months,
                  'material_delta': config.material_delta,
                  'material_persistence': config.material_persistence,
                  'bands': list(config.bands)}
    if outlook is None and bank is not None:
        from algorithm.score_outlook import compute_outlook
        outlook = compute_outlook(bank, panels, ap_pending=ap_pending)
    out = {}
    for c, company_id in enumerate(panels['company_id']):
        built = _company_episodes(panels, c, events, state_config, config)
        sin_aviso = []
        if outlook is not None:
            sin_aviso = _attach_outlook(built, panels, c, outlook, state_config.persistence_months)
        episodios = [ep for ep, _ in built]
        destacado = next((i for i, e in enumerate(episodios) if e['estado'] == 'activo'),
                         len(episodios) - 1 if episodios else None)
        if destacado is None:
            marcas = {'deteccion': None, 'camino': None, 'texto': ''}
        else:
            ep = episodios[destacado]
            marcas = {'deteccion': {'as_of': ep['deteccion'], 'state': ep['estado_deteccion'],
                                    'score': ep['score_deteccion'], 'direccion': ep['direccion']},
                      'camino': _camino_marca(ep), 'texto': ep['texto']}
        out[str(company_id)] = {'episodios': episodios, 'episodio_destacado': destacado,
                                'perspectivas_sin_aviso': sin_aviso,
                                'trayectoria_marcas': marcas,
                                'parametros': parametros}
    return out


def empty_company_episodes(state_config=None, config=None):
    state_config = state_config or StateConfig()
    config = config or EpisodeConfig()
    return {'episodios': [], 'episodio_destacado': None, 'perspectivas_sin_aviso': [],
            'trayectoria_marcas': {'deteccion': None, 'camino': None, 'texto': ''},
            'parametros': {'persistence_months': state_config.persistence_months,
                           'neutral_persistence_months': state_config.neutral_persistence_months,
                           'material_delta': config.material_delta,
                           'material_persistence': config.material_persistence,
                           'bands': list(config.bands)}}


def slice_company_panels(panels, company_id):
    """Recorte (1, meses) de una empresa. `(None, None)` si no está."""
    ids = np.asarray(panels['company_id']).astype(str)
    hits = np.flatnonzero(ids == str(company_id))
    if hits.size == 0:
        return None, None
    i = int(hits[0])
    n = int(np.asarray(panels['score']).shape[0])
    out = {}
    for key, value in panels.items():
        arr = np.asarray(value)
        if arr.ndim == 2 and arr.shape[0] == n:
            out[key] = arr[i:i + 1]
        elif arr.ndim == 1 and arr.shape[0] == n:
            out[key] = arr[i:i + 1]
        else:
            out[key] = arr
    return out, i


def _slice_aligned_bank(bank, i, n):
    out = {}
    for key, value in bank.items():
        arr = np.asarray(value)
        if arr.ndim == 2 and arr.shape[0] == n:
            out[key] = arr[i:i + 1]
        elif arr.ndim == 1 and arr.shape[0] == n:
            out[key] = arr[i:i + 1]
        else:
            out[key] = arr
    return out


def episodes_for_company(company_id, panels, bank=None, ap_pending=None, state_config=None, config=None, outlook=None):
    """Contrato de una empresa. El API llama esto; no hay snapshot JSON."""
    sliced, i = slice_company_panels(panels, company_id)
    if sliced is None:
        return empty_company_episodes(state_config, config)
    n = int(np.asarray(panels['score']).shape[0])
    bank_s = None
    if bank is not None:
        receipts = np.asarray(bank['receipts'])
        bank_s = bank if receipts.ndim == 2 and receipts.shape[0] == 1 else _slice_aligned_bank(bank, i, n)
    ap_s = None
    if ap_pending is not None:
        ap = np.asarray(ap_pending, dtype=float).reshape(-1)
        if ap.size == 1:
            ap_s = ap
        elif ap.size == n:
            ap_s = ap[i:i + 1]
    return build_episodes(sliced, state_config=state_config, config=config,
                          bank=bank_s, ap_pending=ap_s, outlook=outlook)[str(company_id)]
