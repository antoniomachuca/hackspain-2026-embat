"""Frozen lever catalog (D1A). No HTTP, no I/O.

Facades share mutators. Adding a lever = new catalog row, not a new engine.
"""

from __future__ import annotations

from typing import Any, FrozenSet

AS_OF = '2026-09-01'
MODO = 'contrafactual_de_corte'
TIPO_REF_ANUAL = 0.03
MAX_HAIRCUT = 0.03
DAYS_GRID = (7, 15, 30)
OPEX_GRID = (0.05, 0.10)
REFI_GRID = (0.20, 0.40)
DISCOUNT_ANCHORS = (0.005, 0.02, 0.03)
DPO_COST_ANCHORS = (0.01, 0.02)
SEARCH_BUDGET = 60
RANK_TOP_N = 10
OPEX_MIN_EUR = 500.0
REFUND_MIN_EUR = 500.0
H_MATERIAL_EUR = 100.0
D_REFINANCE_CEILING = 0.49  # D already ~0.5 → refinance is a no-op

AGREEMENT_COBROS = frozenset({
    'descuento_pronto_pago',
    'acuerdo_grupo',
    'presion_comercial',
    'contrato_ya_firmado',
})
AGREEMENT_DPO = frozenset({
    'perder_descuento_proveedor',
    'recargo_proveedor',
    'acuerdo_negociado',
    'confirming_en_su_lugar',
})

# mutator_id names match research §13.4
LEVER_CATALOG: dict[str, dict[str, Any]] = {
    'adelantar_cobros': {
        'family': 'salud',
        'mutator': 'ar_a_receipts',
        'agreement_types': tuple(AGREEMENT_COBROS - {'descuento_pronto_pago'}),
        'excluido_con': ('descuento_pronto_pago',),
        'alias_of': None,
        'needs_agreement': True,
    },
    'reducir_dso': {
        'family': 'salud',
        'mutator': 'ar_a_receipts',
        'agreement_types': tuple(AGREEMENT_COBROS - {'descuento_pronto_pago'}),
        'excluido_con': ('descuento_pronto_pago',),
        'alias_of': 'adelantar_cobros',
        'needs_agreement': True,
    },
    'descuento_pronto_pago': {
        'family': 'salud',
        'mutator': 'ar_a_receipts',
        'agreement_types': ('descuento_pronto_pago',),
        'excluido_con': ('adelantar_cobros', 'reducir_dso'),
        'alias_of': None,
        'needs_agreement': True,
    },
    'recortar_opex': {
        'family': 'salud',
        'mutator': 'opex_whitelist',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'refinanciar': {
        'family': 'salud',
        'mutator': 'bajar_h_recurrente',
        'agreement_types': (),
        'excluido_con': ('renegociar_interes', 'leasing_a_cuota_menor'),
        'alias_of': None,
        'needs_agreement': False,
    },
    'renegociar_interes': {
        'family': 'salud',
        'mutator': 'bajar_h_recurrente',
        'agreement_types': (),
        'excluido_con': ('refinanciar', 'leasing_a_cuota_menor'),
        'alias_of': None,
        'needs_agreement': False,
    },
    'leasing_a_cuota_menor': {
        'family': 'salud',
        'mutator': 'bajar_h_recurrente',
        'agreement_types': (),
        'excluido_con': ('refinanciar', 'renegociar_interes'),
        'alias_of': None,
        'needs_agreement': False,
    },
    'ampliar_dpo': {
        'family': 'circulante',
        'mutator': 'retrasar_ap',
        'agreement_types': tuple(AGREEMENT_DPO - {'confirming_en_su_lugar'}),
        'excluido_con': ('usar_confirming', 'ofrecer_pronto_pago_proveedor'),
        'alias_of': None,
        'needs_agreement': True,
    },
    'usar_confirming': {
        'family': 'circulante',
        'mutator': 'confirming_fee',
        'agreement_types': (),
        'excluido_con': ('ampliar_dpo', 'ofrecer_pronto_pago_proveedor'),
        'alias_of': None,
        'needs_agreement': False,
    },
    'ofrecer_pronto_pago_proveedor': {
        'family': 'circulante',
        'mutator': 'adelantar_ap',
        'agreement_types': tuple(AGREEMENT_DPO - {'confirming_en_su_lugar'}),
        'excluido_con': ('ampliar_dpo', 'usar_confirming'),
        'alias_of': None,
        'needs_agreement': True,
    },
    'bajar_utilizacion_linea': {
        'family': 'circulante',
        'mutator': 'caja_linea',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'amortizar_linea_con_caja': {
        'family': 'circulante',
        'mutator': 'caja_linea',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'disponer_linea': {
        'family': 'circulante',
        'mutator': 'caja_linea',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'vender_inversiones': {
        'family': 'circulante',
        'mutator': 'liquidar_investment',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'sustituir_factoring': {
        'family': 'salud',
        'mutator': 'factoring_a_linea',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'reducir_concentracion': {
        'family': 'salud',
        'mutator': 'mix_receipts',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
    'bajar_devoluciones': {
        'family': 'salud',
        'mutator': 'bajar_refunds',
        'agreement_types': (),
        'excluido_con': (),
        'alias_of': None,
        'needs_agreement': False,
    },
}

MUTEX_GROUPS: tuple[FrozenSet[str], ...] = (
    frozenset({'adelantar_cobros', 'reducir_dso', 'descuento_pronto_pago'}),
    frozenset({'refinanciar', 'renegociar_interes', 'leasing_a_cuota_menor'}),
    frozenset({'ampliar_dpo', 'usar_confirming', 'ofrecer_pronto_pago_proveedor'}),
)

PUBLIC_LEVER_IDS = tuple(k for k, v in LEVER_CATALOG.items() if not v.get('alias_of'))


def canonical_lever_id(lever_id: str) -> str:
    meta = LEVER_CATALOG.get(lever_id)
    if meta is None:
        raise KeyError(f'unknown lever_id: {lever_id}')
    return str(meta['alias_of'] or lever_id)


def family_of(lever_id: str) -> str:
    return str(LEVER_CATALOG[canonical_lever_id(lever_id)]['family'])
