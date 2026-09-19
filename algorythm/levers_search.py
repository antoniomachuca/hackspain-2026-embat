"""Grid search + two rankings (salud vs circulante). No HTTP."""

from __future__ import annotations

from typing import Any

from algorythm.levers import load_model_version, simulate_levers
from algorythm.levers_catalog import (
    AS_OF,
    DAYS_GRID,
    MODO,
    OPEX_GRID,
    RANK_TOP_N,
    REFI_GRID,
    SEARCH_BUDGET,
    family_of,
)
from algorythm.levers_cost import discount_buttons, dpo_cost_buttons
from algorythm.levers_gates import evaluate_catalog

_LABELS = {
    'adelantar_cobros': 'Adelantar cobros',
    'recortar_opex': 'Recortar opex',
    'refinanciar': 'Refinanciar',
    'renegociar_interes': 'Renegociar interés',
    'leasing_a_cuota_menor': 'Leasing a cuota menor',
    'ampliar_dpo': 'Ampliar DPO',
    'usar_confirming': 'Usar confirming',
    'ofrecer_pronto_pago_proveedor': 'Pronto pago a proveedor',
    'disponer_linea': 'Disponer línea',
    'bajar_utilizacion_linea': 'Bajar utilización de línea',
    'amortizar_linea_con_caja': 'Amortizar línea con caja',
    'vender_inversiones': 'Vender inversiones',
    'sustituir_factoring': 'Sustituir factoring',
    'reducir_concentracion': 'Reducir concentración',
    'bajar_devoluciones': 'Bajar devoluciones',
}

_ONE_SHOT = (
    'disponer_linea',
    'bajar_utilizacion_linea',
    'amortizar_linea_con_caja',
    'vender_inversiones',
    'sustituir_factoring',
    'reducir_concentracion',
    'bajar_devoluciones',
    'ofrecer_pronto_pago_proveedor',
)

_PARAM_KEYS = ('days', 'pct', 'haircut', 'tasa_descuento', 'agreement_type', 'proposed_cost_pct', 'amount_eur', 'lineas')


def _candidate(lever_id: str, **params: Any) -> dict[str, Any]:
    row: dict[str, Any] = {'id': lever_id}
    row.update({key: params[key] for key in _PARAM_KEYS if key in params})
    return row


def _sim_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {'id': candidate['id']}
    for key in _PARAM_KEYS:
        value = candidate.get(key)
        if value is not None:
            payload[key] = value
    return payload


def _label(candidate: dict[str, Any]) -> str:
    base = _LABELS.get(candidate['id'], candidate['id'].replace('_', ' '))
    bits: list[str] = []
    days = candidate.get('days')
    pct = candidate.get('pct')
    haircut = candidate.get('haircut') or candidate.get('tasa_descuento')
    cost = candidate.get('proposed_cost_pct')
    if days is not None:
        bits.append(f'{int(days)}d')
    if pct is not None:
        bits.append(f'{float(pct):.0%}')
    if haircut:
        bits.append(f'dto {float(haircut):.1%}')
    if cost and not haircut:
        bits.append(f'coste {float(cost):.1%}')
    return f'{base} ({", ".join(bits)})' if bits else base


def _tipico_dpo_cost(days: int) -> float:
    buttons = dpo_cost_buttons(days)
    for button in buttons:
        if button.get('name') == 'tipico':
            return float(button['pct'])
    if buttons:
        return float(buttons[-1]['pct'])
    return 0.02


def _build_candidates(applicable: set[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    if 'adelantar_cobros' in applicable:
        for days in DAYS_GRID:
            candidates.append(_candidate(
                'adelantar_cobros',
                days=int(days),
                agreement_type='presion_comercial',
            ))
        for button in discount_buttons(15):
            candidates.append(_candidate(
                'adelantar_cobros',
                days=15,
                haircut=float(button['pct']),
                tasa_descuento=float(button['pct']),
                agreement_type='descuento_pronto_pago',
            ))

    if 'recortar_opex' in applicable:
        for pct in OPEX_GRID:
            candidates.append(_candidate('recortar_opex', pct=float(pct)))

    if 'refinanciar' in applicable:
        for pct in REFI_GRID:
            candidates.append(_candidate('refinanciar', pct=float(pct)))
    else:
        for facade in ('renegociar_interes', 'leasing_a_cuota_menor'):
            if facade in applicable:
                candidates.append(_candidate(facade, pct=0.20))

    if 'ampliar_dpo' in applicable:
        candidates.append(_candidate(
            'ampliar_dpo',
            days=15,
            pct=0.20,
            agreement_type='acuerdo_negociado',
            proposed_cost_pct=_tipico_dpo_cost(15),
        ))

    if 'usar_confirming' in applicable:
        candidates.append(_candidate('usar_confirming', pct=0.20))

    for lever_id in _ONE_SHOT:
        if lever_id not in applicable:
            continue
        if lever_id == 'ofrecer_pronto_pago_proveedor':
            candidates.append(_candidate(
                lever_id,
                pct=0.20,
                agreement_type='acuerdo_negociado',
                proposed_cost_pct=0.02,
            ))
        elif lever_id == 'bajar_utilizacion_linea':
            candidates.append(_candidate(lever_id, pct=0.20))
        elif lever_id == 'bajar_devoluciones':
            candidates.append(_candidate(lever_id, pct=0.50))
        else:
            candidates.append(_candidate(lever_id))

    return candidates[:SEARCH_BUDGET]


def _cost_pct(row: dict[str, Any]) -> float:
    haircut = row.get('haircut') or row.get('tasa_descuento')
    if haircut:
        return float(haircut)
    return 0.0


def _row_from_sim(candidate: dict[str, Any], sim: dict[str, Any]) -> dict[str, Any]:
    lever_id = candidate['id']
    familia = family_of(lever_id)
    delta = sim.get('delta_score')
    if familia == 'circulante':
        delta = None
    return {
        'id': lever_id,
        'familia': familia,
        'delta_score': delta,
        'caja_liberada_eur': sim.get('caja_liberada_eur'),
        'eur_año': sim.get('eur_año'),
        'days': candidate.get('days'),
        'pct': candidate.get('pct'),
        'haircut': candidate.get('haircut') or candidate.get('tasa_descuento'),
        'tasa_descuento': candidate.get('tasa_descuento') or candidate.get('haircut'),
        'agreement_type': candidate.get('agreement_type'),
        'warnings': list(sim.get('warnings') or []),
        'label': _label(candidate),
    }


def recommend_levers(company_id: str) -> dict[str, Any]:
    try:
        catalog = evaluate_catalog(company_id)
    except KeyError:
        return {'ok': False, 'error': 'empresa_no_encontrada', 'company_id': company_id}

    applicable = {row['id'] for row in catalog if row.get('es_aplicable')}
    candidates = _build_candidates(applicable)

    salud_rows: list[dict[str, Any]] = []
    circulante_rows: list[dict[str, Any]] = []
    model_version: str | None = None
    n_sims = 0

    for candidate in candidates:
        sim = simulate_levers(company_id, [_sim_payload(candidate)])
        n_sims += 1
        if not sim.get('ok'):
            continue
        if model_version is None:
            model_version = sim.get('model_version')
        row = _row_from_sim(candidate, sim)
        if row['familia'] == 'salud' and row['delta_score'] is not None:
            salud_rows.append(row)
        elif row['familia'] == 'circulante':
            circulante_rows.append(row)

    sugerencias = sorted(
        salud_rows,
        key=lambda row: float(row['delta_score']),
        reverse=True,
    )[:RANK_TOP_N]
    opciones_circulante = sorted(
        circulante_rows,
        key=lambda row: float(row.get('caja_liberada_eur') or 0.0),
        reverse=True,
    )[:RANK_TOP_N]

    recomendado = None
    if sugerencias:
        recomendado = max(
            sugerencias,
            key=lambda row: float(row['delta_score']) / max(_cost_pct(row), 0.001),
        )

    return {
        'ok': True,
        'company_id': company_id,
        'as_of': AS_OF,
        'modo': MODO,
        'model_version': model_version or load_model_version(),
        'n_sims': n_sims,
        'sugerencias': sugerencias,
        'opciones_circulante': opciones_circulante,
        'recomendado': recomendado,
    }
