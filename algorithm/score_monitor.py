import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithm.score_data import sha256
from algorithm.score_states import NEGATIVE_STATES, POSITIVE_STATES, PENDING


POINTS = ('liquidity_points', 'collections_points', 'debt_points', 'momentum_points', 'growth_points', 'fragility_points', 'clipping_points')
ROOT = Path(__file__).resolve().parents[1]


class SnapshotNotReady(RuntimeError):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix=f'.{path.name}.', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def directional_event_matrix(panels):
    states = panels['state']
    previous = np.column_stack((np.full(states.shape[0], PENDING), states[:, :-1]))
    negative = np.isin(states, NEGATIVE_STATES)
    positive = np.isin(states, POSITIVE_STATES)
    negative_entry = negative & (~np.isin(previous, NEGATIVE_STATES) | ((previous == 'TORCIENDOSE') & (states == 'DETERIORO')))
    positive_entry = positive & ~np.isin(previous, POSITIVE_STATES)
    return np.where(panels['state_eligible'], np.where(negative_entry, -1, np.where(positive_entry, 1, 0)), 0)


def make_alert(panels, company, month, model_version):
    state = str(panels['state'][company, month])
    base_month = max(0, month - 3)
    contributions = {key: float(panels[key][company, month] - panels[key][company, base_month]) for key in POINTS}
    delta = float(panels['score'][company, month] - panels['score'][company, base_month])
    if not np.isclose(delta, sum(contributions.values()), atol=1e-8, rtol=0):
        raise ValueError('Alert contribution deltas do not reconcile with the score change')
    identity = {'company_id': str(panels['company_id'][company]), 'as_of': str(panels['as_of'][month]),
                'state': state, 'model_version': model_version}
    alert_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    drivers = [{'field': key, 'delta_points': value, 'unit': 'score_points'}
               for key, value in sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True) if abs(value) > 1e-10][:2]
    changed_evidence = any(bool(panels[key][company, month]) != bool(panels[key][company, base_month]) for key in ('erp_used', 'cash_used'))
    return dict(identity, alert_id=alert_id, group_id=str(panels['group_id'][company]),
                severity='ALTA' if state == 'DETERIORO' else 'MEDIA' if state == 'TORCIENDOSE' else 'INFORMATIVA',
                direction='deterioration' if state in NEGATIVE_STATES else 'improvement',
                score=float(panels['score'][company, month]), base_health=float(panels['base_health'][company, month]),
                momentum=float(panels['momentum'][company, month]), delta_score=delta,
                comparison_as_of=str(panels['as_of'][base_month]), drivers=drivers, contribution_deltas=contributions,
                state_quality=float(panels['state_quality'][company, month]), evidence_changed=changed_evidence,
                seasonality_available=bool(panels['seasonality_available'][company, month]),
                annual_pattern_match=bool(panels['annual_pattern_match'][company, month]),
                trajectory_basis='observed_bank_core', lead_months=None, reference_event_as_of=None,
                delivery_mode='historical_replay')


def build_alert_history(panels, model_version):
    events = directional_event_matrix(panels)
    result = [make_alert(panels, int(company), int(month), model_version) for company, month in zip(*np.nonzero(events))]
    return sorted(result, key=lambda row: (row['as_of'], row['company_id'], row['state']))


def read_json(path, default):
    if not path.exists():
        return default
    with path.open(encoding='utf-8') as source:
        return json.load(source)


def load_completed_snapshot(folder):
    manifest_path = folder / 'score_manifest.json'
    fingerprint = sha256(manifest_path)
    manifest = read_json(manifest_path, None)
    panels_path = folder / 'score_panels.npz'
    if not manifest or manifest.get('panels_sha256') != sha256(panels_path):
        raise SnapshotNotReady('Scoring snapshot is not fully published; waiting for a consistent manifest.')
    with np.load(panels_path, allow_pickle=False) as stored:
        panels = dict(stored)
    if fingerprint != sha256(manifest_path) or manifest['panels_sha256'] != sha256(panels_path):
        raise SnapshotNotReady('Manifest or panels changed during snapshot reading.')
    required = ('state', 'state_eligible', 'state_quality', 'seasonality_available', 'annual_pattern_match',
                'company_id', 'group_id', 'as_of', *POINTS)
    missing = [key for key in required if key not in panels]
    if missing:
        raise SnapshotNotReady(f'Snapshot lacks monitor fields {missing}; rerun calc_score.')
    return manifest, panels, fingerprint


def monitor_once(results):
    results = Path(results)
    state_path = results / 'monitor_state.json'
    state = read_json(state_path, {})
    fingerprint = sha256(results / 'score_manifest.json')
    if state.get('snapshot_fingerprint') == fingerprint:
        return {'status': 'unchanged', 'new_alerts': []}
    manifest, panels, fingerprint = load_completed_snapshot(results)
    model_version = manifest['model_version']
    history = build_alert_history(panels, model_version)
    atomic_json(results / 'alerts_history.json', {'mode': 'retrospective_analysis', 'model_version': model_version, 'alerts': history})
    feed = read_json(results / 'alerts_feed.json', {'alerts': []})
    seen = {row['alert_id'] for row in feed['alerts']}
    cursors = state.get('companies', {})
    changed_model = bool(state) and state.get('model_version') != model_version
    new = []
    latest = str(panels['as_of'][-1])
    watermark = max((row['as_of'] for row in cursors.values()), default='')
    if state and latest < watermark:
        atomic_json(state_path, dict(state, snapshot_fingerprint=fingerprint))
        return {'status': 'older_snapshot', 'new_alerts': [], 'snapshot_as_of': latest}
    index = {str(company_id): i for i, company_id in enumerate(panels['company_id'])}
    if not changed_model:
        for event in history:
            previous = cursors.get(event['company_id'])
            if previous and event['as_of'] > previous['as_of']:
                new.append(dict(event, delivery_mode='new_snapshot'))
        for company_id, i in index.items():
            previous = cursors.get(company_id)
            current_state = str(panels['state'][i, -1])
            if not panels['state_eligible'][i, -1] or current_state not in NEGATIVE_STATES + POSITIVE_STATES:
                continue
            if previous is None:
                new.append(dict(make_alert(panels, i, panels['score'].shape[1] - 1, model_version), delivery_mode='initial_snapshot'))
            elif latest == previous['as_of'] and current_state != previous['state']:
                alert = make_alert(panels, i, panels['score'].shape[1] - 1, model_version)
                revision = json.dumps([alert['alert_id'], alert['score'], alert['contribution_deltas']], sort_keys=True)
                alert.update(alert_id=hashlib.sha256(revision.encode()).hexdigest(), delivery_mode='data_revision')
                new.append(alert)
    emitted = []
    for event in sorted(new, key=lambda row: (row['as_of'], row['company_id'], row['state'])):
        if event['alert_id'] not in seen:
            emitted.append(event)
            seen.add(event['alert_id'])
    for company_id, i in index.items():
        previous = cursors.get(company_id)
        if changed_model or previous is None or latest >= previous['as_of']:
            cursors[company_id] = {'as_of': latest, 'state': str(panels['state'][i, -1])}
    atomic_json(results / 'alerts_feed.json', {'alerts': feed['alerts'] + emitted})
    atomic_json(state_path, {'model_version': model_version, 'snapshot_fingerprint': fingerprint, 'companies': cursors})
    return {'status': 'model_rebaseline' if changed_model else 'processed', 'new_alerts': emitted,
            'history_alerts': len(history), 'current_as_of': latest}


def main():
    parser = argparse.ArgumentParser(description='Local proactive monitor for completed scoring snapshots; can broadcast to Telegram and email.')
    parser.add_argument('--results', type=Path, default=ROOT / 'algorithm' / 'engine_results')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=float, default=2.0)
    parser.add_argument('--telegram', action='store_true', help='Broadcast new alerts to registered Telegram subscribers')
    parser.add_argument('--email', action='store_true', help='Send deterioration alerts by email to the affected company (Mailpit in local)')
    args = parser.parse_args()
    if not np.isfinite(args.interval) or args.interval <= 0:
        parser.error('interval must be finite and positive')
    previous_error = None
    try:
        while True:
            try:
                result = monitor_once(args.results)
                if result['status'] != 'unchanged':
                    print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
                    if args.telegram and result.get('new_alerts'):
                        try:
                            from algorithm.telegram_notifier import broadcast_alert
                            for alert in result['new_alerts']:
                                broadcast_alert(alert)
                        except Exception as tg_err:
                            print(f"[Telegram error] {tg_err}", file=sys.stderr, flush=True)
                    if args.email and result.get('new_alerts'):
                        try:
                            from algorithm.email_notifier import broadcast_alert as email_alert
                            for alert in result['new_alerts']:
                                outcome = email_alert(alert)
                                if outcome.get('sent') or outcome.get('failed'):
                                    print(json.dumps({'email': outcome}, ensure_ascii=False), flush=True)
                        except Exception as mail_err:
                            print(f"[Email error] {mail_err}", file=sys.stderr, flush=True)
                previous_error = None
            except (FileNotFoundError, json.JSONDecodeError, zipfile.BadZipFile, SnapshotNotReady) as error:
                if not args.watch:
                    raise
                message = str(error)
                if message != previous_error:
                    print(message, file=sys.stderr, flush=True)
                previous_error = message
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
