"""Offline builder for engine_results/bank_inputs.npz (~13s once; never on HTTP)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorythm.bank_panels import export_bank_inputs, fill_expense_splits
from algorythm.score_data import load_bank_panel

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='Export bank panel inputs for /simulate slices.')
    parser.add_argument('--dataset', type=Path, default=ROOT / 'dataset')
    parser.add_argument('--output', type=Path, default=ROOT / 'algorythm' / 'engine_results' / 'bank_inputs.npz')
    parser.add_argument('--start', default='2024-09-01')
    parser.add_argument('--end', default='2026-09-01')
    args = parser.parse_args()
    print('Loading bank panel (one-shot offline build)…', flush=True)
    companies, edges, bank, audit = load_bank_panel(args.dataset, args.start, args.end)
    fill_expense_splits(bank, args.dataset, companies, edges)
    path = export_bank_inputs(companies, edges, bank, args.output)
    print(f'Wrote {path} · {len(companies)} companies × {len(edges) - 1} months', flush=True)
    print(f"Audit: {audit}", flush=True)


if __name__ == '__main__':
    main()
