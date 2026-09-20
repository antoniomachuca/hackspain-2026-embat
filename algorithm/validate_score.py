import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithm.score_data import sha256
from algorithm.score_engine import ScoreConfig, bounded_momentum, calculate_scores
from algorithm.score_states import PENDING, StateConfig, classify_states


POINTS = ('liquidity_points', 'collections_points', 'debt_points', 'momentum_points', 'growth_points', 'fragility_points', 'clipping_points')
PILLARS = ('L', 'C', 'D', 'fragility')
ROOT = Path(__file__).resolve().parents[1]


def stress_control(config=None):
    receipts = np.r_[np.full(12, 120.0), np.maximum(120 - 10 * np.arange(1, 25), 5)][None, :]
    expenses = np.full_like(receipts, 100)
    debt = np.full_like(receipts, 5)
    bank = {'receipts': receipts, 'gross_receipts': receipts.copy(), 'refunds': np.zeros_like(receipts),
            'expenses': expenses, 'debt_service': debt, 'quality': np.ones_like(receipts), 'funding_gap': np.zeros_like(receipts)}
    cash = 300 + np.cumsum(receipts - expenses - debt, axis=1)
    collapse = int(np.flatnonzero(cash[0] <= 0)[0])
    core = calculate_scores(bank, config=config)
    observed_cash = calculate_scores(dict(bank, cash_balance=cash, commitments_30d=np.full_like(cash, 105.0)), config=config)
    result = {'opening_cash': 300, 'shock_starts_at_month_index': 12, 'cash_nonpositive_month_index': collapse,
              'cash_is_evaluation_only_in_bank_core_test': True, 'observed_on_real_companies': False, 'variants': {}}
    for name, output in (('bank_core', core), ('known_cash', observed_cash)):
        baseline = float(np.median(output['score'][0, 9:12]))
        alert = (output['score'][0] <= baseline - 5) & (output['momentum'][0] < -.1)
        candidates = np.flatnonzero(alert[12:collapse + 1])
        first = int(candidates[0] + 12) if len(candidates) else None
        differences = np.diff(output['score'][0, 12:collapse + 1])
        result['variants'][name] = {'baseline_score': baseline, 'score_at_cash_loss': float(output['score'][0, collapse]),
                                    'first_alert_month_index': first, 'lead_months': collapse - first if first is not None else None,
                                    'monotone_from_shock_to_cash_loss': bool(np.all(differences <= 1e-10)),
                                    'maximum_monthly_increase': float(np.max(differences)),
                                    'scores': output['score'][0].tolist(), 'momentum': output['momentum'][0].tolist()}
    return result


def trajectory_control(config=None):
    config = config or ScoreConfig()
    base = np.array([np.linspace(45, 65, 24), np.linspace(82, 68, 24)])
    trend = bounded_momentum(base, 2 * base / 100 - 1, np.ones_like(base), config)
    final = np.clip(base[:, -1] + config.momentum_weight * trend[:, -1], 0, 100)
    return {'input_type': 'idealized_base_paths_not_identified_CSV_companies',
            'recovery_final_base': 65, 'deterioration_final_base': 68,
            'recovery_final_score': float(final[0]), 'deterioration_final_score': float(final[1]),
            'recovery_momentum': float(trend[0, -1]), 'deterioration_momentum': float(trend[1, -1]),
            'passes': bool(trend[0, -1] > 0 and trend[1, -1] < 0 and final[0] > final[1])}


def rank_matrix(panels, mask):
    matrix, pairs, undefined = {}, [], []
    maximum = 0.0
    for left in PILLARS:
        matrix[left] = {}
        for right in PILLARS:
            x, y = panels[left][mask, -1], panels[right][mask, -1]
            if len(x) < 3 or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
                value = None
                if left != right:
                    undefined.append([left, right])
            else:
                value = float(spearmanr(x, y).statistic)
                if left != right:
                    maximum = max(maximum, abs(value))
                    if PILLARS.index(left) < PILLARS.index(right):
                        pairs.append({'left': left, 'right': right, 'spearman': value})
            matrix[left][right] = value
    return {'companies': int(mask.sum()), 'matrix': matrix, 'maximum_absolute_off_diagonal': maximum,
            'undefined_pairs': undefined, 'pairs': pairs, 'passes_065': bool(not undefined and mask.sum() >= 30 and maximum < .65)}


def summary(values):
    values = np.asarray(values)
    return {'min': float(values.min()), 'p05': float(np.quantile(values, .05)), 'median': float(np.median(values)),
            'p95': float(np.quantile(values, .95)), 'max': float(values.max()), 'mean': float(values.mean())}


def monthly_diagnostics(panels):
    result = []
    for month in range(5, panels['score'].shape[1]):
        view = {key: panels[key][:, :month + 1] for key in PILLARS}
        observed = ~panels['is_prior'][:, month]
        high = observed & (panels['bank_quality'][:, month] >= .8)
        all_matrix, high_matrix = rank_matrix(view, observed), rank_matrix(view, high)
        scores = panels['score'][observed, month]
        saturation = float(np.mean((scores <= 0) | (scores >= 100))) if len(scores) else 1.0
        result.append({'month_index': month, 'observed_companies': int(observed.sum()),
                       'max_correlation_observed': all_matrix['maximum_absolute_off_diagonal'],
                       'max_correlation_high_quality': high_matrix['maximum_absolute_off_diagonal'],
                       'correlation_pass': all_matrix['passes_065'] and high_matrix['passes_065'],
                       'saturation_observed': saturation})
    return result


def validate_outputs(panels, config=None, state_config=None):
    score = panels['score']
    numeric = [values for values in panels.values() if values.dtype.kind in 'fiu']
    all_finite = all(np.isfinite(values).all() for values in numeric)
    exact = bool(np.allclose(score, sum(panels[key] for key in POINTS), atol=1e-10, rtol=0))
    observed = ~panels['is_prior'][:, -1]
    high_quality = observed & (panels['bank_quality'][:, -1] >= .8)
    all_matrix, high_matrix = rank_matrix(panels, observed), rank_matrix(panels, high_quality)
    edges_all = float(np.mean((score[:, -1] <= 0) | (score[:, -1] >= 100)))
    edges_observed = float(np.mean((score[observed, -1] <= 0) | (score[observed, -1] >= 100))) if observed.any() else 1.0
    stress, trajectory = stress_control(config), trajectory_control(config)
    monthly = monthly_diagnostics(panels)
    stress_pass = all(row['lead_months'] is not None and row['lead_months'] >= 3 and row['monotone_from_shock_to_cash_loss'] for row in stress['variants'].values())
    domains = all(np.all((panels[key] >= 0) & (panels[key] <= 1)) for key in (*PILLARS, 'growth_quality'))
    domains = domains and np.all(np.abs(panels['momentum']) <= 1) and np.all((panels['base_health'] >= 0) & (panels['base_health'] <= 100))
    gates = {'finite_outputs': bool(all_finite), 'strict_range': bool(np.all((score >= 0) & (score <= 100))),
             'factor_domains': bool(domains), 'opposite_trajectories_control': trajectory['passes'],
             'exact_additive_waterfall': exact, 'spearman_below_065': all_matrix['passes_065'] and high_matrix['passes_065'],
             'endpoint_saturation_below_2pct': edges_all < .02 and edges_observed < .02,
             'synthetic_monotone_and_three_month_lead': stress_pass,
             'mature_month_correlations_below_065': bool(monthly) and all(row['correlation_pass'] for row in monthly),
             'mature_month_saturation_below_2pct': bool(monthly) and all(row['saturation_observed'] < .02 for row in monthly)}
    state_summary = {}
    if 'state' in panels:
        expected_states = classify_states(panels, state_config)
        gates['reproducible_state_classification'] = all(np.array_equal(panels[key], value) for key, value in expected_states.items())
        gates['priors_remain_unrated'] = bool(np.all(panels['state'][panels['is_prior']] == PENDING) and np.all(panels['health_band'][panels['is_prior']] == 'SIN_EVIDENCIA'))
        labels, counts = np.unique(panels['state'][:, -1], return_counts=True)
        state_summary = {'endpoint_counts': dict(zip(labels.tolist(), counts.tolist())),
                         'endpoint_eligible': int(panels['state_eligible'][:, -1].sum()),
                         'endpoint_seasonality_available': int(panels['seasonality_available'][:, -1].sum())}
    return {'gates': gates, 'all_gates_pass': all(gates.values()), 'trajectory_states': state_summary,
            'coverage': {'companies': score.shape[0], 'months': score.shape[1], 'endpoint_observed': int(observed.sum()),
                         'endpoint_prior': int(panels['is_prior'][:, -1].sum()), 'high_quality': int(high_quality.sum()),
                         'cash_known': int(panels['cash_known'][:, -1].sum()), 'erp_used': int(panels['erp_used'][:, -1].sum()),
                         'hhi_used': int(panels['hhi_used'][:, -1].sum())},
            'correlations_all_observed': all_matrix, 'correlations_high_quality': high_matrix,
            'endpoint_saturation_all': edges_all, 'endpoint_saturation_observed': edges_observed,
            'endpoint_score': summary(score[:, -1]),
            'endpoint_pillars': {key: summary(panels[key][:, -1]) for key in PILLARS},
            'stress_control': stress, 'trajectory_control': trajectory, 'monthly_diagnostics': monthly,
            'spearman_is_not_independence_proof': True, 'real_world_anticipation_validated': False,
            'credit_probability_calibrated': False, 'historical_cash_identifiable_without_anchor': False}


def main():
    parser = argparse.ArgumentParser(description='Empirical quality gates; failure is reported rather than hidden.')
    parser.add_argument('--results', type=Path, default=ROOT / 'algorithm' / 'engine_results')
    parser.add_argument('--strict', action='store_true', help='Exit nonzero if any empirical gate fails.')
    args = parser.parse_args()
    with (args.results / 'score_manifest.json').open(encoding='utf-8') as source:
        manifest = json.load(source)
    for key, name in (('engine_sha256', 'score_engine.py'), ('data_adapter_sha256', 'score_data.py'),
                      ('state_engine_sha256', 'score_states.py'), ('monitor_sha256', 'score_monitor.py')):
        if manifest.get(key) != sha256(Path(__file__).parent / name):
            raise SystemExit('Source files differ from the manifest; rerun calc_score before validation.')
    if manifest.get('panels_sha256') != sha256(args.results / 'score_panels.npz'):
        raise SystemExit('Panel content differs from the published manifest.')
    config = ScoreConfig(**manifest['config'])
    state_config = StateConfig(**manifest['state_config'])
    with np.load(args.results / 'score_panels.npz', allow_pickle=False) as stored:
        report = validate_outputs(dict(stored), config, state_config)
    report.update(model_version=manifest['model_version'], panels_sha256=manifest['panels_sha256'])
    with (args.results / 'validation.json').open('w', encoding='utf-8') as destination:
        json.dump(report, destination, ensure_ascii=False, indent=2, allow_nan=False)
        destination.write('\n')
    for name, passed in report['gates'].items():
        print(f'{name}: {"PASS" if passed else "FAIL"}')
    print(f"Correlations, observed / high quality: {report['correlations_all_observed']['maximum_absolute_off_diagonal']:.3f} / {report['correlations_high_quality']['maximum_absolute_off_diagonal']:.3f}")
    if args.strict and not report['all_gates_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
