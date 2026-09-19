import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import numpy as np

from algorythm.calc_score import main as calculate_main
from algorythm.score_data import add_cash_observations, load_erp_snapshot, month_edges, sha256


class PointInTimeDataTests(unittest.TestCase):
    def write_csv(self, path, records):
        with path.open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    def test_cash_recorded_after_cutoff_is_rejected(self):
        companies = [{'company_id': 'C', 'currency': 'EUR'}]
        bank = {'receipts': np.zeros((1, 3))}
        row = {'company_id': 'C', 'currency': 'EUR', 'as_of': '2024-10-01', 'observed_at': '2024-10-02', 'cash_balance': '100'}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cash.csv'
            self.write_csv(path, [row])
            with self.assertRaises(ValueError):
                add_cash_observations(bank, companies, month_edges('2024-09-01', '2024-12-01'), path)

    def test_cash_snapshot_does_not_fill_earlier_months(self):
        companies = [{'company_id': 'C', 'currency': 'EUR'}]
        bank = {'receipts': np.zeros((1, 3))}
        row = {'company_id': 'C', 'currency': 'EUR', 'as_of': '2024-12-01', 'observed_at': '2024-12-01', 'cash_balance': '100', 'commitments_30d': '50'}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cash.csv'
            self.write_csv(path, [row])
            add_cash_observations(bank, companies, month_edges('2024-09-01', '2024-12-01'), path)
        self.assertTrue(np.isnan(bank['cash_balance'][0, :2]).all())
        self.assertEqual(bank['cash_balance'][0, 2], 100)

    def test_missing_cash_observation_timestamp_is_rejected(self):
        companies = [{'company_id': 'C', 'currency': 'EUR'}]
        bank = {'receipts': np.zeros((1, 3))}
        row = {'company_id': 'C', 'currency': 'EUR', 'as_of': '2024-12-01', 'observed_at': '', 'cash_balance': '100'}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cash.csv'
            self.write_csv(path, [row])
            with self.assertRaises(ValueError):
                add_cash_observations(bank, companies, month_edges('2024-09-01', '2024-12-01'), path)

    def test_full_cli_scores_an_unseen_company_and_publishes_idempotent_alerts(self):
        with tempfile.TemporaryDirectory() as folder:
            dataset = Path(folder) / 'dataset'
            output = Path(folder) / 'results'
            dataset.mkdir()
            company = 'NEW_UNSEEN_COMPANY'
            self.write_csv(dataset / 'companies.csv', [{'company_id': company, 'group_id': 'NEW_GROUP', 'currency': 'EUR'}])
            self.write_csv(dataset / 'banking_products.csv', [{'product_id': 'NEW_BANK', 'company_id': company, 'currency': 'EUR'}])
            self.write_csv(dataset / 'debt_products.csv', [{'product_id': 'NEW_DEBT', 'company_id': company, 'currency': 'EUR'}])
            transactions = []
            for month, day in enumerate(month_edges()[:-1]):
                for category, amount in (('collection', 160 - 90 * month / 23), ('payment', -100), ('debt_repayment', -5)):
                    transactions.append({'company_id': company, 'product_id': 'NEW_BANK', 'date': day.isoformat(),
                                         'amount': amount, 'status': 'booked', 'category': category,
                                         'exchange_rate': 1, 'counterparty_id': 'CUSTOMER' if amount > 0 else ''})
            self.write_csv(dataset / 'transactions.csv', transactions)
            argv = ['calc_score', '--dataset', str(dataset), '--output', str(output)]
            with patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
                calculate_main()
            manifest = json.loads((output / 'score_manifest.json').read_text())
            self.assertEqual(manifest['companies'], 1)
            self.assertEqual(manifest['panels_sha256'], sha256(output / 'score_panels.npz'))
            self.assertEqual(manifest['csv_sha256'], sha256(output / 'scores_monthly.csv'))
            with (output / 'scores_monthly.csv').open(newline='') as source:
                records = list(csv.DictReader(source))
            self.assertEqual(len(records), 24)
            self.assertEqual(records[0]['state'], 'EVALUACION_PENDIENTE')
            self.assertEqual(records[-1]['state'], 'DETERIORO')
            feed = json.loads((output / 'alerts_feed.json').read_text())
            self.assertEqual(len(feed['alerts']), 1)
            self.assertIsNone(feed['alerts'][0]['lead_months'])
            with patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
                calculate_main()
            self.assertEqual(json.loads((output / 'alerts_feed.json').read_text()), feed)

    def test_erp_snapshot_is_not_backdated_or_inferred_from_payment_date(self):
        companies = [{'company_id': 'WITH', 'currency': 'EUR'}, {'company_id': 'WITHOUT', 'currency': 'EUR'}]
        bank = {'receipts': np.full((2, 24), 200.0)}
        invoice = {'company_id': 'WITH', 'amount': '100', 'pending_amount': '20', 'document_type': 'invoice',
                   'issuance_date': '2026-07-01', 'due_date': '2026-07-31', 'payment_date': '2026-07-31',
                   'status': 'pending', 'currency': 'EUR', 'accounting_currency': 'EUR', 'exchange_rate': '1', 'counterparty_id': 'CUSTOMER'}
        with tempfile.TemporaryDirectory() as folder:
            self.write_csv(Path(folder) / 'invoices.csv', [invoice.copy() for _ in range(6)])
            erp, audit = load_erp_snapshot(Path(folder), companies, month_edges(), bank)
        np.testing.assert_allclose(erp['quality'][:, :-1], 0)
        self.assertEqual(erp['quality'][1, -1], 0)
        self.assertGreater(erp['quality'][0, -1], 0)
        self.assertAlmostEqual(erp['late_fraction'][0, -1], .2)
        self.assertAlmostEqual(erp['dso_days'][0, -1], 18.4)
        self.assertAlmostEqual(erp['conversion'][0, -1], .8)
        self.assertFalse(audit['payment_date_used_to_infer_payment'])


if __name__ == '__main__':
    unittest.main()
