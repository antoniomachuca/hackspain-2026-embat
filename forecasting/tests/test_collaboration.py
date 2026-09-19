import json

import numpy as np
import pytest

from forecasting.data import Samples
from forecasting.experiment import blind, evaluate, load_frozen_stress, paired_group_bootstrap
from forecasting.registry import digest, generate_leaderboard


def test_inference_never_receives_future_labels():
    samples = Samples(np.ones((4, 24)), np.array([40., 50., 60., 55.]), np.full(4, 50.),
                      np.full(4, 50.), np.array(['a', 'b', 'c', 'd']), np.array(['g', 'g', 'h', 'h']),
                      np.full(4, 17), np.full(4, 20))

    class Model:
        def predict(self, s):
            assert np.isnan(s.y).all()
            s.x[:] = 999  # Must not mutate the shared feature table.
            return np.tile([30., 50., 70.], (len(s.y), 1))

        def direction_probabilities(self, s):
            assert np.isnan(s.y).all()
            return np.tile([.3, .4, .3], (len(s.y), 1))

    result = evaluate(Model(), samples)
    assert result['mae'] == 6.25
    assert (samples.x == 1).all()
    np.testing.assert_array_equal(samples.y, [40, 50, 60, 55])
    assert np.isnan(blind(samples).y).all()


def report(mae=10, key='same', name='ridge', rank=4, paired=None):
    return {'run_id': name, 'comparison': {'key': key}, 'contribution': {
        'author': 'team', 'complexity_rank': rank, 'explanation_checked': True},
        'horizons': {str(h): {'validation': {name: {'macro_group_mae': mae, 'samples': 10, 'groups': 2,
            'interval_80_coverage': .8, 'balanced_direction_accuracy': .5}},
            'test': {name: {'macro_group_mae': 100/mae}},
            'paired_vs_baseline': paired or {},
            'partitions': {'validation': {'samples': 10, 'groups': 2}}} for h in (1, 3, 6)}}


def write_run(path, data):
    data['result_sha256'] = digest(data)
    path.write_text(json.dumps(data))


def test_leaderboard_validation_only_and_incompatible_runs_excluded(tmp_path):
    baseline = tmp_path/'baseline.json'
    baseline.write_text(json.dumps(report()))
    runs = tmp_path/'runs'
    runs.mkdir()
    write_run(runs/'good.json', report(8, name='new_model', rank=7))
    write_run(runs/'other_protocol.json', report(.01, key='different', name='incompatible'))
    winner = generate_leaderboard(baseline, runs, tmp_path/'LEADERBOARD.md')
    assert winner['3']['model'] == 'new_model'  # Despite worse test error.
    assert 'other_protocol.json' in (tmp_path/'LEADERBOARD.md').read_text()


def test_paired_group_bootstrap_constant_improvement():
    model = {'a': 1., 'b': 1., 'c': 1.}
    baseline = {'a': 2., 'b': 2., 'c': 2.}
    result = paired_group_bootstrap(model, baseline)
    assert result['delta_macro_group_mae'] == 1.
    assert result['ci95'] == [1., 1.]
    assert result['probability_better'] == 1.
    assert result['groups'] == 3


def test_leaderboard_shows_paired_delta(tmp_path):
    baseline = tmp_path/'baseline.json'
    baseline.write_text(json.dumps(report()))
    runs = tmp_path/'runs'
    runs.mkdir()
    paired = {'ridge': {'delta_macro_group_mae': .5, 'ci95': [.1, .9], 'probability_better': .99, 'groups': 2}}
    write_run(runs/'new.json', report(9, name='new_model', rank=7, paired=paired))
    generate_leaderboard(baseline, runs, tmp_path/'LEADERBOARD.md')
    table = (tmp_path/'LEADERBOARD.md').read_text()
    assert '+0.50 [+0.10, +0.90] ✓' in table
    assert 'Δ MAE vs ridge [IC 95%]' in table


def test_leaderboard_tolerance_prefers_simplicity(tmp_path):
    baseline = tmp_path/'baseline.json'
    baseline.write_text(json.dumps(report(10.1)))
    runs = tmp_path/'runs'
    runs.mkdir()
    write_run(runs/'complex.json', report(10, name='complex', rank=9))
    winner = generate_leaderboard(baseline, runs, tmp_path/'LEADERBOARD.md')
    assert winner['1']['model'] == 'ridge'


def test_tampered_benchmark_is_rejected(tmp_path):
    baseline = tmp_path/'baseline.json'
    baseline.write_text(json.dumps(report()))
    runs = tmp_path/'runs'
    runs.mkdir()
    data = report(8)
    write_run(runs/'run.json', data)
    data['horizons']['1']['validation']['ridge']['macro_group_mae'] = .01
    (runs/'run.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='modified'):
        generate_leaderboard(baseline, runs, tmp_path/'LEADERBOARD.md')


def test_changed_frozen_synthetic_data_is_rejected(tmp_path):
    (tmp_path/'MANIFEST.json').write_text(json.dumps({'files_sha256': {'control.npz': 'wrong-hash'}}))
    (tmp_path/'control.npz').write_bytes(b'changed')
    with pytest.raises(ValueError, match='Frozen stress dataset changed'):
        load_frozen_stress(tmp_path)
