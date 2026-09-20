"""Lever lines + resource_key overlap. No HTTP.

A cobros/AP lever is a list of lines, each targeting facturas XOR clientes
(or proveedores on AP). 422 only when two lines share an invoice resource_key.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from algorithm.levers_catalog import LEVER_CATALOG, canonical_lever_id
from algorithm.levers_objects import ArPick, CompanyObjects, invoice_resource_key, select_ap_advance, select_ar_advance

_TARGET_KEYS = ('facturas', 'clientes', 'proveedores')
_LINE_COPY_KEYS = (
    'facturas', 'clientes', 'proveedores', 'dias', 'days',
    'tasa_descuento', 'tasa', 'haircut', 'descuento_pct', 'proposed_cost_pct',
)
_AMOUNT_KEYS = ('amount_eur', 'euros')
_AR_MUTATORS = frozenset({'ar_a_receipts'})
_AP_MUTATORS = frozenset({'retrasar_ap', 'adelantar_ap', 'confirming_fee'})
_POOLED_KEYS = {
    'opex_whitelist': 'opex',
    'bajar_h_recurrente': 'debt_service',
    'caja_linea': 'lineofcredit',
    'liquidar_investment': 'investment',
    'factoring_a_linea': 'factoring',
    'mix_receipts': 'hhi',
    'bajar_refunds': 'refunds',
}


def line_days(line: dict[str, Any], default: int = 15) -> int:
    return int(line.get('dias') or line.get('days') or default)


def line_tasa(line: dict[str, Any], default: float = 0.0) -> float:
    for key in ('tasa_descuento', 'tasa', 'haircut', 'descuento_pct'):
        if line.get(key) is not None:
            return float(line[key])
    return float(default)


def line_targets_error(line: dict[str, Any]) -> str | None:
    present = [key for key in _TARGET_KEYS if line.get(key)]
    if len(present) > 1:
        return 'linea_facturas_o_clientes'
    return None


def lines_have_targets(lines: Sequence[dict[str, Any]]) -> bool:
    return any(line.get(key) for line in lines for key in _TARGET_KEYS)


def uses_amount_shortcut(params: dict[str, Any]) -> bool:
    if params.get('lineas'):
        return False
    if any(params.get(key) for key in _TARGET_KEYS):
        return False
    return any(key in params and params[key] is not None for key in _AMOUNT_KEYS)


def normalize_lineas(params: dict[str, Any]) -> list[dict[str, Any]]:
    raw = params.get('lineas')
    if raw:
        return [dict(line) for line in raw]
    line = {key: params[key] for key in _LINE_COPY_KEYS if key in params and params[key] is not None}
    for key in _AMOUNT_KEYS:
        if key in params and params[key] is not None:
            line[key] = params[key]
    return [line]


def max_tasa(params: dict[str, Any]) -> float:
    return max((line_tasa(line) for line in normalize_lineas(params)), default=0.0)


def _unknown_facturas(invoices: Sequence[dict[str, Any]], facturas: Iterable[str]) -> tuple[str, ...]:
    known = {str(inv.get('invoice_id') or '') for inv in invoices}
    known.discard('')
    return tuple(fid for fid in facturas if str(fid) not in known)


def resolve_ar_line(obj: CompanyObjects, line: dict[str, Any]) -> tuple[ArPick, tuple[str, ...]]:
    facturas = line.get('facturas')
    if facturas:
        missing = _unknown_facturas(obj.ar_invoices, facturas)
        if missing:
            return ArPick(days=line_days(line), amount_eur=0.0, n_invoices=0), missing
    picked = select_ar_advance(
        obj,
        days=line_days(line),
        clients=line.get('clientes'),
        facturas=facturas,
    )
    return picked, ()


def resolve_ap_line(obj: CompanyObjects, line: dict[str, Any]) -> tuple[ArPick, tuple[str, ...]]:
    facturas = line.get('facturas')
    proveedores = line.get('proveedores') or line.get('clientes')
    if facturas:
        missing = _unknown_facturas(obj.ap_invoices, facturas)
        if missing:
            return ArPick(days=line_days(line), amount_eur=0.0, n_invoices=0), missing
    picked = select_ap_advance(
        obj,
        days=line_days(line),
        proveedores=proveedores,
        facturas=facturas,
    )
    return picked, ()


def _pool_keys(invoices: Sequence[dict[str, Any]], sentinel: str) -> set[str]:
    if invoices:
        return {invoice_resource_key(inv) for inv in invoices}
    return {sentinel}


def _line_invoice_keys(
    obj: CompanyObjects,
    line: dict[str, Any],
    *,
    is_ar: bool,
    amount_shortcut: bool,
) -> tuple[set[str], str | None, str | None]:
    error = line_targets_error(line)
    if error:
        return set(), error, None
    if is_ar and line.get('proveedores'):
        return set(), 'linea_facturas_o_clientes', None

    invoices = obj.ar_invoices if is_ar else obj.ap_invoices
    sentinel = 'ar_pending' if is_ar else 'ap_pending'
    targeted = any(line.get(key) for key in _TARGET_KEYS)
    if amount_shortcut or not targeted:
        return _pool_keys(invoices, sentinel), None, None

    picked, missing = (resolve_ar_line if is_ar else resolve_ap_line)(obj, line)
    if missing:
        return set(), 'factura_desconocida', missing[0]
    if picked.resource_keys:
        return set(picked.resource_keys), None, None
    if picked.invoice_ids:
        wanted = set(picked.invoice_ids)
        return {
            invoice_resource_key(inv)
            for inv in invoices
            if str(inv.get('invoice_id') or '') in wanted
        }, None, None
    return set(), None, None


def check_resource_overlap(
    obj: CompanyObjects,
    levers: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    claimed: dict[str, str] = {}
    for index, item in enumerate(levers):
        lid_raw = str(item.get('id') or item.get('lever_id') or '')
        lid = canonical_lever_id(lid_raw)
        mutator = str(LEVER_CATALOG[lid]['mutator'])
        if mutator in _AR_MUTATORS or mutator in _AP_MUTATORS:
            amount_shortcut = uses_amount_shortcut(item)
            for line_idx, line in enumerate(normalize_lineas(item)):
                keys, error, resource_key = _line_invoice_keys(
                    obj, line, is_ar=mutator in _AR_MUTATORS, amount_shortcut=amount_shortcut,
                )
                if error:
                    payload: dict[str, Any] = {
                        'error': error,
                        'lever_id': lid,
                    }
                    if resource_key:
                        payload['resource_key'] = resource_key
                    return payload
                conflict = _claim(claimed, keys, f'{lid}:{index}:{line_idx}')
                if conflict:
                    return conflict
            continue
        pooled = _POOLED_KEYS.get(mutator, lid)
        conflict = _claim(claimed, {pooled}, f'{lid}:{index}')
        if conflict:
            return conflict
    return None


def _claim(claimed: dict[str, str], keys: set[str], owner: str) -> dict[str, Any] | None:
    for key in keys:
        if key in claimed:
            return {
                'error': 'doble_conteo',
                'resource_key': key,
                'lever_id': owner.split(':', 1)[0],
            }
        claimed[key] = owner
    return None
