"""Shared compatibility signature and generated leaderboard; never select on test."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from algorithm.score_data import sha256
from forecasting.models import CANDIDATES

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT/'forecasting'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def comparison_spec(protocol, inputs, mode, groups):
    # Model implementations are deliberately excluded: these are what contributors change.
    files = ('forecasting/data.py', 'forecasting/context.py', 'forecasting/country.py',
             'forecasting/benchmark.py', 'algorithm/score_engine.py', 'algorithm/score_data.py')
    definition = {'schema': 1, 'protocol': protocol, 'input_sha256': inputs, 'context_mode': mode,
                  'split_sha256': digest(groups), 'evaluation_sha256': {p: sha256(ROOT/p) for p in files}}
    return {'key': digest(definition), 'definition': definition}


def generate_leaderboard(baseline, runs, output):
    reference = json.loads(Path(baseline).read_text())
    signature = reference['comparison']['key']
    reports = [(Path(baseline), reference)]
    excluded = []
    for path in sorted(Path(runs).glob('*.json')):
        report = json.loads(path.read_text())
        if report.get('result_sha256') != digest({k: v for k, v in report.items() if k != 'result_sha256'}):
            raise ValueError(f'Benchmark result modified without rerunning: {path}')
        if report.get('comparison', {}).get('key') != signature:
            excluded.append((path.name, 'protocolo, datos, evaluación o contexto diferentes'))
            continue
        if set(report.get('horizons', {})) != set(reference['horizons']):
            excluded.append((path.name, 'faltan horizontes'))
            continue
        reports.append((path, report))
    rows = {h: [] for h in reference['horizons']}
    baseline_candidate = {}
    for horizon, value in reference['horizons'].items():
        best = min(m['macro_group_mae'] for m in value['validation'].values())
        admissible = [n for n in CANDIDATES if n in value['validation']
                      and value['validation'][n]['macro_group_mae'] <= best*1.02+1e-12]
        baseline_candidate[horizon] = min(admissible, key=CANDIDATES.index)
    for path, report in reports:
        for horizon, value in report['horizons'].items():
            for name, metric in value['validation'].items():
                error = metric['macro_group_mae']
                if not isinstance(error, (float, int)) or not math.isfinite(error) or error < 0:
                    raise ValueError(f'Invalid validation MAE: {path}')
                if metric['samples'] != reference['horizons'][horizon]['partitions']['validation']['samples'] or metric['groups'] != reference['horizons'][horizon]['partitions']['validation']['groups']:
                    raise ValueError(f'Validation cohort differs: {path}')
                info = report.get('contribution', {})
                complexity = info.get('complexity_rank', CANDIDATES.index(name) if name in CANDIDATES else 100)
                if not isinstance(complexity, int) or complexity < 0:
                    raise ValueError(f'Invalid complexity rank: {path}')
                rows[horizon].append({'model': name, 'run': report['run_id'], 'author': info.get('author', 'baseline'),
                    'mae': error, 'complexity': complexity, 'coverage': metric['interval_80_coverage'],
                    'direction': metric['balanced_direction_accuracy'], 'test': value.get('test', {}).get(name),
                    'paired': value.get('paired_vs_baseline', {}).get(baseline_candidate[horizon]),
                    'source': path, 'production_ready': not info or info.get('explanation_checked', False)})
    lines = ['# Comparación común de modelos', '',
             'Generado con `python -m forecasting.registry`. Se elige por **validación**, nunca por test.',
             f'Contrato comparable: `{signature[:16]}`. Baseline: `{reference["run_id"]}`.', '',
             'Dentro del 2% del mejor MAE por grupo gana la menor complejidad declarada (revisada en PR).',
             'La tabla propone candidatos: no cambia automáticamente el modelo de la demo.',
             'Δ positiva = mejora frente al candidato baseline; IC del bootstrap emparejado por grupo.',
             'La regla del 2% no cambia: el IC es contexto para juzgar si la diferencia se distingue del ruido.', '']
    winners = {}
    for h, entries in rows.items():
        eligible = [r for r in entries if r['production_ready']]
        best = min(r['mae'] for r in eligible)
        winner = min((r for r in eligible if r['mae'] <= best*1.02+1e-12),
                     key=lambda r: (r['complexity'], r['mae'], r['model'], r['run']))
        winners[h] = {'model': winner['model'], 'run_id': winner['run'], 'validation_macro_group_mae': winner['mae']}
        winners[h]['paired_vs_baseline'] = winner.get('paired')
        lines += [f'## {h} meses · candidato: {winner["model"]}', '',
                  f'| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Δ MAE vs {baseline_candidate[h]} [IC 95%] | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |',
                  '|---|---|---:|---:|---:|---:|---:|']
        for row in sorted(entries, key=lambda r: (r['mae'], r['complexity'])):
            test = '—' if row['test'] is None else f'{row["test"]["macro_group_mae"]:.2f}'
            marker = ' **← candidato**' if row is winner else ''
            relative = Path(os.path.relpath(row['source'], Path(output).parent)).as_posix()
            if row['paired'] is None:
                delta = '—'
            else:
                lo, hi = row['paired']['ci95']
                delta = f'{row["paired"]["delta_macro_group_mae"]:+.2f} [{lo:+.2f}, {hi:+.2f}]'
                if lo > 0:
                    delta += ' ✓'
            lines.append(f'| [{row["model"]} · {row["run"]}]({relative}){marker} | {row["author"]} | {row["mae"]:.2f} | {delta} | {row["direction"]:.1%} | {row["coverage"]:.1%} | {test} |')
        lines.append('')
    lines += ['*Test v1 ya publicado: diagnóstico, no criterio de selección. Para una nueva afirmación de generalización necesitamos otro holdout congelado.',
              'Antes de promover: revisar explicación, recalls en ambas direcciones, cobertura, estrés y coste de inferencia.', '']
    if excluded:
        lines += ['## Ejecuciones excluidas', '', *[f'- `{n}`: {reason}.' for n, reason in excluded], '']
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text('\n'.join(lines))
    Path(output).with_suffix('.json').write_text(json.dumps({'comparison_key': signature, 'candidates': winners,
        'excluded': excluded}, indent=2)+'\n')
    return winners


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=HOME/'benchmarks/baseline/benchmark.json')
    parser.add_argument('--runs', type=Path, default=HOME/'benchmarks/runs')
    parser.add_argument('--output', type=Path, default=HOME/'benchmarks/LEADERBOARD.md')
    args = parser.parse_args()
    print(json.dumps(generate_leaderboard(args.baseline, args.runs, args.output), indent=2))
