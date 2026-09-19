"""Per-company objects for lever gates. Never parse transactions.csv per request."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from algorythm.bank_panels import load_bank_inputs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATASET = ROOT / 'dataset'
PANELS_PATH = HERE / 'engine_results' / 'score_panels.npz'
OBJECTS_PATH = HERE / 'engine_results' / 'lever_objects.npz'
INVOICES_PATH = HERE / 'engine_results' / 'pending_invoices.npz'
CUTOFF = date(2026, 9, 1)
LAST_MONTH = -1
PENDING_STATUSES = frozenset({'pending', 'overdue', 'payment_in_progress'})

_CACHE: dict[str, Any] | None = None
_INV_CACHE: dict[str, Any] | None = None


@dataclass(frozen=True)
class ArPick:
    days: int
    amount_eur: float
    n_invoices: int
    clients: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompanyObjects:
    company_id: str
    group_id: str
    is_prior: bool
    debt_points: float
    ar_pending_eur: float
    ap_pending_eur: float
    opex_m23: float
    ap_expenses_m23: float
    debt_service_m23: float
    refunds_m23: float
    receipts_m23: float
    hhi: float
    hhi_quality: float
    hhi_used: bool
    n_ar_clients: int
    has_lineofcredit: bool
    loc_outstanding: float
    loc_granted: float
    loc_headroom: float
    has_factoring: bool
    factoring_outstanding: float
    has_confirming: bool
    has_leasing: bool
    has_renting: bool
    has_investment: bool
    investment_balance: float
    checking_balance: float
    ar_invoices: tuple[dict[str, Any], ...] = field(default=(), repr=False)
    ap_invoices: tuple[dict[str, Any], ...] = field(default=(), repr=False)


def objects_path(path: Path | None = None) -> Path:
    return Path(path) if path else OBJECTS_PATH


def _invoices_sidecar(objects_file: Path) -> Path:
    if objects_file.resolve() == OBJECTS_PATH.resolve():
        return INVOICES_PATH
    return objects_file.parent / 'pending_invoices.npz'


def _f(value: Any) -> float:
    if value is None or value == '':
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _due_ord(value: str | None) -> int:
    if not value:
        return -1
    try:
        return date.fromisoformat(value[:10]).toordinal()
    except ValueError:
        return -1


def _money(arr: np.ndarray) -> np.ndarray:
    return np.maximum(np.nan_to_num(np.asarray(arr, dtype=np.float64), nan=0.0), 0.0)


def _clear_cache() -> None:
    global _CACHE, _INV_CACHE
    _CACHE = None
    _INV_CACHE = None


def _invoice_dict(pending: float, due_ord: int, counterparty: str) -> dict[str, Any]:
    due = date.fromordinal(int(due_ord)).isoformat() if int(due_ord) > 0 else ''
    return {
        'pending_amount': float(pending),
        'due_date': due,
        'counterparty_id': str(counterparty) if counterparty else '',
    }


def _pack_invoices(rows: list[tuple[int, float, int, str]], is_ar: bool):
    if not rows:
        empty_i = np.zeros(0, dtype=np.int32)
        empty_f = np.zeros(0, dtype=np.float64)
        empty_s = np.array([], dtype='<U1')
        empty_b = np.zeros(0, dtype=bool)
        return empty_i, empty_b, empty_f, empty_i, empty_s
    company_idx = np.fromiter((r[0] for r in rows), dtype=np.int32, count=len(rows))
    pending = np.fromiter((r[1] for r in rows), dtype=np.float64, count=len(rows))
    due_ord = np.fromiter((r[2] for r in rows), dtype=np.int32, count=len(rows))
    counterparties = np.array([r[3] for r in rows], dtype=object)
    order = np.argsort(company_idx, kind='mergesort')
    company_idx = company_idx[order]
    pending = pending[order]
    due_ord = due_ord[order]
    counterparties = np.array([str(counterparties[i]) for i in order])
    side = np.full(len(rows), is_ar, dtype=bool)
    return company_idx, side, pending, due_ord, counterparties


def _concat_invoices(ar_pack, ap_pack, n_companies: int):
    packs = [p for p in (ar_pack, ap_pack) if p[0].size]
    if not packs:
        inv_company_idx = np.zeros(0, dtype=np.int32)
        inv_is_ar = np.zeros(0, dtype=bool)
        inv_pending = np.zeros(0, dtype=np.float64)
        inv_due_ord = np.zeros(0, dtype=np.int32)
        inv_counterparty = np.array([], dtype='<U1')
    else:
        inv_company_idx = np.concatenate([p[0] for p in packs])
        inv_is_ar = np.concatenate([p[1] for p in packs])
        inv_pending = np.concatenate([p[2] for p in packs])
        inv_due_ord = np.concatenate([p[3] for p in packs])
        inv_counterparty = np.concatenate([p[4] for p in packs])
        order = np.argsort(inv_company_idx, kind='mergesort')
        inv_company_idx = inv_company_idx[order]
        inv_is_ar = inv_is_ar[order]
        inv_pending = inv_pending[order]
        inv_due_ord = inv_due_ord[order]
        inv_counterparty = inv_counterparty[order]

    counts = np.bincount(inv_company_idx, minlength=n_companies).astype(np.int32) if inv_company_idx.size else np.zeros(n_companies, dtype=np.int32)
    starts = np.zeros(n_companies, dtype=np.int32)
    if inv_company_idx.size:
        starts[1:] = np.cumsum(counts[:-1])
    return {
        'inv_company_idx': inv_company_idx.astype(np.int32, copy=False),
        'inv_is_ar': inv_is_ar,
        'inv_pending': inv_pending.astype(np.float64, copy=False),
        'inv_due_ord': inv_due_ord.astype(np.int32, copy=False),
        'inv_counterparty': np.asarray(inv_counterparty),
        'inv_start': starts,
        'inv_count': counts,
    }


def build_lever_objects(destination: Path | None = None) -> Path:
    """Scan invoices once, write npz cache, return path. Never call load_bank_panel."""
    target = objects_path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)

    bank = load_bank_inputs()
    if not PANELS_PATH.exists():
        raise FileNotFoundError(f'{PANELS_PATH} missing. Run calc_score first.')
    with np.load(PANELS_PATH, allow_pickle=False) as panels_file:
        panels = {k: panels_file[k] for k in ('company_id', 'group_id', 'is_prior', 'debt_points')}

    company_ids = np.asarray(panels['company_id'])
    n = int(company_ids.shape[0])
    idx_map = {str(cid): i for i, cid in enumerate(company_ids)}

    ar_pending = np.zeros(n, dtype=np.float64)
    ap_pending = np.zeros(n, dtype=np.float64)
    ar_clients: list[set[str]] = [set() for _ in range(n)]
    ar_rows: list[tuple[int, float, int, str]] = []
    ap_rows: list[tuple[int, float, int, str]] = []

    invoices_csv = DATASET / 'invoices.csv'
    with invoices_csv.open(newline='', encoding='utf-8') as source:
        for row in csv.DictReader(source):
            if row['status'] not in PENDING_STATUSES:
                continue
            i = idx_map.get(row['company_id'])
            if i is None:
                continue
            amount = _f(row['amount'])
            pending = _f(row['pending_amount'])
            due_ord = _due_ord(row.get('due_date'))
            counterparty = row.get('counterparty_id') or ''
            if amount > 0 and pending > 0:
                ar_pending[i] += pending
                if counterparty:
                    ar_clients[i].add(counterparty)
                ar_rows.append((i, pending, due_ord, counterparty))
            elif amount < 0 and pending != 0:
                ap_pending[i] += abs(pending)
                ap_rows.append((i, abs(pending), due_ord, counterparty))

    n_ar_clients = np.fromiter((len(s) for s in ar_clients), dtype=np.int32, count=n)

    has_lineofcredit = np.zeros(n, dtype=bool)
    loc_granted = np.zeros(n, dtype=np.float64)
    loc_outstanding = np.zeros(n, dtype=np.float64)
    has_factoring = np.zeros(n, dtype=bool)
    factoring_outstanding = np.zeros(n, dtype=np.float64)
    has_confirming = np.zeros(n, dtype=bool)
    has_leasing = np.zeros(n, dtype=bool)
    has_renting = np.zeros(n, dtype=bool)

    with (DATASET / 'debt_products.csv').open(newline='', encoding='utf-8') as source:
        for row in csv.DictReader(source):
            i = idx_map.get(row['company_id'])
            if i is None:
                continue
            kind = row['type']
            granted = abs(_f(row.get('granted')))
            outstanding = abs(_f(row.get('outstanding')))
            if kind == 'lineofcredit':
                has_lineofcredit[i] = True
                loc_granted[i] += granted
                loc_outstanding[i] += outstanding
            elif kind == 'factoring':
                has_factoring[i] = True
                factoring_outstanding[i] += outstanding
            elif kind == 'confirming':
                has_confirming[i] = True
            elif kind == 'leasing':
                has_leasing[i] = True
            elif kind == 'renting':
                has_renting[i] = True

    loc_headroom = np.maximum(loc_granted - loc_outstanding, 0.0)

    product_type: dict[str, tuple[int, str]] = {}
    has_investment = np.zeros(n, dtype=bool)
    with (DATASET / 'banking_products.csv').open(newline='', encoding='utf-8') as source:
        for row in csv.DictReader(source):
            i = idx_map.get(row['company_id'])
            if i is None:
                continue
            kind = row['type']
            product_type[row['product_id']] = (i, kind)
            if kind == 'investment':
                has_investment[i] = True

    investment_balance = np.zeros(n, dtype=np.float64)
    checking_balance = np.zeros(n, dtype=np.float64)
    with (DATASET / 'balances.csv').open(newline='', encoding='utf-8') as source:
        for row in csv.DictReader(source):
            info = product_type.get(row['product_id'])
            if info is None:
                continue
            i, kind = info
            balance = _f(row.get('balance'))
            if kind == 'investment':
                investment_balance[i] += balance
            elif kind == 'checking':
                checking_balance[i] += balance

    hhi = np.asarray(bank['hhi'][:, LAST_MONTH], dtype=np.float64)
    hhi_quality = np.asarray(bank['hhi_quality'][:, LAST_MONTH], dtype=np.float64)
    hhi_used = np.isfinite(hhi) & (hhi_quality > 0)

    inv = _concat_invoices(
        _pack_invoices(ar_rows, True),
        _pack_invoices(ap_rows, False),
        n,
    )

    payload: dict[str, Any] = {
        'company_id': company_ids,
        'group_id': np.asarray(panels['group_id']),
        'is_prior': np.asarray(panels['is_prior'][:, LAST_MONTH], dtype=bool),
        'debt_points': np.asarray(panels['debt_points'][:, LAST_MONTH], dtype=np.float64),
        'ar_pending_eur': ar_pending,
        'ap_pending_eur': ap_pending,
        'opex_m23': _money(bank['expenses_opex'][:, LAST_MONTH]),
        'ap_expenses_m23': _money(bank['expenses_ap'][:, LAST_MONTH]),
        'debt_service_m23': _money(bank['debt_service'][:, LAST_MONTH]),
        'refunds_m23': _money(bank['refunds'][:, LAST_MONTH]),
        'receipts_m23': _money(bank['receipts'][:, LAST_MONTH]),
        'hhi': hhi,
        'hhi_quality': hhi_quality,
        'hhi_used': hhi_used,
        'n_ar_clients': n_ar_clients,
        'has_lineofcredit': has_lineofcredit,
        'loc_outstanding': loc_outstanding,
        'loc_granted': loc_granted,
        'loc_headroom': loc_headroom,
        'has_factoring': has_factoring,
        'factoring_outstanding': factoring_outstanding,
        'has_confirming': has_confirming,
        'has_leasing': has_leasing,
        'has_renting': has_renting,
        'has_investment': has_investment,
        'investment_balance': investment_balance,
        'checking_balance': checking_balance,
        **inv,
    }
    np.savez_compressed(target, **payload)

    sidecar = _invoices_sidecar(target)
    np.savez_compressed(
        sidecar,
        company_idx=inv['inv_company_idx'],
        is_ar=inv['inv_is_ar'],
        pending_amount=inv['inv_pending'],
        due_ord=inv['inv_due_ord'],
        counterparty_id=inv['inv_counterparty'],
        inv_start=inv['inv_start'],
        inv_count=inv['inv_count'],
        company_id=company_ids,
    )
    _clear_cache()
    return target


def _hydrate(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        loaded = {k: data[k] for k in data.files}
    loaded['index'] = {str(cid): i for i, cid in enumerate(loaded['company_id'])}
    loaded['objects'] = {}
    return loaded


def _load(path: Path | None = None) -> dict[str, Any]:
    global _CACHE
    target = objects_path(path)
    if path is None and _CACHE is not None:
        return _CACHE
    if not target.exists():
        if path is None:
            build_lever_objects()
        else:
            raise FileNotFoundError(target)
        target = objects_path(None)
    loaded = _hydrate(target)
    if path is None:
        _CACHE = loaded
    return loaded


def _invoices_for(cache: dict[str, Any], i: int) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    start = int(cache['inv_start'][i])
    count = int(cache['inv_count'][i])
    if count <= 0:
        return (), ()
    end = start + count
    is_ar = cache['inv_is_ar'][start:end]
    pending = cache['inv_pending'][start:end]
    due_ord = cache['inv_due_ord'][start:end]
    counterparties = cache['inv_counterparty'][start:end]
    ar: list[dict[str, Any]] = []
    ap: list[dict[str, Any]] = []
    for k in range(count):
        item = _invoice_dict(float(pending[k]), int(due_ord[k]), str(counterparties[k]))
        if bool(is_ar[k]):
            ar.append(item)
        else:
            ap.append(item)
    return tuple(ar), tuple(ap)


def get_company_objects(company_id: str, path: Path | None = None) -> CompanyObjects:
    cid = company_id.strip().upper()
    cache = _load(path)
    memo = cache['objects']
    if cid in memo:
        return memo[cid]
    index = cache['index']
    if cid not in index:
        raise KeyError(f'company_id not in lever_objects: {cid}')
    i = index[cid]
    ar_invoices, ap_invoices = _invoices_for(cache, i)
    obj = CompanyObjects(
        company_id=str(cache['company_id'][i]),
        group_id=str(cache['group_id'][i]),
        is_prior=bool(cache['is_prior'][i]),
        debt_points=float(cache['debt_points'][i]),
        ar_pending_eur=float(cache['ar_pending_eur'][i]),
        ap_pending_eur=float(cache['ap_pending_eur'][i]),
        opex_m23=float(cache['opex_m23'][i]),
        ap_expenses_m23=float(cache['ap_expenses_m23'][i]),
        debt_service_m23=float(cache['debt_service_m23'][i]),
        refunds_m23=float(cache['refunds_m23'][i]),
        receipts_m23=float(cache['receipts_m23'][i]),
        hhi=float(cache['hhi'][i]),
        hhi_quality=float(cache['hhi_quality'][i]),
        hhi_used=bool(cache['hhi_used'][i]),
        n_ar_clients=int(cache['n_ar_clients'][i]),
        has_lineofcredit=bool(cache['has_lineofcredit'][i]),
        loc_outstanding=float(cache['loc_outstanding'][i]),
        loc_granted=float(cache['loc_granted'][i]),
        loc_headroom=float(cache['loc_headroom'][i]),
        has_factoring=bool(cache['has_factoring'][i]),
        factoring_outstanding=float(cache['factoring_outstanding'][i]),
        has_confirming=bool(cache['has_confirming'][i]),
        has_leasing=bool(cache['has_leasing'][i]),
        has_renting=bool(cache['has_renting'][i]),
        has_investment=bool(cache['has_investment'][i]),
        investment_balance=float(cache['investment_balance'][i]),
        checking_balance=float(cache['checking_balance'][i]),
        ar_invoices=ar_invoices,
        ap_invoices=ap_invoices,
    )
    memo[cid] = obj
    return obj


def _parse_due(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def select_ar_advance(
    obj: CompanyObjects,
    days: int,
    clients: Sequence[str] | None = None,
) -> ArPick:
    days = int(days)
    invoices = obj.ar_invoices
    if clients is not None:
        allowed = set(clients)
        invoices = tuple(inv for inv in invoices if inv.get('counterparty_id') in allowed)

    dated = []
    for inv in invoices:
        due = _parse_due(inv.get('due_date'))
        if due is None:
            continue
        dated.append((due, inv))

    if not invoices:
        amount = 0.0 if clients is not None else obj.ar_pending_eur * min(1.0, days / 30.0)
        amount = min(max(0.0, amount), obj.ar_pending_eur)
        return ArPick(days=days, amount_eur=amount, n_invoices=0, clients=())

    if not dated:
        base = sum(float(inv['pending_amount']) for inv in invoices)
        amount = min(max(0.0, base * min(1.0, days / 30.0)), obj.ar_pending_eur)
        return ArPick(days=days, amount_eur=amount, n_invoices=0, clients=())

    end = CUTOFF.toordinal() + days
    picked: list[dict[str, Any]] = []
    seen: list[str] = []
    seen_set: set[str] = set()
    total = 0.0
    for due, inv in dated:
        if due.toordinal() <= end:
            picked.append(inv)
            total += float(inv['pending_amount'])
            cp = str(inv.get('counterparty_id') or '')
            if cp and cp not in seen_set:
                seen_set.add(cp)
                seen.append(cp)

    amount = min(max(0.0, total), obj.ar_pending_eur)
    return ArPick(days=days, amount_eur=amount, n_invoices=len(picked), clients=tuple(seen))
