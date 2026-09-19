import unittest

import numpy as np

from algorythm.score_engine import ScoreConfig, bounded_momentum, calculate_scores, hill


CONTRIBUTIONS = ('liquidity_points', 'collections_points', 'debt_points', 'momentum_points', 'growth_points', 'fragility_points', 'clipping_points')


def bank_fixture(receipts, expenses=100, debt=5):
    receipts = np.atleast_2d(np.asarray(receipts, dtype=float))
    return {'receipts': receipts, 'gross_receipts': receipts.copy(), 'refunds': np.zeros_like(receipts),
            'expenses': np.broadcast_to(expenses, receipts.shape).copy(), 'debt_service': np.broadcast_to(debt, receipts.shape).copy(),
            'quality': np.ones_like(receipts), 'funding_gap': np.zeros_like(receipts)}


class ScoreEngineContractTests(unittest.TestCase):
    def test_score_range_finiteness_and_exact_waterfall(self):
        rng = np.random.default_rng(17)
        bank = bank_fixture(rng.lognormal(5, 1, (50, 24)), rng.lognormal(5, 1, (50, 24)), rng.lognormal(2, 1, (50, 24)))
        output = calculate_scores(bank)
        for name, values in output.items():
            self.assertTrue(np.isfinite(values).all(), name)
        self.assertTrue(((output['score'] >= 0) & (output['score'] <= 100)).all())
        np.testing.assert_allclose(output['score'], sum(output[name] for name in CONTRIBUTIONS), atol=1e-12)
        np.testing.assert_allclose(np.diff(output['score']), sum(np.diff(output[name]) for name in CONTRIBUTIONS), atol=1e-12)

    def test_absent_erp_is_identical_to_zero_quality_erp(self):
        bank = bank_fixture([120] * 24)
        erp = {key: np.ones((1, 24)) for key in ('dso_days', 'late_fraction', 'conversion', 'sales_growth')}
        erp['quality'] = np.zeros((1, 24))
        np.testing.assert_array_equal(calculate_scores(bank)['score'], calculate_scores(bank, erp)['score'])

    def test_erp_availability_does_not_create_bank_momentum(self):
        bank = bank_fixture([120] * 24)
        erp = {'quality': np.zeros((1, 24)), 'dso_days': np.full((1, 24), 240.0), 'late_fraction': np.full((1, 24), .9)}
        erp['quality'][0, -1] = 1
        core, enriched = calculate_scores(bank), calculate_scores(bank, erp)
        np.testing.assert_array_equal(core['momentum'], enriched['momentum'])
        self.assertLess(enriched['collections_points'][0, -1], core['collections_points'][0, -1])

    def test_empty_bank_history_returns_marked_neutral_prior(self):
        bank = bank_fixture([0] * 24, expenses=0, debt=0)
        bank['quality'][:] = 0
        output = calculate_scores(bank)
        np.testing.assert_allclose(output['score'], 50)
        self.assertTrue(output['is_prior'].all())
        self.assertFalse(output['cash_known'].any())

    def test_connected_feed_without_any_activity_is_still_a_prior(self):
        output = calculate_scores(bank_fixture([0] * 24, expenses=0, debt=0))
        np.testing.assert_allclose(output['score'], 50)
        self.assertTrue(output['is_prior'].all())

    def test_verified_erp_growth_alone_is_marked_as_evidence(self):
        bank = bank_fixture([0] * 24, expenses=0, debt=0)
        bank['quality'][:] = 0
        erp = {'quality': np.ones((1, 24)), 'sales_growth': np.full((1, 24), .3), 'conversion': np.full((1, 24), .8)}
        output = calculate_scores(bank, erp)
        self.assertGreater(output['score'][0, -1], 50)
        self.assertFalse(output['is_prior'][0, -1])

    def test_observed_refunds_are_not_discarded_when_net_collections_are_zero(self):
        bank = bank_fixture([0] * 24)
        bank['gross_receipts'][:] = 100
        bank['refunds'][:] = 100
        self.assertLess(calculate_scores(bank)['C_bank'][0, -1], .5)

    def test_no_observed_debt_is_neutral_not_perfect_debt_health(self):
        self.assertAlmostEqual(calculate_scores(bank_fixture([120] * 24, debt=0))['D'][0, -1], .5)

    def test_more_debt_never_improves_debt_pillar(self):
        low = calculate_scores(bank_fixture([120] * 24, debt=5))
        high = calculate_scores(bank_fixture([120] * 24, debt=50))
        self.assertLess(high['D'][0, -1], low['D'][0, -1])

    def test_hhi_transform_does_not_collapse_at_sixty_percent(self):
        values = hill(np.array([.36, .5, .8, 1]), .25)
        self.assertTrue((np.diff(values) > 0).all())
        self.assertTrue((values < 1).all())

    def test_future_bank_and_erp_values_do_not_change_prefix(self):
        bank = bank_fixture(np.linspace(80, 140, 24))
        original = calculate_scores(bank)
        changed = {key: values.copy() for key, values in bank.items()}
        changed['receipts'][:, 18:] = 1
        changed['gross_receipts'][:, 18:] = 1
        cash = np.full((1, 24), np.nan)
        cash[:, 18:] = -1000
        changed['cash_balance'] = cash
        erp = {'quality': np.zeros((1, 24)), 'dso_days': np.full((1, 24), 300.0), 'late_fraction': np.ones((1, 24))}
        erp['quality'][:, 18:] = 1
        modified = calculate_scores(changed, erp)
        for name in original:
            np.testing.assert_allclose(original[name][:, :18], modified[name][:, :18], err_msg=name)

    def test_score_is_invariant_to_currency_unit_scale(self):
        bank = bank_fixture(np.linspace(80, 140, 24))
        bank['cash_balance'] = np.full((1, 24), 200.0)
        bank['commitments_30d'] = np.full((1, 24), 110.0)
        scaled = {key: values.copy() if key == 'quality' else values * 1000 for key, values in bank.items()}
        np.testing.assert_allclose(calculate_scores(bank)['score'], calculate_scores(scaled)['score'])

    def test_raw_momentum_rewards_opposite_paths_with_same_final_base(self):
        base = np.array([np.linspace(45, 65, 24), np.linspace(85, 65, 24)])
        output = bounded_momentum(base, base / 100, np.ones_like(base), ScoreConfig())
        self.assertGreater(output[0, -1], 0)
        self.assertLess(output[1, -1], 0)

    def test_single_month_cash_shock_does_not_activate_persistent_momentum(self):
        base = np.full((1, 24), 65.0)
        base[0, 12] = 30
        confirmation = np.full_like(base, .6)
        confirmation[0, 12] = .1
        np.testing.assert_allclose(bounded_momentum(base, confirmation, np.ones_like(base), ScoreConfig()), 0)

    def test_verified_cash_is_never_invented_when_absent(self):
        output = calculate_scores(bank_fixture([120] * 24))
        self.assertFalse(output['cash_known'].any())
        self.assertFalse(output['commitments_known'].any())

    def test_negative_financial_inputs_are_rejected(self):
        bank = bank_fixture([120] * 24)
        bank['expenses'][0, 10] = -1
        with self.assertRaises(ValueError):
            calculate_scores(bank)

    def test_control_has_monotone_decline_and_three_month_lead(self):
        from algorythm.validate_score import stress_control
        for name, case in stress_control()['variants'].items():
            self.assertTrue(case['monotone_from_shock_to_cash_loss'], name)
            self.assertIsNotNone(case['lead_months'], name)
            self.assertGreaterEqual(case['lead_months'], 3, name)

    def test_missing_financial_values_do_not_escape_as_nan(self):
        output = calculate_scores(bank_fixture([np.nan] * 24))
        np.testing.assert_allclose(output['score'], 50)
        self.assertTrue(output['is_prior'].all())

    def test_named_opposite_trajectories_overcome_similar_final_levels(self):
        base = np.array([np.linspace(45, 65, 24), np.linspace(82, 68, 24)])
        trend = bounded_momentum(base, 2 * base / 100 - 1, np.ones_like(base), ScoreConfig())
        self.assertGreater(65 + 8 * trend[0, -1], 68 + 8 * trend[1, -1])

    def test_clipping_is_exposed_as_an_exact_adjustment(self):
        output = calculate_scores(bank_fixture(np.linspace(30, 180, 24)), config=ScoreConfig(momentum_weight=500))
        self.assertTrue((output['clipping_points'] < 0).any())
        np.testing.assert_allclose(output['score'], sum(output[key] for key in CONTRIBUTIONS), atol=1e-12)

    def test_invalid_optional_measurements_are_rejected(self):
        bank = bank_fixture([120] * 24)
        bank['hhi'] = np.full((1, 24), 2.0)
        with self.assertRaises(ValueError):
            calculate_scores(bank)
        bank.pop('hhi')
        with self.assertRaises(ValueError):
            calculate_scores(bank, {'quality': np.ones((1, 24)), 'conversion': np.full((1, 24), 1.1)})

    def test_momentum_does_not_compare_mature_base_against_warmup_priors(self):
        bank = bank_fixture([120, 118, 119, 125, 126, 127, 128, 129, 130, 131, 132, 133])
        output = calculate_scores(bank)
        np.testing.assert_allclose(output['momentum'][:, :8], 0)

    def test_history_readiness_counts_observed_months_not_calendar_positions(self):
        bank = bank_fixture([0] * 18 + [120] * 6, expenses=0, debt=0)
        bank['quality'][:, :18] = 0
        bank['expenses'][:, 18:] = 100
        output = calculate_scores(bank)
        self.assertFalse(output['history_ready'][0, :23].any())
        self.assertTrue(output['history_ready'][0, 23])
        self.assertFalse(output['momentum_ready'][0, 23])
        self.assertEqual(output['observed_months'][0, 23], 6)

    def test_company_batch_permutation_and_unseen_companies_do_not_change_scores(self):
        bank = bank_fixture(np.array([np.linspace(90, 150, 24), np.linspace(160, 90, 24)]))
        together = calculate_scores(bank)
        alone = calculate_scores({key: value[:1] for key, value in bank.items()})
        reversed_batch = calculate_scores({key: value[::-1] for key, value in bank.items()})
        for key in together:
            np.testing.assert_allclose(together[key][:1], alone[key], err_msg=key)
            np.testing.assert_allclose(together[key][::-1], reversed_batch[key], err_msg=key)

    def test_invalid_coefficient_weights_are_rejected(self):
        with self.assertRaises(ValueError):
            ScoreConfig(base_weights=(.5, .5, .5))


if __name__ == '__main__':
    unittest.main()
