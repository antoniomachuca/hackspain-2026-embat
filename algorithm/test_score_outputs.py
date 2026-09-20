import csv
import json
import unittest
from pathlib import Path

import numpy as np

from algorithm.render_score_report import render
from algorithm.score_data import sha256
from algorithm.validate_score import POINTS


HERE = Path(__file__).resolve().parent


@unittest.skipUnless((HERE / 'engine_results' / 'score_panels.npz').exists(), 'Run calc_score and validation before artifact verification.')
class ExportedScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = []
        for folder in (HERE / 'engine_results', HERE / 'engine_results_erp'):
            with np.load(folder / 'score_panels.npz', allow_pickle=False) as stored:
                panels = dict(stored)
            with (folder / 'score_manifest.json').open() as source:
                manifest = json.load(source)
            with (folder / 'validation.json').open() as source:
                validation = json.load(source)
            cls.results.append((panels, manifest, validation))

    def test_artifacts_match_current_source_and_every_gate_passes(self):
        for panels, manifest, validation in self.results:
            self.assertEqual(manifest['engine_sha256'], sha256(HERE / 'score_engine.py'))
            self.assertEqual(manifest['data_adapter_sha256'], sha256(HERE / 'score_data.py'))
            self.assertTrue(validation['all_gates_pass'], validation['gates'])
            self.assertEqual(panels['score'].shape, (manifest['companies'], manifest['months']))
            np.testing.assert_allclose(panels['score'], sum(panels[key] for key in POINTS), atol=1e-10, rtol=0)
            np.testing.assert_allclose(panels['score'][panels['is_prior']], 50)

    def test_actual_erp_snapshot_has_no_effect_on_earlier_scores(self):
        core, enriched = self.results[0][0], self.results[1][0]
        no_erp = ~enriched['erp_used']
        np.testing.assert_array_equal(core['score'][no_erp], enriched['score'][no_erp])
        self.assertGreater(enriched['erp_used'].sum(), 0)

    def test_csv_rows_and_point_contributions_match_numpy_export(self):
        panels = self.results[0][0]
        count = 0
        with (HERE / 'engine_results' / 'scores_monthly.csv').open(newline='') as source:
            for row in csv.DictReader(source):
                company, month = divmod(count, panels['score'].shape[1])
                self.assertEqual(row['company_id'], panels['company_id'][company])
                self.assertEqual(row['as_of'], panels['as_of'][month])
                self.assertAlmostEqual(float(row['score']), panels['score'][company, month], places=10)
                self.assertAlmostEqual(float(row['score']), sum(float(row[key]) for key in POINTS), places=10)
                count += 1
        self.assertEqual(count, panels['score'].size)

    def test_document_tables_are_generated_from_the_measured_results(self):
        core, enriched = self.results
        expected = render(core[2], enriched[2], core[1], enriched[1])
        actual = (HERE / 'formula' / 'engine_benchmark_results.tex').read_text(encoding='utf-8')
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
