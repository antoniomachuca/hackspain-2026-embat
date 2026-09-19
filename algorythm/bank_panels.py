"""Fast per-company bank panel slices for /simulate.

Never call score_data.load_bank_panel from an HTTP handler (~13s).
Serve from engine_results/bank_inputs.npz built offline by calc_score / build_bank_inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
BANK_INPUTS_PATH = HERE / 'engine_results' / 'bank_inputs.npz'

# Fields required / consumed by calculate_scores.
SCORE_FIELDS = (
    'receipts', 'expenses', 'debt_service', 'gross_receipts', 'refunds',
    'quality', 'funding_gap', 'hhi', 'hhi_quality',
)

# Auxiliaries for lever mutators (not passed to calculate_scores unless folded into expenses).
LEVER_AUX_FIELDS = ('expenses_opex', 'expenses_ap')

_CACHE: dict[str, Any] | None = None


def bank_inputs_path(path: Path | None = None) -> Path:
    return Path(path) if path else BANK_INPUTS_PATH


def fill_expense_splits(bank: dict[str, np.ndarray], dataset: Path, companies: list[dict], edges) -> None:
    """Populate salary∪utility and payment∪bulk_payment without changing score_data.py."""
    from algorythm.score_data import normalize_transaction, parse_day, rows

    shape = bank['receipts'].shape
    bank['expenses_opex'] = np.zeros(shape)
    bank['expenses_ap'] = np.zeros(shape)
    index = {row['company_id']: i for i, row in enumerate(companies)}
    ordinals = np.array([day.toordinal() for day in edges])
    for row in rows(Path(dataset) / 'transactions.csv'):
        i = index.get(row['company_id'])
        if i is None or row.get('status') != 'booked':
            continue
        day = parse_day(row['date'])
        month = int(np.searchsorted(ordinals, day, side='right') - 1)
        if not 0 <= month < shape[1]:
            continue
        field, signed = normalize_transaction(row)
        if field != 'expenses':
            continue
        category = row.get('category')
        if category in {'salary', 'utility'}:
            bank['expenses_opex'][i, month] += signed
        elif category in {'payment', 'bulk_payment'}:
            bank['expenses_ap'][i, month] += signed
    bank['expenses_opex'] = np.maximum(bank['expenses_opex'], 0)
    bank['expenses_ap'] = np.maximum(bank['expenses_ap'], 0)


def export_bank_inputs(
    companies: list[dict],
    edges,
    bank: dict[str, np.ndarray],
    destination: Path | None = None,
) -> Path:
    """Serialize bank panel inputs for all companies (offline; ~2–3 MB compressed)."""
    target = bank_inputs_path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        'company_id': np.array([row['company_id'] for row in companies]),
        'group_id': np.array([row['group_id'] for row in companies]),
        'as_of': np.array([day.isoformat() for day in edges[1:]]),
    }
    for name in SCORE_FIELDS + LEVER_AUX_FIELDS:
        if name not in bank:
            raise KeyError(f'bank panel missing field required for bank_inputs: {name}')
        payload[name] = np.asarray(bank[name], dtype=np.float64)
    np.savez_compressed(target, **payload)
    global _CACHE
    _CACHE = None
    return target


def load_bank_inputs(path: Path | None = None) -> dict[str, Any]:
    global _CACHE
    target = bank_inputs_path(path)
    if _CACHE is not None and path is None:
        return _CACHE
    if not target.exists():
        raise FileNotFoundError(
            f'{target} missing. Build it with: python -m algorythm.build_bank_inputs'
        )
    with np.load(target, allow_pickle=False) as data:
        loaded = {k: data[k] for k in data.files}
    if path is None:
        _CACHE = loaded
    return loaded


def get_company_bank_slice(company_id: str, path: Path | None = None) -> dict[str, np.ndarray]:
    """Return a mutable bank dict with shape (1, M) for calculate_scores. Target < 1 ms."""
    cid = company_id.strip().upper()
    panels = load_bank_inputs(path)
    ids = [str(x) for x in panels['company_id']]
    if cid not in ids:
        raise KeyError(f'company_id not in bank_inputs: {cid}')
    i = ids.index(cid)
    slice_: dict[str, np.ndarray] = {}
    for name in SCORE_FIELDS + LEVER_AUX_FIELDS:
        if name in panels:
            slice_[name] = np.array(panels[name][i:i + 1], copy=True, dtype=np.float64)
    return slice_


def clone_bank_slice(bank: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {k: np.array(v, copy=True) for k, v in bank.items()}
