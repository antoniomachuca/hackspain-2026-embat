import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import numpy as np

from algorythm.score_data import month_edges, sha256
from algorythm.score_monitor import SnapshotNotReady, build_alert_history, load_completed_snapshot, monitor_once
from algorythm.score_states import StateConfig, classify_states
from algorythm.test_score_states import state_fixture


def monitor_fixture(months=24):
    scores = state_fixture(months=months)
    scores['momentum'][:, 12:] = -.3
    scores['monthly_flow_margin'][:, 12:] = -.1
    scores['score'] = np.clip(scores['base_health'] + 8 * scores['momentum'], 0, 100)
    for name, weight in (('liquidity_points', .5), ('collections_points', .3), ('debt_points', .2)):
        scores[name] = weight * scores['base_health']
    scores['momentum_points'] = 8 * scores['momentum']
    for key in ('growth_points', 'fragility_points', 'clipping_points'):
        scores[key] = np.zeros_like(scores['score'])
    scores.update(classify_states(scores))
    scores.update(company_id=np.array(['C1']), group_id=np.array(['G1']),
                  as_of=np.array([day.isoformat() for day in month_edges('2024-09-01', '2026-09-01')[1:]][:months]))
    return scores


def write_snapshot(folder, panels, version='v1'):
    folder.mkdir(exist_ok=True)
    np.savez_compressed(folder / 'score_panels.npz', **panels)
    manifest = {'model_version': version, 'state_config': asdict(StateConfig()), 'panels_sha256': sha256(folder / 'score_panels.npz')}
    (folder / 'score_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


class MonitorTests(unittest.TestCase):
    def test_alerts_have_exact_drivers_and_no_invented_lead_time(self):
        events = build_alert_history(monitor_fixture(), 'model')
        self.assertTrue(events)
        for event in events:
            self.assertIsNone(event['lead_months'])
            self.assertAlmostEqual(event['delta_score'], sum(event['contribution_deltas'].values()), places=10)
            self.assertLessEqual(len(event['drivers']), 2)
            self.assertGreaterEqual(event['as_of'], '2025-12-01')

    def test_reprocessing_identical_snapshot_does_not_duplicate_alerts(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture())
            first = monitor_once(directory)
            second = monitor_once(directory)
            self.assertEqual(len(first['new_alerts']), 1)
            self.assertEqual(second['new_alerts'], [])
            feed = json.loads((directory / 'alerts_feed.json').read_text())
            self.assertEqual(len(feed['alerts']), 1)

    def test_a_new_score_snapshot_triggers_alert_without_a_company_query(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture(14))
            self.assertEqual(monitor_once(directory)['new_alerts'], [])
            write_snapshot(directory, monitor_fixture(15))
            events = monitor_once(directory)['new_alerts']
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['state'], 'TORCIENDOSE')
            self.assertEqual(events[0]['delivery_mode'], 'new_snapshot')

    def test_model_change_rebaselines_without_claiming_financial_change(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture(), 'v1')
            monitor_once(directory)
            write_snapshot(directory, monitor_fixture(), 'v2')
            result = monitor_once(directory)
            self.assertEqual(result['status'], 'model_rebaseline')
            self.assertEqual(result['new_alerts'], [])

    def test_older_time_machine_snapshot_does_not_move_live_cursor_backwards(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture())
            monitor_once(directory)
            write_snapshot(directory, monitor_fixture(12))
            self.assertEqual(monitor_once(directory)['new_alerts'], [])
            state = json.loads((directory / 'monitor_state.json').read_text())
            self.assertEqual(state['companies']['C1']['as_of'], '2026-09-01')

    def test_same_cutoff_revision_is_marked_and_delivered_once(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            panels = monitor_fixture()
            write_snapshot(directory, panels)
            monitor_once(directory)
            panels['base_health'][:, -1] = 50
            panels['score'][:, -1] = 50 + panels['momentum_points'][:, -1]
            for key, weight in (('liquidity_points', .5), ('collections_points', .3), ('debt_points', .2)):
                panels[key][:, -1] = 50 * weight
            panels.update(classify_states(panels))
            write_snapshot(directory, panels)
            events = monitor_once(directory)['new_alerts']
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['delivery_mode'], 'data_revision')
            self.assertEqual(events[0]['state'], 'DETERIORO')
            self.assertEqual(monitor_once(directory)['new_alerts'], [])

    def test_model_change_on_old_snapshot_cannot_rewind_live_cursor(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture(), 'v1')
            monitor_once(directory)
            write_snapshot(directory, monitor_fixture(12), 'v2')
            self.assertEqual(monitor_once(directory)['new_alerts'], [])
            state = json.loads((directory / 'monitor_state.json').read_text())
            self.assertEqual(state['companies']['C1']['as_of'], '2026-09-01')
            write_snapshot(directory, monitor_fixture(), 'v2')
            self.assertEqual(monitor_once(directory)['new_alerts'], [])

    def test_panel_replaced_during_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture())
            manifest_hash = sha256(directory / 'score_manifest.json')
            panel_hash = sha256(directory / 'score_panels.npz')
            with patch('algorythm.score_monitor.sha256', side_effect=[manifest_hash, panel_hash, manifest_hash, 'replacement']):
                with self.assertRaises(SnapshotNotReady):
                    load_completed_snapshot(directory)

    def test_incomplete_publication_is_not_consumed(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_snapshot(directory, monitor_fixture())
            manifest = json.loads((directory / 'score_manifest.json').read_text())
            manifest['panels_sha256'] = 'not-the-current-panel'
            (directory / 'score_manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(SnapshotNotReady):
                monitor_once(directory)


if __name__ == '__main__':
    unittest.main()
