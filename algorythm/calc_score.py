import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import numpy as np

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorythm.score_data import add_cash_observations, load_bank_panel, load_erp_snapshot, sha256
from algorythm.score_engine import ScoreConfig, calculate_scores
from algorythm.score_monitor import atomic_json, monitor_once
from algorythm.score_states import StateConfig, classify_states


ROOT = Path(__file__).resolve().parents[1]


def calculate_dataset(dataset, start='2024-09-01', end='2026-09-01', erp_snapshot=False, cash_observations=None, config=None, state_config=None, erp_single_snapshot=False):
    config = config or ScoreConfig()
    companies, edges, bank, audit = load_bank_panel(Path(dataset), start, end)
    if cash_observations is not None:
        add_cash_observations(bank, companies, edges, Path(cash_observations))
    erp = None
    erp_audit = {'mode': 'disabled_without_verified_direction_and_historical_states'}
    if erp_snapshot:
        snapshot_as_of = '2026-09-01' if erp_single_snapshot else None
        erp, erp_audit = load_erp_snapshot(Path(dataset), companies, edges, bank, snapshot_as_of=snapshot_as_of)
        erp_audit['mode'] = 'single_snapshot_assumed_positive_sales' if erp_single_snapshot else 'continuous_monthly_erp_panel'
    output = calculate_scores(bank, erp, config)
    output.update(classify_states(output, state_config))
    return companies, edges, bank, output, {'bank': audit, 'erp': erp_audit}


def export_scores(directory, companies, edges, bank, output, manifest):
    directory.mkdir(parents=True, exist_ok=True)
    names = list(output)
    with tempfile.TemporaryDirectory(dir=directory, prefix='.score-export-') as temporary:
        staging = Path(temporary)
        with (staging / 'scores_monthly.csv').open('w', newline='', encoding='utf-8') as destination:
            writer = csv.writer(destination)
            writer.writerow(['company_id', 'group_id', 'currency', 'as_of'] + names)
            for i, company in enumerate(companies):
                for month, cutoff in enumerate(edges[1:]):
                    writer.writerow([company['company_id'], company['group_id'], company['currency'], cutoff.isoformat()] + [output[name][i, month].item() for name in names])
        panels = dict(output, company_id=np.array([row['company_id'] for row in companies]),
                      group_id=np.array([row['group_id'] for row in companies]),
                      as_of=np.array([day.isoformat() for day in edges[1:]]),
                      bank_native_share=bank['native_share'], bank_classified_share=bank['classified_share'])
        np.savez_compressed(staging / 'score_panels.npz', **panels)
        manifest['panels_sha256'] = sha256(staging / 'score_panels.npz')
        manifest['csv_sha256'] = sha256(staging / 'scores_monthly.csv')
        for filename in ('scores_monthly.csv', 'score_panels.npz'):
            os.replace(staging / filename, directory / filename)
        atomic_json(directory / 'score_manifest.json', manifest)


def source_hashes():
    return {key: sha256(Path(__file__).parent / name) for key, name in (
        ('engine_sha256', 'score_engine.py'), ('data_adapter_sha256', 'score_data.py'),
        ('state_engine_sha256', 'score_states.py'), ('monitor_sha256', 'score_monitor.py'))}


def main():
    parser = argparse.ArgumentParser(description='Dynamic financial health index with explicit availability and additive contributions.')
    parser.add_argument('--dataset', type=Path, default=ROOT / 'dataset')
    parser.add_argument('--output', type=Path, default=ROOT / 'algorythm' / 'engine_results')
    parser.add_argument('--start', default='2024-09-01')
    parser.add_argument('--end', default='2026-09-01', help='Exclusive transaction boundary, included as final as_of date.')
    parser.add_argument('--erp-snapshot-assumed-positive', action='store_true', help='Opt in to ERP invoice analysis across evaluation cutoffs.')
    parser.add_argument('--erp-single-snapshot', action='store_true', help='Limit ERP to the single 2026-09-01 snapshot.')
    parser.add_argument('--cash-observations', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--state-config', type=Path)
    args = parser.parse_args()
    values = {}
    if args.config:
        with args.config.open(encoding='utf-8') as source:
            values = json.load(source)
    config = ScoreConfig(**values)
    state_values = {}
    if args.state_config:
        with args.state_config.open(encoding='utf-8') as source:
            state_values = json.load(source)
    state_config = StateConfig(**state_values)
    hashes = source_hashes()
    print('Loading observed bank flows and calculating monthly scores.', flush=True)
    companies, edges, bank, output, audit = calculate_dataset(args.dataset, args.start, args.end,
                                                              args.erp_snapshot_assumed_positive, args.cash_observations, config, state_config,
                                                              erp_single_snapshot=args.erp_single_snapshot)
    if hashes != source_hashes():
        raise RuntimeError('Source files changed during calculation; rerun on a stable working tree.')
    inputs = ['companies.csv', 'banking_products.csv', 'debt_products.csv', 'transactions.csv']
    if args.erp_snapshot_assumed_positive:
        inputs.append('invoices.csv')
    model_identity = dict(hashes, score_config=asdict(config), state_config=asdict(state_config), erp_mode=audit['erp']['mode'])
    model_version = hashlib.sha256(json.dumps(model_identity, sort_keys=True).encode()).hexdigest()
    manifest = {'companies': len(companies), 'months': len(edges) - 1, 'config': asdict(config), 'audit': audit,
                'state_config': asdict(state_config), 'model_version': model_version,
                'input_sha256': {name: sha256(args.dataset / name) for name in inputs}, **hashes,
                'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__},
                'cash_observations_sha256': sha256(args.cash_observations) if args.cash_observations else None,
                'terminal_balances_used': False, 'credit_rating_calibrated': False,
                'endpoint_prior_count': int(output['is_prior'][:, -1].sum()),
                'endpoint_cash_known_count': int(output['cash_known'][:, -1].sum()),
                'endpoint_erp_used_count': int(output['erp_used'][:, -1].sum())}
    export_scores(args.output, companies, edges, bank, output, manifest)
    monitor = monitor_once(args.output)
    print(f"Exported {len(companies)} companies x {len(edges)-1} months to {args.output}", flush=True)
    print(f"Monitor: {monitor['status']}, {len(monitor['new_alerts'])} new notifications.", flush=True)
    print(f"Endpoint: {manifest['endpoint_prior_count']} neutral priors, {manifest['endpoint_cash_known_count']} known cash observations, {manifest['endpoint_erp_used_count']} ERP enrichments.")


if __name__ == '__main__':
    main()
