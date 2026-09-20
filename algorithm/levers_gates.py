"""Applicability gates (filtro A). No scoring, no HTTP."""

from __future__ import annotations

from typing import Any

from algorithm.levers_catalog import (
    D_REFINANCE_CEILING,
    H_MATERIAL_EUR,
    LEVER_CATALOG,
    OPEX_MIN_EUR,
    PUBLIC_LEVER_IDS,
    REFUND_MIN_EUR,
    canonical_lever_id,
    family_of,
)
from algorithm.levers_objects import CompanyObjects, get_company_objects

# debt_points = 20 * D  (w_d = 0.2). D >= 0.49 → points >= 9.8
_DEBT_POINTS_CEILING = 20.0 * D_REFINANCE_CEILING


def _resolve(company: str | CompanyObjects) -> CompanyObjects:
    if isinstance(company, CompanyObjects):
        return company
    return get_company_objects(str(company))


def is_applicable(company: str | CompanyObjects, lever_id: str) -> tuple[bool, str | None]:
    obj = _resolve(company)
    lid = canonical_lever_id(lever_id)
    if obj.is_prior:
        return False, 'sin_evidencia_score'

    if lid == 'adelantar_cobros':
        if obj.ar_pending_eur <= 0:
            return False, 'sin_ar_pendiente'
        return True, None

    if lid == 'recortar_opex':
        if obj.opex_m23 < OPEX_MIN_EUR:
            return False, 'sin_opex'
        return True, None

    if lid == 'refinanciar':
        if obj.debt_service_m23 < H_MATERIAL_EUR:
            return False, 'sin_debt_service'
        if obj.debt_points >= _DEBT_POINTS_CEILING:
            return False, 'techo_d'
        return True, None

    if lid == 'renegociar_interes':
        if obj.debt_service_m23 < H_MATERIAL_EUR:
            return False, 'sin_interes'
        if obj.debt_points >= _DEBT_POINTS_CEILING:
            return False, 'techo_d'
        return True, None

    if lid == 'leasing_a_cuota_menor':
        if not (obj.has_leasing or obj.has_renting):
            return False, 'sin_leasing'
        if obj.debt_service_m23 < H_MATERIAL_EUR:
            return False, 'sin_debt_service'
        if obj.debt_points >= _DEBT_POINTS_CEILING:
            return False, 'techo_d'
        return True, None

    if lid == 'ampliar_dpo':
        if obj.ap_pending_eur <= 0 and obj.ap_expenses_m23 <= 0:
            return False, 'sin_ap'
        return True, None

    if lid == 'ofrecer_pronto_pago_proveedor':
        if obj.ap_pending_eur <= 0 and obj.ap_expenses_m23 <= 0:
            return False, 'sin_ap'
        return True, None

    if lid == 'usar_confirming':
        if not obj.has_confirming:
            return False, 'sin_confirming'
        if obj.ap_pending_eur <= 0 and obj.ap_expenses_m23 <= 0:
            return False, 'sin_ap'
        return True, None

    if lid == 'bajar_utilizacion_linea':
        if not obj.has_lineofcredit:
            return False, 'sin_linea'
        if obj.loc_outstanding <= 0:
            return False, 'sin_dispuesto'
        return True, None

    if lid == 'amortizar_linea_con_caja':
        if not obj.has_lineofcredit:
            return False, 'sin_linea'
        if obj.loc_outstanding <= 0:
            return False, 'sin_dispuesto'
        return True, None

    if lid == 'disponer_linea':
        if not obj.has_lineofcredit:
            return False, 'sin_linea'
        if obj.loc_headroom <= 0:
            return False, 'sin_holgura_linea'
        return True, None

    if lid == 'vender_inversiones':
        if not obj.has_investment or obj.investment_balance <= 0:
            return False, 'sin_inversion'
        return True, None

    if lid == 'sustituir_factoring':
        if not obj.has_factoring:
            return False, 'sin_factoring'
        return True, None

    if lid == 'reducir_concentracion':
        if not obj.hhi_used or obj.n_ar_clients < 2:
            return False, 'sin_hhi_usable'
        return True, None

    if lid == 'bajar_devoluciones':
        if obj.refunds_m23 < REFUND_MIN_EUR:
            return False, 'sin_refunds'
        return True, None

    return False, 'palanca_desconocida'


def evaluate_catalog(company_id: str) -> list[dict[str, Any]]:
    obj = get_company_objects(company_id)
    rows: list[dict[str, Any]] = []
    for lever_id in PUBLIC_LEVER_IDS:
        meta = LEVER_CATALOG[lever_id]
        ok, reason = is_applicable(obj, lever_id)
        rows.append({
            'id': lever_id,
            'familia': family_of(lever_id),
            'mutator': meta['mutator'],
            'excluido_con': list(meta['excluido_con']),
            'es_aplicable': bool(ok),
            'motivo_rechazo': None if ok else reason,
            'needs_agreement': bool(meta['needs_agreement']),
            'agreement_types': list(meta['agreement_types']),
        })
    return rows
