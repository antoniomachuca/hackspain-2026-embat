import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from algorythm.score_data import add_cash_observations, load_erp_snapshot, month_edges


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
