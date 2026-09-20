import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from algorithm.score_data import load_bank_panel, sha256
from algorithm.score_engine import calculate_scores, divide
from algorithm.score_monitor import atomic_json, directional_event_matrix
from algorithm.score_states import StateConfig, classify_states


HERE = Path(__file__).resolve().parent


def load_protocol():
    with (HERE / 'trajectory_protocol.json').open(encoding='utf-8') as source:
        return json.load(source)


def generate_scenario(name, seed, protocol):
    settings = protocol['synthetic']
    scenario_index = settings['scenarios'].index(name)
    rng = np.random.default_rng(np.random.SeedSequence([seed, scenario_index]))
    n, months = settings['companies_per_scenario'], settings['months']
    change = settings['change_month_index']
    operating = rng.lognormal(np.log(100), .5, (n, 1))
    debt = operating * rng.uniform(.01, .10, (n, 1))
    total_out = operating + debt
    limits = settings['recovery_margin_range'] if name == 'recovery' else settings['healthy_margin_range']
    baseline = rng.uniform(*limits, (n, 1))
    noise = rng.normal(0, settings['margin_noise_sd'], (n, months))
    phi = settings['noise_autocorrelation']
    for month in range(1, months):
        noise[:, month] = phi * noise[:, month - 1] + np.sqrt(1 - phi ** 2) * noise[:, month]
    margin = baseline + noise
    ramp = np.arange(1, months - change + 1)[None, :]
    if name in ('deterioration', 'improvement', 'recovery'):
        slopes = rng.uniform(*settings['margin_step_range'], (n, 1))
        sign = -1 if name == 'deterioration' else 1
        margin[:, change:] += sign * slopes * ramp
    if name in ('pulse', 'abrupt_deterioration'):
        if name == 'pulse':
            margin[:, change] -= settings['pulse_size']
        else:
            margin[:, change:] -= settings['pulse_size']
    if name == 'seasonal':
        phase = rng.uniform(0, 2 * np.pi, (n, 1))
        margin += settings['seasonal_amplitude'] * np.sin(2 * np.pi * np.arange(months)[None, :] / 12 + phase)
    margin = np.clip(margin, -.70, .70)
    receipts = total_out * (1 + margin) / (1 - margin)
    expenses = np.broadcast_to(operating, receipts.shape).copy()
    service = np.broadcast_to(debt, receipts.shape).copy()
    bank = {'receipts': receipts, 'gross_receipts': receipts.copy(), 'refunds': np.zeros_like(receipts),
            'expenses': expenses, 'debt_service': service, 'funding_gap': np.zeros_like(receipts), 'quality': np.ones_like(receipts)}
    buffer = rng.uniform(*settings['cash_at_change_outflow_months_range'], (n, 1)) * total_out
    cash_after_change = buffer + np.cumsum((receipts - expenses - service)[:, change:], axis=1)
    expected = -1 if name in ('deterioration', 'abrupt_deterioration') else 1 if name in ('improvement', 'recovery') else 0
    return bank, {'change': change, 'expected_direction': expected, 'cash_after_change': cash_after_change}


def eligible_history(bank, scores, minimum_quality=.8):
    activity = ((bank['receipts'] + bank['expenses'] + bank['debt_service']) > 0) & (bank['quality'] > 0)
    history = np.zeros_like(activity)
    for month in range(5, activity.shape[1]):
        history[:, month] = activity[:, month - 5:month + 1].all(axis=1)
    return history & ~scores['is_prior'] & (scores['bank_quality'] >= minimum_quality)


def episode_entries(signals):
    previous = np.column_stack((np.zeros(signals.shape[0], dtype=signals.dtype), signals[:, :-1]))
    return np.where((signals != 0) & (signals != previous), signals, 0)


def metric_summary(events, eligible, oracle):
    n, months = events.shape
    change = oracle['change']
    negative = events < 0
    positive = events > 0
    exposure_years = eligible.sum() / 12
    report = {'companies': n, 'eligible_company_years': float(exposure_years),
              'adverse_alerts_per_company_year': float(negative.sum() / exposure_years) if exposure_years else None,
              'all_alerts_per_company_year': float((negative | positive).sum() / exposure_years) if exposure_years else None,
              'pre_change_alert_fraction': float(np.mean(np.any(events[:, :change] != 0, axis=1))),
              'false_adverse_path_fraction': None, 'false_any_path_fraction': None}
    direction = oracle['expected_direction']
    if direction == 0:
        report.update(false_adverse_path_fraction=float(np.mean(negative.any(axis=1))),
                      false_any_path_fraction=float(np.mean((events != 0).any(axis=1))))
        return report
    matched = events[:, change:] == direction
    detected = matched.any(axis=1)
    first = np.where(detected, matched.argmax(axis=1), months)
    within_six = detected & (first < 6)
    report.update(detection_within_6_months=float(within_six.mean()), detection_within_horizon=float(detected.mean()),
                  median_delay_months=float(np.median(first[detected])) if detected.any() else None,
                  mean_delay_capped_6=float(np.minimum(first, 6).mean()))
    if direction < 0:
        lost = oracle['cash_after_change'] <= 0
        collapsed = lost.any(axis=1)
        cash_event = np.where(collapsed, lost.argmax(axis=1), months)
        paired = collapsed & detected
        lead = cash_event[paired] - first[paired]
        report.update(cash_collapses=int(collapsed.sum()), cash_paths_censored=int((~collapsed).sum()),
                      detected_before_cash_loss=int(np.sum(paired & (first < cash_event))),
                      fraction_collapses_warned_3_months=float(np.mean((detected & (cash_event - first >= 3))[collapsed])) if collapsed.any() else None,
                      median_lead_months_including_late=float(np.median(lead)) if len(lead) else None,
                      lead_months_p10=float(np.quantile(lead, .1)) if len(lead) else None)
    return report


def evaluate_simple_momentum(seed, protocol):
    result = {}
    threshold = protocol['monitor_candidates']['momentum_threshold']
    for scenario in protocol['synthetic']['scenarios']:
        bank, oracle = generate_scenario(scenario, seed, protocol)
        scores = calculate_scores(bank)
        eligible = eligible_history(bank, scores, protocol['monitor_candidates']['minimum_quality'])
        signals = np.where(scores['momentum'] > threshold, 1, np.where(scores['momentum'] < -threshold, -1, 0))
        signals = np.where(eligible, signals, 0)
        result[scenario] = metric_summary(episode_entries(signals), eligible, oracle)
    return result


def evaluate_monitor(seed, protocol, config):
    result = {}
    for scenario in protocol['synthetic']['scenarios']:
        bank, oracle = generate_scenario(scenario, seed, protocol)
        scores = calculate_scores(bank)
        states = classify_states(scores, config)
        events = directional_event_matrix(states)
        metrics = metric_summary(events, states['state_eligible'], oracle)
        if oracle['expected_direction'] < 0:
            matches = events[:, oracle['change']:] < 0
            detected = matches.any(axis=1)
            indices = matches.argmax(axis=1) + oracle['change']
            levels = scores['base_health'][np.arange(len(indices)), indices]
            metrics['fraction_detected_while_base_at_least_60'] = float(np.mean(levels[detected] >= 60)) if detected.any() else None
        if scenario == 'seasonal':
            eligible = states['state_eligible'] & states['seasonality_available']
            years = eligible.sum() / 12
            metrics['adverse_alerts_per_year_when_annual_context_available'] = float(((events < 0) & eligible).sum() / years) if years else None
        result[scenario] = metrics
    return result


def operational_cash_control(config):
    receipts = np.r_[np.full(12, 120.0), np.maximum(120 - 10 * np.arange(1, 25), 5)][None, :]
    bank = {'receipts': receipts, 'gross_receipts': receipts.copy(), 'refunds': np.zeros_like(receipts),
            'expenses': np.full_like(receipts, 100), 'debt_service': np.full_like(receipts, 5),
            'quality': np.ones_like(receipts), 'funding_gap': np.zeros_like(receipts)}
    scores = calculate_scores(bank)
    events = directional_event_matrix(classify_states(scores, config))
    cash = 300 + np.cumsum(receipts - 105, axis=1)
    collapse = int(np.flatnonzero(cash[0] <= 0)[0])
    alerts = np.flatnonzero(events[0, 12:] < 0) + 12
    first = int(alerts[0]) if len(alerts) else None
    return {'synthetic': True, 'opening_cash': 300, 'cash_not_used_as_a_feature': True,
            'first_confirmed_alert_month_index': first, 'cash_nonpositive_month_index': collapse,
            'lead_months': collapse - first if first is not None else None,
            'monotone_score_until_cash_loss': bool(np.all(np.diff(scores['score'][0, 12:collapse + 1]) <= 1e-10))}


def candidate_admissible(metrics):
    checks = ((metrics['stable']['adverse_alerts_per_company_year'], 1),
              (metrics['seasonal']['adverse_alerts_per_company_year'], 1),
              (metrics['pulse']['false_adverse_path_fraction'], .05))
    return all(value is not None and value <= limit for value, limit in checks)


def calibrate_monitor(protocol):
    candidates = []
    fixed = {key: value for key, value in protocol['monitor_candidates'].items() if key != 'persistence_months'}
    for persistence in protocol['monitor_candidates']['persistence_months']:
        config = StateConfig(persistence_months=persistence, **fixed)
        metrics = evaluate_monitor(protocol['synthetic']['development_seed'], protocol, config)
        delay = float(np.mean([metrics[name]['mean_delay_capped_6'] for name in ('deterioration', 'improvement', 'recovery')]))
        candidates.append({'config': asdict(config), 'admissible': candidate_admissible(metrics), 'selection_loss': delay, 'metrics': metrics})
    acceptable = [row for row in candidates if row['admissible']]
    chosen = min(acceptable, key=lambda row: row['selection_loss']) if acceptable else None
    result = {'candidates': candidates, 'selected': chosen['config'] if chosen else None,
              'selection_data': 'synthetic_development_only', 'protocol_sha256': sha256(HERE / 'trajectory_protocol.json'),
              'source_sha256': behavior_sources()}
    atomic_json(HERE / 'behavior_results' / 'calibration.json', result)
    if chosen:
        atomic_json(HERE / 'state_config.json', chosen['config'])
    return result


def rank_association(x, y):
    if len(x) < 3 or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
        return None
    return float(spearmanr(x, y).statistic)


def signal_metrics(predicted, target):
    hits = int((predicted & target).sum())
    return {'signals': int(predicted.sum()), 'proxy_events': int(target.sum()), 'true_positive_proxy': hits,
            'precision_on_proxy': hits / int(predicted.sum()) if predicted.any() else None,
            'recall_on_proxy': hits / int(target.sum()) if target.any() else None,
            'false_positive_rate_on_proxy_nonevents': float(np.mean(predicted[~target])) if (~target).any() else None}


def grouped_rank_intervals(rows, repetitions=300):
    groups = np.array([row['group_id'] for row in rows])
    unique = np.unique(groups)
    if len(unique) < 5:
        return {'groups': len(unique), 'intervals': None}
    values = {key: np.array([row[key] for row in rows]) for key in ('score', 'q3', 'q6', 'future_q')}
    rng = np.random.default_rng(1909)
    samples = {key: [] for key in ('score', 'q3', 'q6', 'score_minus_q3', 'score_minus_q6')}
    positions = {group: np.flatnonzero(groups == group) for group in unique}
    for _ in range(repetitions):
        selected = np.concatenate([positions[group] for group in rng.choice(unique, size=len(unique), replace=True)])
        correlations = {key: rank_association(values[key][selected], values['future_q'][selected]) for key in ('score', 'q3', 'q6')}
        if any(value is None for value in correlations.values()):
            continue
        for key, value in correlations.items():
            samples[key].append(value)
        for key in ('q3', 'q6'):
            samples[f'score_minus_{key}'].append(correlations['score'] - correlations[key])
    return {'groups': len(unique), 'bootstrap_repetitions': repetitions,
            'intervals': {key: np.quantile(values, [.025, .975]).tolist() if values else None for key, values in samples.items()}}


def evaluate_real_holdout(dataset, protocol, config):
    companies, edges, bank, audit = load_bank_panel(Path(dataset))
    scores = calculate_scores(bank)
    states = classify_states(scores, config)
    settings = protocol['real_data']
    groups = np.array([row['group_id'] for row in companies])
    selected_groups = np.random.default_rng(settings['held_out_group_seed']).permutation(np.unique(groups))
    start, stop = settings['held_out_group_positions']
    selected_groups = selected_groups[start:stop]
    held = np.isin(groups, selected_groups)
    independent = calculate_scores({key: values[held] for key, values in bank.items()})
    batch_difference = max(float(np.max(np.abs(independent[key].astype(float) - scores[key][held].astype(float)))) for key in scores)
    records = []
    horizon = settings['future_horizon_months']
    for cutoff in settings['cutoff_indices']:
        quarters = (slice(cutoff - 2, cutoff + 1), slice(cutoff - 5, cutoff - 2), slice(cutoff + 1, cutoff + 1 + horizon))
        measures = []
        sufficient = held.copy()
        for window in quarters:
            receipts = bank['receipts'][:, window].sum(axis=1)
            expenses = bank['expenses'][:, window].sum(axis=1) + bank['debt_service'][:, window].sum(axis=1)
            ratio = divide(receipts, receipts + expenses)
            measures.append(ratio)
            sufficient &= np.isfinite(ratio) & (bank['quality'][:, window].mean(axis=1) >= config.minimum_quality)
        q3, previous_q3, future_q = measures
        r6 = bank['receipts'][:, cutoff - 5:cutoff + 1].sum(axis=1)
        total6 = r6 + bank['expenses'][:, cutoff - 5:cutoff + 1].sum(axis=1) + bank['debt_service'][:, cutoff - 5:cutoff + 1].sum(axis=1)
        q6 = divide(r6, total6)
        for i in np.flatnonzero(sufficient):
            records.append({'company_id': companies[i]['company_id'], 'group_id': companies[i]['group_id'],
                            'as_of': edges[cutoff + 1].isoformat(), 'score': float(scores['score'][i, cutoff]),
                            'momentum': float(scores['momentum'][i, cutoff]), 'q3': float(q3[i]), 'q6': float(q6[i]),
                            'past_change': float(q3[i] - previous_q3[i]), 'future_q': float(future_q[i]),
                            'future_change': float(future_q[i] - q3[i]), 'state': str(states['state'][i, cutoff]),
                            'monitor_eligible': bool(states['state_eligible'][i, cutoff])})
    result = {'held_out_groups': selected_groups.tolist(), 'held_out_companies': int(held.sum()),
              'usable_company_cutoffs': len(records), 'test_rows': records, 'native_currency_only': True,
              'technical_generalization_max_batch_difference': batch_difference,
              'protocol_sha256': sha256(HERE / 'trajectory_protocol.json'),
              'financial_health_generalization_validated': False, 'empirical_cash_collapse_lead_validated': False,
              'target_is_auxiliary_flow_proxy_not_health_label': True, 'dataset_previously_explored': True,
              'audit': audit, 'monitor_config': asdict(config), 'source_sha256': behavior_sources()}
    if not records:
        result['status'] = 'insufficient_qualified_holdout_data'
        return result
    values = {key: np.array([row[key] for row in records]) for key in ('score', 'momentum', 'q3', 'q6', 'past_change', 'future_q', 'future_change')}
    labels = np.array([row['state'] for row in records])
    deadband = settings['direction_deadband']
    result.update(status='evaluated_auxiliary_proxy', observed_companies=len({row['company_id'] for row in records}),
                  observed_groups=len({row['group_id'] for row in records}),
                  monitor_eligible_observations=sum(row['monitor_eligible'] for row in records),
                  future_coverage_spearman={key: rank_association(values[key], values['future_q']) for key in ('score', 'q3', 'q6')},
                  future_change_spearman={key: rank_association(values[key], values['future_change']) for key in ('momentum', 'past_change')},
                  deterioration=signal_metrics(np.isin(labels, ['TORCIENDOSE', 'DETERIORO']), values['future_change'] <= -deadband),
                  improvement=signal_metrics(np.isin(labels, ['MEJORANDO', 'RECUPERACION']), values['future_change'] >= deadband),
                  grouped_intervals=grouped_rank_intervals(records))
    return result


def behavior_sources():
    return {name: sha256(HERE / name) for name in ('score_engine.py', 'score_states.py', 'score_monitor.py', 'behavior_benchmark.py')}


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--baseline', action='store_true')
    mode.add_argument('--calibrate', action='store_true')
    mode.add_argument('--evaluate', action='store_true')
    mode.add_argument('--real-data', action='store_true')
    parser.add_argument('--dataset', type=Path, default=HERE.parent / 'dataset')
    args = parser.parse_args()
    protocol = load_protocol()
    if args.baseline:
        result = {'model': 'simple_momentum_reference_not_an_existing_monitor',
                  'engine_sha256': sha256(HERE / 'score_engine.py'), 'protocol_sha256': sha256(HERE / 'trajectory_protocol.json'),
                  'seed': protocol['synthetic']['development_seed'],
                  'metrics': evaluate_simple_momentum(protocol['synthetic']['development_seed'], protocol),
                  'real_financial_health_validated': False}
        path = HERE / 'behavior_results' / 'baseline.json'
        if path.exists():
            parser.error('The pre-change baseline is already recorded; refusing to overwrite it.')
        atomic_json(path, result)
    elif args.calibrate:
        result = calibrate_monitor(protocol)
        if result['selected'] is None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            raise SystemExit('No candidate passed the preregistered development controls.')
    else:
        with (HERE / 'state_config.json').open(encoding='utf-8') as source:
            config = StateConfig(**json.load(source))
        with (HERE / 'behavior_results' / 'calibration.json').open(encoding='utf-8') as source:
            calibration = json.load(source)
        if (asdict(config) != calibration['selected'] or calibration['protocol_sha256'] != sha256(HERE / 'trajectory_protocol.json')
                or any(sha256(HERE / name) != value for name, value in calibration['source_sha256'].items())):
            raise SystemExit('Detector differs from the frozen calibration; review before evaluating held-out data.')
        if args.real_data:
            result = evaluate_real_holdout(args.dataset, protocol, config)
            atomic_json(HERE / 'behavior_results' / 'real_holdout.json', result)
        else:
            result = {'config': asdict(config), 'validation': evaluate_monitor(protocol['synthetic']['validation_seed'], protocol, config),
                      'test': evaluate_monitor(protocol['synthetic']['test_seed'], protocol, config),
                      'real_financial_health_validated': False, 'real_cash_anticipation_validated': False,
                      'operational_cash_control': operational_cash_control(config),
                      'protocol_sha256': sha256(HERE / 'trajectory_protocol.json'), 'source_sha256': behavior_sources()}
            result['test_controls_pass'] = candidate_admissible(result['test'])
            result['bidirectional_recall_gap'] = abs(result['test']['deterioration']['detection_within_6_months'] - result['test']['improvement']['detection_within_6_months'])
            atomic_json(HERE / 'behavior_results' / 'synthetic_validation.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'test_rows'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
