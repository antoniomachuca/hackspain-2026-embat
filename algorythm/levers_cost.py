"""D2C/D3C proposed cost numbers. No HTTP, no I/O."""

from __future__ import annotations

from typing import Any

from algorythm.levers_catalog import (
    AGREEMENT_COBROS,
    AGREEMENT_DPO,
    DISCOUNT_ANCHORS,
    DPO_COST_ANCHORS,
    LEVER_CATALOG,
    TIPO_REF_ANUAL,
    canonical_lever_id,
)

_MAX_HAIRCUT = 0.03
_DISCOUNT_NAMES = ('minimo', 'tipico', 'agresivo')
_DPO_ANCHOR_NAMES = ('recargo', 'tipico')


def floor_pct(days: int) -> float:
    return TIPO_REF_ANUAL * days / 365


def discount_buttons(days: int) -> list[dict[str, Any]]:
    minimo = max(floor_pct(days), DISCOUNT_ANCHORS[0])
    pcts = (minimo, DISCOUNT_ANCHORS[1], DISCOUNT_ANCHORS[2])
    buttons = [
        {'name': name, 'pct': pct}
        for name, pct in zip(_DISCOUNT_NAMES, pcts)
    ]
    return sorted(buttons, key=lambda button: button['pct'])


def dpo_cost_buttons(days: int) -> list[dict[str, Any]]:
    buttons: list[dict[str, Any]] = []
    floor = floor_pct(days)
    if 0 < floor <= _MAX_HAIRCUT:
        buttons.append({'name': 'minimo', 'pct': floor})
    for name, pct in zip(_DPO_ANCHOR_NAMES, DPO_COST_ANCHORS):
        if 0 < pct <= _MAX_HAIRCUT:
            buttons.append({'name': name, 'pct': pct})
    return sorted(buttons, key=lambda button: button['pct'])


def caja_neta(bruto: float, cost_pct: float) -> float:
    return max(0.0, bruto * (1.0 - cost_pct))


def impacto_anual_eur(delta_mensual: float) -> float:
    return 12.0 * delta_mensual


def validate_agreement(
    lever_id: str, agreement_type: str | None
) -> tuple[bool, str | None]:
    canonical = canonical_lever_id(lever_id)
    meta = LEVER_CATALOG[canonical]
    allowed = set(meta['agreement_types'])
    if canonical == 'adelantar_cobros':
        allowed = set(AGREEMENT_COBROS - {'descuento_pronto_pago'})
    elif canonical == 'descuento_pronto_pago':
        allowed = {'descuento_pronto_pago'}
    elif canonical == 'ampliar_dpo':
        allowed = set(AGREEMENT_DPO - {'confirming_en_su_lugar'})

    if not meta['needs_agreement']:
        return True, None
    if agreement_type is None:
        return False, 'missing_agreement_type'
    if agreement_type not in allowed:
        return False, 'invalid_agreement_type'
    return True, None
