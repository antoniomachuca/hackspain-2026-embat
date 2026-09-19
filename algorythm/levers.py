"""Lever domain: mutate last month, rescore. HTTP/Telegram call this — they do not reimplement it."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np

from algorythm.bank_panels import SCORE_FIELDS, clone_bank_slice, get_company_bank_slice
from algorythm.levers_catalog import (
    AS_OF,
    LEVER_CATALOG,
    MUTEX_GROUPS,
    TIPO_REF_ANUAL,
    canonical_lever_id,
)
from algorythm.levers_cost import impacto_anual_eur, validate_agreement
from algorythm.levers_gates import is_applicable
from algorythm.levers_lines import (
    check_resource_overlap,
    line_tasa,
    lines_have_targets,
    normalize_lineas,
    resolve_ap_line,
    resolve_ar_line,
    uses_amount_shortcut,
)
from algorythm.levers_objects import get_company_objects, select_ar_advance
from algorythm.score_engine import ScoreConfig, calculate_scores
from algorythm.score_states import StateConfig, classify_states

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / 'engine_results' / 'score_manifest.json'
LAST_MONTH = -1

STANDARD_WARNINGS = (
    'retrospectivo_un_mes',
    'momentum_no_activado',
    'caja_es_circulante_no_beneficio',
    'curva_score_tipo_retirada',
)


def load_model_version(manifest_path: Path | None = None) -> str:
    path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    with path.open(encoding='utf-8') as source:
        return str(json.load(source)['model_version'])


def _endpoint(scores: dict[str, np.ndarray]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, arr in scores.items():
        value = arr[0, LAST_MONTH]
        if isinstance(value, (np.floating, float)):
            out[key] = float(value)
        elif isinstance(value, (np.integer, int)):
            out[key] = int(value)
        elif isinstance(value, (np.bool_, bool)):
            out[key] = bool(value)
        else:
            out[key] = value.item() if hasattr(value, 'item') else value
    return out


def score_bank_slice(bank: dict[str, np.ndarray], config: ScoreConfig | None = None,
                     state_config: StateConfig | None = None) -> dict[str, np.ndarray]:
    payload = {k: bank[k] for k in SCORE_FIELDS if k in bank}
    output = calculate_scores(payload, erp=None, config=config or ScoreConfig())
    output.update(classify_states(output, state_config or StateConfig()))
    return output


def mutate_cobros(bank: dict[str, np.ndarray], amount_eur: float, haircut: float = 0.0) -> float:
    net = max(0.0, float(amount_eur) * (1.0 - max(0.0, min(1.0, haircut))))
    if net <= 0:
        return 0.0
    m = LAST_MONTH
    bank['receipts'][:, m] += net
    bank['gross_receipts'][:, m] += net
    gap = bank['funding_gap'][:, m]
    bank['funding_gap'][:, m] = np.where(np.isfinite(gap), np.maximum(gap - net, 0.0), gap)
    return net


def mutate_opex(bank: dict[str, np.ndarray], pct: float) -> float:
    pct = max(0.0, min(1.0, float(pct)))
    m = LAST_MONTH
    opex = float(np.nan_to_num(bank.get('expenses_opex', np.zeros_like(bank['expenses']))[0, m]))
    save = opex * pct
    if save <= 0:
        return 0.0
    bank['expenses'][:, m] = np.maximum(bank['expenses'][:, m] - save, 0.0)
    if 'expenses_opex' in bank:
        bank['expenses_opex'][:, m] = np.maximum(bank['expenses_opex'][:, m] - save, 0.0)
    return save


def mutate_dpo(bank: dict[str, np.ndarray], pct: float | None = None,
               amount_eur: float | None = None) -> float:
    m = LAST_MONTH
    ap = float(np.nan_to_num(bank.get('expenses_ap', np.zeros_like(bank['expenses']))[0, m]))
    if amount_eur is not None:
        defer = min(max(0.0, float(amount_eur)), ap)
    else:
        pct = max(0.0, min(1.0, float(pct or 0.0)))
        defer = ap * pct
    if defer <= 0:
        return 0.0
    bank['expenses'][:, m] = np.maximum(bank['expenses'][:, m] - defer, 0.0)
    if 'expenses_ap' in bank:
        bank['expenses_ap'][:, m] = np.maximum(bank['expenses_ap'][:, m] - defer, 0.0)
    return defer


def mutate_early_ap(bank: dict[str, np.ndarray], pct: float | None = None,
                    discount: float = 0.0, amount_eur: float | None = None) -> float:
    """Pay AP now: expenses rise by net amount (1-discount). Inverse of DPO."""
    discount = max(0.0, min(1.0, float(discount)))
    m = LAST_MONTH
    ap = float(np.nan_to_num(bank.get('expenses_ap', np.zeros_like(bank['expenses']))[0, m]))
    if amount_eur is not None:
        extra = max(0.0, float(amount_eur)) * (1.0 - discount)
    else:
        pct = max(0.0, min(1.0, float(pct or 0.0)))
        extra = ap * pct * (1.0 - discount)
    if extra <= 0:
        return 0.0
    bank['expenses'][:, m] = bank['expenses'][:, m] + extra
    if 'expenses_ap' in bank:
        bank['expenses_ap'][:, m] = bank['expenses_ap'][:, m] + extra
    return extra


def mutate_refi(bank: dict[str, np.ndarray], pct: float) -> float:
    pct = max(0.0, min(1.0, float(pct)))
    m = LAST_MONTH
    h = float(np.nan_to_num(bank['debt_service'][0, m]))
    cut = h * pct
    if cut <= 0:
        return 0.0
    bank['debt_service'][:, m] = np.maximum(bank['debt_service'][:, m] - cut, 0.0)
    return cut


def mutate_refunds(bank: dict[str, np.ndarray], pct: float) -> float:
    pct = max(0.0, min(1.0, float(pct)))
    m = LAST_MONTH
    r = float(np.nan_to_num(bank['refunds'][0, m]))
    cut = r * pct
    if cut <= 0:
        return 0.0
    bank['refunds'][:, m] = np.maximum(bank['refunds'][:, m] - cut, 0.0)
    return cut


def check_mutex(lever_ids: list[str]) -> str | None:
    chosen = {canonical_lever_id(i) for i in lever_ids}
    for group in MUTEX_GROUPS:
        hit = chosen & group
        if len(hit) > 1:
            return f"mutuamente_excluyentes: {sorted(hit)}"
    return None


def _cobros_amount(params: dict[str, Any], obj) -> tuple[float, float]:
    haircut = line_tasa(params)
    if 'amount_eur' in params or 'euros' in params:
        amount = float(params.get('amount_eur') or params.get('euros') or 0.0)
        return amount, haircut
    days = int(params.get('days') or params.get('dias') or 15)
    picked = select_ar_advance(
        obj, days=days, clients=params.get('clientes'), facturas=params.get('facturas'),
    )
    return picked.amount_eur, haircut


def _apply_cobros_lines(bank: dict[str, np.ndarray], params: dict[str, Any], obj,
                        original_id: str) -> tuple[float, bool]:
    lines = normalize_lineas(params)
    default_tasa = 0.02 if original_id == 'descuento_pronto_pago' else 0.0
    if uses_amount_shortcut(params):
        amount, haircut = _cobros_amount(params, obj)
        if haircut <= 0:
            haircut = default_tasa
        return mutate_cobros(bank, amount, haircut), haircut > 0

    euros = 0.0
    any_haircut = False
    for line in lines:
        picked, _missing = resolve_ar_line(obj, line)
        tasa = line_tasa(line, default=default_tasa)
        if tasa <= 0:
            tasa = default_tasa
        if tasa > 0:
            any_haircut = True
        euros += mutate_cobros(bank, picked.amount_eur, tasa)
    return euros, any_haircut


def _apply_ap_lines(params: dict[str, Any], obj) -> float | None:
    lines = normalize_lineas(params)
    if not lines_have_targets(lines):
        return None
    total = 0.0
    for line in lines:
        picked, _missing = resolve_ap_line(obj, line)
        total += picked.amount_eur
    return total


def apply_lever(bank: dict[str, np.ndarray], lever_id: str, params: dict[str, Any],
                obj=None) -> dict[str, Any]:
    original_id = lever_id
    lid = canonical_lever_id(lever_id)
    meta = LEVER_CATALOG[lid]
    mutator = meta['mutator']
    euros = 0.0
    delta_score_allowed = meta['family'] == 'salud'
    eur_year = None
    warnings = list(STANDARD_WARNINGS)

    if mutator == 'ar_a_receipts':
        euros, discounted = _apply_cobros_lines(bank, params, obj, original_id)
        if discounted:
            warnings.append('descuento_supuesto')
        delta_score_allowed = True
    elif mutator == 'opex_whitelist':
        pct = float(params.get('pct', params.get('opex_pct', 0.05)))
        euros = mutate_opex(bank, pct)
        eur_year = impacto_anual_eur(euros)
        warnings.append('extrapolacion_lineal_12m')
        delta_score_allowed = True
    elif mutator == 'bajar_h_recurrente':
        pct = float(params.get('pct', params.get('refi_pct', 0.20)))
        euros = mutate_refi(bank, pct)
        eur_year = impacto_anual_eur(euros)
        warnings.append('oferta_refinanciacion_supuesta')
        delta_score_allowed = True
    elif mutator == 'retrasar_ap':
        targeted = _apply_ap_lines(params, obj) if obj is not None else None
        if targeted is not None:
            bruto = mutate_dpo(bank, amount_eur=targeted)
        else:
            pct = float(params.get('pct', params.get('dpo_pct', 0.20)))
            bruto = mutate_dpo(bank, pct=pct)
        cost = float(params.get('proposed_cost_pct') or params.get('haircut') or 0.0)
        if targeted is not None:
            lines = normalize_lineas(params)
            cost = float(params.get('proposed_cost_pct') or max((line_tasa(line) for line in lines), default=0.0))
        euros = max(0.0, bruto * (1.0 - cost))
        delta_score_allowed = True  # engine will move L; ranking must null it
        warnings.append('circulante_no_salud')
    elif mutator == 'adelantar_ap':
        discount = float(params.get('proposed_cost_pct') or params.get('haircut') or 0.02)
        targeted = _apply_ap_lines(params, obj) if obj is not None else None
        if targeted is not None:
            lines = normalize_lineas(params)
            discount = float(params.get('proposed_cost_pct') or max((line_tasa(line) for line in lines), default=discount))
            paid = mutate_early_ap(bank, discount=discount, amount_eur=targeted)
        else:
            pct = float(params.get('pct', 0.20))
            paid = mutate_early_ap(bank, pct=pct, discount=discount)
        euros = paid * discount / max(1.0 - discount, 1e-9) if discount < 1 else 0.0
        warnings.append('pronto_pago_proveedor_adelanta_caja')
        delta_score_allowed = True
    elif mutator == 'confirming_fee':
        if params.get('cut_expenses'):
            raise ValueError('confirming_no_puede_bajar_expenses')
        pct = float(params.get('pct', 0.20))
        base = 0.0
        targeted = _apply_ap_lines(params, obj) if obj is not None else None
        if targeted is not None:
            base = targeted
        elif obj is not None:
            base = max(float(obj.ap_pending_eur), float(obj.ap_expenses_m23))
        euros = max(0.0, base * pct)
        delta_score_allowed = False
        warnings.append('confirming_no_toca_expenses')
        warnings.append('delta_score_null_caja_off')
    elif mutator == 'caja_linea':
        if obj is None:
            euros = float(params.get('amount_eur') or params.get('euros') or 0.0)
        elif lid == 'disponer_linea':
            euros = float(params.get('amount_eur') or params.get('euros') or obj.loc_headroom)
        elif lid == 'amortizar_linea_con_caja':
            cap = min(obj.checking_balance, obj.loc_outstanding) if obj.checking_balance > 0 else obj.loc_outstanding
            euros = float(params.get('amount_eur') or params.get('euros') or cap)
        else:
            pct = float(params.get('pct', 0.20))
            euros = float(params.get('amount_eur') or params.get('euros') or obj.loc_outstanding * pct)
        couple = params.get('couple_interest_pct')
        if lid == 'amortizar_linea_con_caja' and couple:
            mutate_refi(bank, float(couple))
            delta_score_allowed = True
            warnings.append('interes_acoplado_supuesto')
        else:
            delta_score_allowed = False
            warnings.append('delta_score_null_caja_off')
        eur_year = impacto_anual_eur(euros * (TIPO_REF_ANUAL / 12.0))
    elif mutator == 'liquidar_investment':
        euros = float(params.get('amount_eur') or params.get('euros') or (obj.investment_balance if obj else 0.0))
        delta_score_allowed = False
        warnings.append('delta_score_null_caja_off')
    elif mutator == 'factoring_a_linea':
        euros = float(params.get('amount_eur') or params.get('euros') or (obj.factoring_outstanding if obj else 0.0))
        delta_score_allowed = False
        warnings.append('factoring_coste_visible_sin_deshinchar_receipts')
        warnings.append('delta_score_null_caja_off')
    elif mutator == 'mix_receipts':
        euros = 0.0
        delta_score_allowed = False
        warnings.append('no_mutar_float_hhi')
    elif mutator == 'bajar_refunds':
        pct = float(params.get('pct', 0.50))
        euros = mutate_refunds(bank, pct)
        delta_score_allowed = True
    else:
        raise KeyError(f'unhandled mutator: {mutator}')

    return {
        'lever_id': lid,
        'family': meta['family'],
        'mutator': mutator,
        'euros': float(euros),
        'eur_año': None if eur_year is None else float(eur_year),
        'delta_score_allowed': bool(delta_score_allowed),
        'agreement_type': params.get('agreement_type'),
        'proposed_cost_pct': params.get('proposed_cost_pct'),
        'warnings': warnings,
    }


def _snapshot(endpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        'score': endpoint['score'],
        'state': endpoint.get('state'),
        'liquidity_points': endpoint.get('liquidity_points'),
        'collections_points': endpoint.get('collections_points'),
        'debt_points': endpoint.get('debt_points'),
        'momentum_points': endpoint.get('momentum_points'),
        'is_prior': bool(endpoint.get('is_prior')),
    }


def simulate_levers(
    company_id: str,
    levers: list[dict[str, Any]],
    *,
    config: ScoreConfig | None = None,
    state_config: StateConfig | None = None,
    manifest_path: Path | None = None,
    enforce_gates: bool = True,
) -> dict[str, Any]:
    ids = [str(item['id']) for item in levers]
    mutex = check_mutex(ids)
    if mutex:
        return {'ok': False, 'error': mutex, 'company_id': company_id}

    try:
        obj = get_company_objects(company_id)
    except KeyError:
        return {'ok': False, 'error': 'empresa_no_encontrada', 'company_id': company_id}

    overlap = check_resource_overlap(obj, levers)
    if overlap:
        return {'ok': False, 'company_id': company_id, **overlap}

    if enforce_gates:
        for item in levers:
            lid = str(item['id'])
            ok, reason = is_applicable(obj, lid)
            if not ok:
                return {
                    'ok': False,
                    'error': 'inaplicable',
                    'motivo_rechazo': reason,
                    'lever_id': canonical_lever_id(lid),
                    'company_id': company_id,
                }
            agr_ok, agr_reason = validate_agreement(lid, item.get('agreement_type'), params=item)
            if not agr_ok:
                return {
                    'ok': False,
                    'error': agr_reason,
                    'lever_id': canonical_lever_id(lid),
                    'company_id': company_id,
                }

    baseline_bank = get_company_bank_slice(company_id)
    baseline_scores = score_bank_slice(baseline_bank, config, state_config)
    baseline = _endpoint(baseline_scores)

    if baseline.get('is_prior'):
        return {
            'ok': False,
            'error': 'sin_evidencia_score',
            'company_id': company_id,
            'baseline': _snapshot(baseline),
            'model_version': load_model_version(manifest_path),
        }

    mutated = clone_bank_slice(baseline_bank)
    expenses_before = float(mutated['expenses'][0, LAST_MONTH])
    effects = []
    total_euros = 0.0
    all_warnings: list[str] = []
    eur_year_total = 0.0
    for item in levers:
        effect = apply_lever(mutated, str(item['id']), item, obj=obj)
        effects.append(effect)
        total_euros += float(effect['euros'])
        if effect.get('eur_año'):
            eur_year_total += float(effect['eur_año'])
        all_warnings.extend(effect.get('warnings') or [])

    expenses_after = float(mutated['expenses'][0, LAST_MONTH])
    for effect in effects:
        if effect['mutator'] == 'confirming_fee' and expenses_after < expenses_before - 1e-6:
            return {
                'ok': False,
                'error': 'confirming_bajo_expenses',
                'company_id': company_id,
            }

    projected_scores = score_bank_slice(mutated, config, state_config)
    projected = _endpoint(projected_scores)

    engine_delta = float(projected['score'] - baseline['score'])
    salud_scored = any(e['family'] == 'salud' and e['delta_score_allowed'] for e in effects)
    delta_score = engine_delta if salud_scored else None

    unique_warnings = list(dict.fromkeys(all_warnings))

    return {
        'ok': True,
        'company_id': company_id,
        'as_of': AS_OF,
        'modo': 'contrafactual_de_corte',
        'month_mutated': 23,
        'model_version': load_model_version(manifest_path),
        'baseline': _snapshot(baseline),
        'projected': _snapshot(projected),
        'delta_score': delta_score,
        'efecto_score_informativo': engine_delta,
        'prohibido_ordenar_por_delta': delta_score is None,
        'caja_liberada_eur': total_euros,
        'eur_año': eur_year_total if eur_year_total else None,
        'delta_bps': None,
        'effects': effects,
        'levers': deepcopy(levers),
        'warnings': unique_warnings,
        'assumptions': {
            'mapear_a_receipts': any(e['mutator'] == 'ar_a_receipts' for e in effects),
            'no_reescribe_prefijo': True,
            'erp_off': True,
            'cash_known': 0,
        },
    }
