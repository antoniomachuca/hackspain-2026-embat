"""Train one independent contribution on the shared protocol and register its results."""
import argparse
import importlib
import inspect
import json
import platform
import re
import time
from pathlib import Path

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from algorythm.score_data import load_bank_panel, sha256
from forecasting.benchmark import load_protocol, metrics
from forecasting.context import load_context
from forecasting.data import Samples, feature_panel, make_samples, partition_samples, split_groups
from forecasting.registry import HOME, comparison_spec, digest
from forecasting.stress import SCENARIOS


def blind(samples):
    """Inference receives no future labels, including when explaining predictions."""
    return Samples(**{k: np.full_like(v, np.nan) if k == 'y' else v.copy() for k, v in vars(samples).items()})


def evaluate(model, samples):
    start = time.perf_counter()
    predictions = np.asarray(model.predict(blind(samples)), dtype=float)
    probabilities = np.asarray(model.direction_probabilities(blind(samples)), dtype=float)
    if predictions.shape != (len(samples.y), 3) or not np.isfinite(predictions).all():
        raise ValueError('predict must return finite (n,3) P10/P50/P90')
    if (predictions < 0).any() or (predictions > 100).any() or (np.diff(predictions, axis=1) < 0).any():
        raise ValueError('Quantiles must be ordered and bounded in [0,100]')
    if probabilities.shape != predictions.shape or not np.isfinite(probabilities).all() or (probabilities < -1e-12).any() or not np.allclose(probabilities.sum(axis=1), 1):
        raise ValueError('Probabilities must be finite down/stable/up, nonnegative, summing to one')
    elapsed = time.perf_counter()-start
    result = metrics(samples, predictions, probabilities)
    result['inference_ms_per_1000'] = elapsed/max(1, len(samples.y))*1_000_000
    return result


def check_explanations(model, samples):
    for i in range(min(5, len(samples.y))):
        sample = blind(samples.take(np.array([i])))
        e = model.explain(sample)
        total = (e['current_score']+e['reference_delta']+sum(c['points'] for c in e['contributions'])+
                 e.get('other_points', 0)+e['calibration_points']+e['clipping_points'])
        prediction = model.predict(sample)[0, 1]
        if not np.isfinite(total) or not np.isclose(total, prediction, atol=1e-6) or not np.isclose(e['current_score'], sample.current[0]):
            raise ValueError('Explanation does not reconstruct the forecast')


def load_frozen_stress(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'MANIFEST.json').read_text())
    for name, expected in manifest['files_sha256'].items():
        if sha256(directory/name) != expected:
            raise ValueError(f'Frozen stress dataset changed: {name}')
    panels = {}
    for name in SCENARIOS:
        metadata = json.loads((directory/f'{name}.json').read_text())
        with np.load(directory/f'{name}.npz', allow_pickle=False) as archive:
            bank = dict(archive)
        panels[name] = (*feature_panel(bank, metadata['companies'], metadata['as_of']), metadata['companies'])
    return panels, sha256(directory/'MANIFEST.json')


def run(factory_spec, author, run_name, dataset, context, output, final_test=False):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', run_name) or not re.fullmatch(r'[a-zA-Z0-9_-]+', author):
        raise ValueError('author and run-name allow only letters, digits, underscores and hyphens')
    path = output/f'{author}__{run_name}.json'
    if path.exists():
        raise FileExistsError(f'{path} exists. Use a new run-name; previous experiments are immutable.')
    module_name, factory_name = factory_spec.split(':', 1)
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name)
    info = dict(module.MODEL_INFO)
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', info['name']):
        raise ValueError('MODEL_INFO.name must be a simple identifier')
    if not isinstance(info.get('complexity_rank'), int) or info['complexity_rank'] < 0:
        raise ValueError('MODEL_INFO requires nonnegative complexity_rank')
    protocol = load_protocol()
    companies, edges, bank, _ = load_bank_panel(dataset)
    dates = [d.isoformat() for d in edges[1:]]
    groups = split_groups(companies, protocol['seed'])
    x, scores, eligible = feature_panel(bank, companies, dates, load_context(context))
    inputs = {name: sha256(dataset/name) for name in ('companies.csv', 'transactions.csv', 'banking_products.csv', 'debt_products.csv')}
    inputs['external_context'] = sha256(context)
    comparison = comparison_spec(protocol, inputs, 'strict_point_in_time', groups)
    stress, stress_hash = load_frozen_stress(HOME/'datasets/synthetic/v1')
    source = Path(inspect.getfile(module))
    source_hash = sha256(source)
    run_id = f'{author}__{run_name}'
    report = {'schema_version': 1, 'run_id': run_id, 'comparison': comparison, 'protocol': protocol,
              'input_sha256': inputs, 'contribution': {**info, 'author': author, 'factory': factory_spec,
                  'source_sha256': source_hash, 'source_file': str(source.relative_to(HOME.parent)),
                  'source_code': source.read_text(),
                  'explanation_checked': True}, 'stress_manifest_sha256': stress_hash,
              'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
              'test_policy': 'visible_v1_diagnostic_only' if final_test else 'not_evaluated',
              'horizons': {}, 'stress': {}}
    for horizon in protocol['horizons']:
        print(f'{run_id}: training and validating {horizon}M', flush=True)
        parts = partition_samples(make_samples(x, scores, eligible, companies, horizon), groups, protocol)
        model = factory(horizon=horizon, seed=protocol['seed'])
        start = time.perf_counter()
        model.fit(parts['train'])
        model.calibrate(parts['calibration'])
        elapsed = time.perf_counter()-start
        name = info['name']
        check_explanations(model, parts['validation'])
        row = {'validation': {name: evaluate(model, parts['validation'])}, 'test': {},
               'fit_and_calibration_seconds': elapsed,
               'partitions': {p: {'samples': len(s.y), 'groups': len(np.unique(s.group))} for p, s in parts.items()}}
        if final_test:
            row['test'][name] = evaluate(model, parts['test'])
        report['horizons'][str(horizon)] = row
        report['stress'][str(horizon)] = {}
        for scenario, (sx, ss, se, sc) in stress.items():
            samples = make_samples(sx, ss, se, sc, horizon)
            samples = samples.take(samples.origin >= protocol['stress_change_index']-horizon)
            report['stress'][str(horizon)][scenario] = evaluate(model, samples) if len(samples.y) else {'status': 'no_eligible_samples'}
    if sha256(source) != source_hash:
        raise RuntimeError('Experiment source changed during training; rerun')
    if comparison_spec(protocol, inputs, 'strict_point_in_time', groups) != comparison:
        raise RuntimeError('Common evaluation code changed during training; rerun')
    report['result_sha256'] = digest(report)
    output.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(f'Registered {path}. Run python -m forecasting.registry to compare.', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factory', required=True, help='Local Python module:function; see experiments/extra_trees.py')
    parser.add_argument('--author', required=True)
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--dataset', type=Path, default=HOME.parent/'data')
    parser.add_argument('--context', type=Path, default=HOME/'datasets/external/external_context.csv')
    parser.add_argument('--output', type=Path, default=HOME/'benchmarks/runs')
    parser.add_argument('--final-test', action='store_true', help='Report diagnostic v1 test; never used for model selection')
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.factory, args.author, args.run_name, args.dataset, args.context, args.output, args.final_test)
