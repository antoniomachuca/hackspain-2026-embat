"""Reproducible benchmark and deployable, JSON-only forecast artifacts.

Run: python -m forecasting.benchmark --dataset data
No model deserialization or training occurs in API requests.
"""
import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from forecasting.context import load_context
from forecasting.data import (FEATURE_NAMES, INTERNAL_FEATURES, Samples, feature_panel,
                                    make_samples, partition_samples, split_groups)
from forecasting.country import known_country
from forecasting.models import CANDIDATES, Forecaster
from forecasting.stress import PROFILES, generate_stress, stress_score_report, synthetic_erp
from forecasting.registry import comparison_spec
from algorithm.score_data import load_bank_panel, month_edges, sha256
from algorithm.score_monitor import atomic_json

HERE = Path(__file__).resolve().parent


def default_dataset():
    root = HERE.parent
    for name in ('data', 'dataset'):
        if (root/name/'companies.csv').exists():
            return root/name
    return root/'data'


def load_protocol():
    return json.loads((HERE/'protocol.json').read_text())


def metrics(samples, predictions, probabilities, seed=419, bootstrap=300):
    lo, med, hi = predictions.T
    errors = np.abs(samples.y-med)
    groups = np.unique(samples.group)
    group_errors = np.array([errors[samples.group == g].mean() for g in groups])
    rng = np.random.default_rng(seed)
    ci = np.quantile(rng.choice(group_errors, (bootstrap, len(groups))).mean(axis=1), [.025, .975])
    actual_delta, predicted_delta = samples.y-samples.current, med-samples.current
    actual_direction = np.where(actual_delta < -3, 0, np.where(actual_delta > 3, 2, 1))
    predicted_direction = np.where(predicted_delta < -3, 0, np.where(predicted_delta > 3, 2, 1))
    recalls = {label: float(np.mean(predicted_direction[actual_direction == j] == j))
               if np.any(actual_direction == j) else None
               for j, label in enumerate(('deterioration', 'stable', 'improvement'))}
    pinball = []
    for j, q in enumerate((.1, .5, .9)):
        residual = samples.y-predictions[:, j]
        pinball.append(float(np.mean(np.maximum(q*residual, (q-1)*residual))))
    truth = np.eye(3)[actual_direction]
    neutral = actual_direction == 1
    return {'samples': len(errors), 'groups': len(groups), 'mae': float(errors.mean()),
            'macro_group_mae': float(group_errors.mean()), 'macro_group_mae_ci95': ci.tolist(),
            'rmse': float(np.sqrt(np.mean((samples.y-med)**2))),
            'direction_accuracy': float(np.mean(actual_direction == predicted_direction)),
            'balanced_direction_accuracy': float(np.mean([r for r in recalls.values() if r is not None])),
            'direction_recall': recalls,
            'false_deterioration_on_stable': float(np.mean(predicted_direction[neutral] == 0)) if neutral.any() else None,
            'interval_80_coverage': float(np.mean((samples.y >= lo) & (samples.y <= hi))),
            'mean_interval_width': float(np.mean(hi-lo)), 'pinball_q10_q50_q90': pinball,
            'direction_brier': float(np.mean(np.sum((probabilities-truth)**2, axis=1)))}


def choose_model(validation):
    best = min(m['macro_group_mae'] for m in validation.values())
    admissible = [name for name in CANDIDATES if validation[name]['macro_group_mae'] <= best*1.02+1e-12]
    return admissible[0]


def future_date(as_of, horizon):
    y, m = map(int, as_of[:7].split('-'))
    total = y*12+m-1+horizon
    return f'{total//12:04}-{total%12+1:02}-01'


def export_forecasts(companies, as_of, features, scores, eligible, winners, run_id, directory):
    output = {}
    for i, company in enumerate(companies):
        cid = company['company_id']
        item = {'company_id': cid, 'as_of': as_of[-1], 'run_id': run_id,
                'target': 'bank_only_score', 'status': 'available' if eligible[i, -1] else 'insufficient_history',
                'current_score': float(scores['score'][i, -1]),
                'history': [{'as_of': d, 'score': float(scores['score'][i, t]),
                             'eligible': bool(eligible[i, t])} for t, d in enumerate(as_of)],
                'context': {'country': company.get('country') or None, 'sector': company.get('sector') or None,
                            'external_indicators_available': int(np.sum(features[i, -1, INTERNAL_FEATURES+1::3] == 0))},
                'scenario_semantics': 'P10 pesimista / P50 central conservador / P90 optimista. Cobertura nominal 80%, marginal y no garantizada.',
                'points': []}
        if eligible[i, -1]:
            for horizon, (model, test_metrics) in winners.items():
                current = float(scores['score'][i, -1])
                previous_year = len(as_of)-1+horizon-12
                seasonal = scores['score'][i, previous_year] if previous_year >= 0 and eligible[i, previous_year] else current
                sample = Samples(features[i:i+1, -1], np.array([np.nan]), np.array([current]),
                    np.array([seasonal]), np.array([cid]), np.array([company['group_id']]),
                    np.array([len(as_of)-1]), np.array([len(as_of)-1+horizon]))
                pred = model.predict(sample)[0]
                probs = model.direction_probabilities(sample)[0]
                explanation = model.explain(sample)
                contributions = sorted(explanation['contributions'], key=lambda c: abs(c['points']), reverse=True)
                explanation['contributions'] = contributions[:5]
                explanation['other_points'] = sum(c['points'] for c in contributions[5:])
                item['points'].append({'horizon_months': horizon, 'as_of': future_date(as_of[-1], horizon),
                    'pessimistic': float(pred[0]), 'conservative': float(pred[1]), 'optimistic': float(pred[2]),
                    'probability_down': float(probs[0]), 'probability_stable': float(probs[1]),
                    'probability_up': float(probs[2]), 'model': model.name,
                    'test_mae': test_metrics['mae'], 'test_interval_coverage': test_metrics['interval_80_coverage'],
                    'explanation': explanation})
        output[cid] = item
    atomic_json(directory/'forecasts.json', {'run_id': run_id, 'companies': output})


def markdown_report(report):
    lines = ['# Benchmark de previsión y estrés', '',
             f"Ejecución `{report['run_id']}`. Target: score bancario futuro; no probabilidad de impago.", '',
             'Selección por MAE medio entre grupos de validación; el test se consulta después.', '',
             '| Horizonte | Modelo seleccionado | N test / grupos | MAE test | MAE por grupo (IC 95%) | Cobertura 80% | Recall mejora / deterioro |',
             '|---|---|---:|---:|---|---:|---|']
    for h, row in report['horizons'].items():
        m = row['test'][row['selected']]
        ci = m['macro_group_mae_ci95']
        recall = m['direction_recall']
        recall_text = ' / '.join(f'{recall[k]:.1%}' if recall[k] is not None else '—' for k in ('improvement', 'deterioration'))
        lines.append(f"| {h} meses | {row['selected']} | {m['samples']} / {m['groups']} | {m['mae']:.2f} | {m['macro_group_mae']:.2f} ({ci[0]:.2f}–{ci[1]:.2f}) | {m['interval_80_coverage']:.1%} | {recall_text} |")
    lines += ['', '## Comparación completa (test)', '', '| Meses | Modelo | MAE grupo | MAE | Dirección equilibrada | Cobertura | Anchura |',
              '|---|---|---:|---:|---:|---:|---:|']
    for h, row in report['horizons'].items():
        for name, m in row['test'].items():
            lines.append(f"| {h} | {name} | {m['macro_group_mae']:.2f} | {m['mae']:.2f} | {m['balanced_direction_accuracy']:.1%} | {m['interval_80_coverage']:.1%} | {m['mean_interval_width']:.2f} |")
    lines += ['', '## Estrés del score y monitor', '', '| Caso | Delta emparejado mediano | Detección ≤6m | Alertas adversas/año |', '|---|---:|---|---:|']
    for name, m in report['stress']['score_monitor'].items():
        detection = m.get('detection_within_6_months')
        detection_text = '—' if detection is None else f'{detection:.1%}'
        lines.append(f"| {name} | {m['paired_score_delta_median']:.2f} | {detection_text} | {m['adverse_alerts_per_company_year']:.2f} |")
    lines += ['', 'La tasa de alertas es falsa alarma solo en controles estables/estacionales; en shocks mezcla alertas verdaderas y falsas.',
              '', '## Contexto y límites', '', f"Modo externo: `{report['context']['mode']}`; cobertura de indicadores: {report['context']['historical_value_coverage']:.1%}.",
              'La ablación con contexto queda sin evidencia cuando no hay observaciones externas disponibles a fecha de corte.', '',
              *['- '+s for s in report['protocol']['limitations']], '',
              'Los tres escenarios son cuantiles marginales por horizonte; las líneas que los unen no representan trayectorias conjuntas ni una garantía del 80%.',
              'La mediana se etiqueta central/conservador: no incorpora una política adicional de aversión al riesgo.',
              'Ver benchmark.json para particiones, métricas de todos los modelos bajo estrés, semillas y hashes.', '']
    return '\n'.join(lines)


def run(dataset, output, context_path=None, allow_assumed=False, stress_n=None):
    start = time.perf_counter()
    protocol = load_protocol()
    if stress_n is not None:
        protocol['stress_companies_per_case'] = stress_n
    output.mkdir(parents=True, exist_ok=True)
    print('Loading bank panel (organizer data).', flush=True)
    companies, edges, bank, audit = load_bank_panel(dataset)
    as_of = [d.isoformat() for d in edges[1:]]
    context = load_context(context_path)
    groups = split_groups(companies, protocol['seed'])
    features, scores, eligible = feature_panel(bank, companies, as_of, context, allow_assumed)
    sources = {str(p.relative_to(HERE.parent)): sha256(p) for p in HERE.glob('*.py')}
    sources.update({f'algorithm/{k}': sha256(HERE.parent/'algorithm'/k) for k in ('score_engine.py', 'score_data.py', 'score_states.py', 'score_monitor.py', 'behavior_benchmark.py')})
    sources.update({f'forecasting/{k}': sha256(HERE/k) for k in ('protocol.json', 'policy_rates.json')})
    inputs = {name: sha256(dataset/name) for name in ('companies.csv', 'transactions.csv', 'banking_products.csv', 'debt_products.csv')}
    if context_path:
        inputs['external_context'] = sha256(context_path)
    import hashlib
    versions = {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__}
    run_id = hashlib.sha256(json.dumps({'sources': sources, 'inputs': inputs, 'protocol': protocol,
                                      'allow_assumed': allow_assumed, 'versions': versions}, sort_keys=True).encode()).hexdigest()[:16]
    report = {'run_id': run_id, 'protocol': protocol, 'source_sha256': sources, 'input_sha256': inputs,
              'versions': versions,
              'companies': len(companies), 'months': len(as_of), 'groups': groups, 'bank_audit': audit,
              'context': {'mode': 'conservative_publication_lag' if allow_assumed else 'strict_point_in_time',
                          'rows': len(context), 'historical_value_coverage': float(np.mean(features[:, 5:, INTERNAL_FEATURES+1::3] == 0)),
                          'country_known': sum(known_country(c.get('country')) for c in companies),
                          'sector_known': sum(bool(c.get('sector')) for c in companies)},
              'horizons': {}, 'stress': {'seed': protocol['stress_seed'], 'profiles': PROFILES,
                  'score_monitor': {}, 'forecast': {}, 'donor_source': 'Training groups, first 12 months only'}}
    report['comparison'] = comparison_spec(protocol, inputs, report['context']['mode'], groups)
    stresses = generate_stress(bank, companies, groups, protocol)
    stress_features = {}
    stress_dates = [d.isoformat() for d in month_edges('2024-01-01', future_date('2024-01-01', protocol['stress_months']))[1:]]
    synthetic_dir = output/'synthetic'
    synthetic_dir.mkdir(exist_ok=True)
    for name, stress_bank, control, synthetic_companies, oracle in stresses:
        erp = synthetic_erp(stress_bank, name, oracle['change'])
        control_erp = synthetic_erp(control, 'control', oracle['change'])
        report['stress']['score_monitor'][name] = stress_score_report(stress_bank, control, oracle, erp, control_erp)
        # These matrices are directly accepted by calculate_scores; no invented raw transactions.
        np.savez_compressed(synthetic_dir/f'{name}.npz', **stress_bank)
        np.savez_compressed(synthetic_dir/f'{name}_erp.npz', **erp)
        np.savez_compressed(synthetic_dir/f'{name}_control.npz', **control)
        np.savez_compressed(synthetic_dir/f'{name}_oracle.npz', cash_after_change=oracle['cash_after_change'])
        atomic_json(synthetic_dir/f'{name}.json', {'scenario': name, 'companies': synthetic_companies,
            'as_of': stress_dates, 'seed': protocol['stress_seed'], 'change_index': oracle['change'],
            'expected_direction': oracle['expected_direction'], 'synthetic': True})
        stress_features[name] = (*feature_panel(stress_bank, synthetic_companies, stress_dates), synthetic_companies)
    models, winners = {}, {}
    for horizon in protocol['horizons']:
        print(f'Benchmark horizon {horizon} months.', flush=True)
        samples = make_samples(features, scores, eligible, companies, horizon)
        partitions = partition_samples(samples, groups, protocol)
        row = {'partitions': {name: {'samples': len(s.y), 'groups': len(np.unique(s.group)),
                    'origin_min': int(s.origin.min()), 'origin_max': int(s.origin.max()),
                    'target_end_max': int(s.target_end.max())} for name, s in partitions.items()},
               'validation': {}, 'test': {}, 'fit_seconds': {}, 'slices': {}}
        models[horizon] = {}
        for name in CANDIDATES:
            model = Forecaster(name, horizon).fit(partitions['train']).calibrate(partitions['calibration'])
            models[horizon][name] = model
            row['fit_seconds'][name] = model.fit_seconds
            sample = partitions['validation']
            row['validation'][name] = metrics(sample, model.predict(sample), model.direction_probabilities(sample))
        row['selected'] = choose_model(row['validation'])
        # Selection frozen before any test outcomes are evaluated.
        for name, model in models[horizon].items():
            sample = partitions['test']
            row['test'][name] = metrics(sample, model.predict(sample), model.direction_probabilities(sample))
        selected = models[horizon][row['selected']]
        winners[horizon] = selected, row['test'][row['selected']]
        test = partitions['test']
        company_map = {c['company_id']: c for c in companies}
        for country in sorted({company_map[c].get('country') or 'unknown' for c in test.company}):
            subset = test.take(np.array([(company_map[c].get('country') or 'unknown') == country for c in test.company]))
            row['slices']['country_'+country] = metrics(subset, selected.predict(subset), selected.direction_probabilities(subset))
        report['horizons'][str(horizon)] = row
        report['stress']['forecast'][str(horizon)] = {}
        for scenario, (sx, ss, se, sc) in stress_features.items():
            sample = make_samples(sx, ss, se, sc, horizon)
            # Includes pre-shock origins; no model sees scenario labels or the cash oracle.
            sample = sample.take(sample.origin >= protocol['stress_change_index']-horizon)
            report['stress']['forecast'][str(horizon)][scenario] = {
                name: metrics(sample, m.predict(sample), m.direction_probabilities(sample), bootstrap=100)
                for name, m in models[horizon].items()} if len(sample.y) else {'status': 'no_eligible_samples'}
    export_forecasts(companies, as_of, features, scores, eligible, winners, run_id, output)
    report['elapsed_seconds'] = time.perf_counter()-start
    atomic_json(output/'benchmark.json', report)
    (output/'REPORT.md').write_text(markdown_report(report))
    print(f'Written {output}/REPORT.md and forecasts.json ({report["elapsed_seconds"]:.1f}s).', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=default_dataset())
    parser.add_argument('--output', type=Path, default=HERE/'artifacts')
    parser.add_argument('--context', type=Path, default=HERE/'datasets/external/external_context.csv')
    parser.add_argument('--allow-assumed-publication', action='store_true')
    parser.add_argument('--stress-companies', type=int)
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.dataset, args.output, args.context, args.allow_assumed_publication, args.stress_companies)


if __name__ == '__main__':
    main()
