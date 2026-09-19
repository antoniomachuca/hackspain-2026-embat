"""Offline builder for engine_results/lever_objects.npz (scan invoices once)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorythm.levers_objects import INVOICES_PATH, build_lever_objects

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='Export per-company lever objects and pending invoices.')
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'algorythm' / 'engine_results' / 'lever_objects.npz',
    )
    args = parser.parse_args()
    print('Scanning invoices.csv once and building lever objects…', flush=True)
    path = build_lever_objects(destination=args.output)
    sidecar = path.parent / 'pending_invoices.npz'
    if path.resolve() == (ROOT / 'algorythm' / 'engine_results' / 'lever_objects.npz').resolve():
        sidecar = INVOICES_PATH
    print(f'Wrote {path} ({path.stat().st_size} bytes)', flush=True)
    if sidecar.exists():
        print(f'Wrote {sidecar} ({sidecar.stat().st_size} bytes)', flush=True)


if __name__ == '__main__':
    main()
