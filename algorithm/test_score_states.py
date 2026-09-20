import unittest

import numpy as np

from algorithm.score_states import StateConfig, classify_states


def state_fixture(base=70.0, months=36):
    shape = (1, months)
    return {'score': np.full(shape, base), 'base_health': np.full(shape, base), 'bank_base_health': np.full(shape, base),
            'momentum': np.zeros(shape), 'bank_quality': np.ones(shape), 'is_prior': np.zeros(shape, dtype=bool),
            'history_ready': np.ones(shape, dtype=bool), 'momentum_ready': np.ones(shape, dtype=bool),
            'monthly_flow_margin': np.full(shape, .2), 'monthly_data_quality': np.ones(shape),
            'flow_margin_available': np.ones(shape, dtype=bool), 'observed_months': np.arange(1, months + 1)[None, :],
            'erp_used': np.zeros(shape, dtype=bool), 'cash_used': np.zeros(shape, dtype=bool)}


class StateClassificationTests(unittest.TestCase):
    def test_sustained_negative_momentum_is_detected_while_base_is_high(self):
        scores = state_fixture()
        scores['momentum'][:, 12:] = -.3
        scores['monthly_flow_margin'][:, 12:] = .2 - .03 * np.arange(1, 25)
        output = classify_states(scores, StateConfig(persistence_months=2))
        self.assertEqual(output['state'][0, 12], 'ESTABLE')
        self.assertEqual(output['state'][0, 13], 'TORCIENDOSE')

    def test_decline_escalates_when_level_falls(self):
        scores = state_fixture()
        scores['momentum'][:, 12:] = -.3
        scores['monthly_flow_margin'][:, 12:] = -.1
        scores['base_health'][:, 15:] = 50
        scores['score'][:, 15:] = 48
        output = classify_states(scores, StateConfig(persistence_months=2))
        self.assertEqual(output['state'][0, 15], 'DETERIORO')

    def test_improvement_and_recovery_are_both_recognized(self):
        healthy, weak = state_fixture(75), state_fixture(50)
        for scores in (healthy, weak):
            scores['momentum'][:, 12:] = .3
            scores['monthly_flow_margin'][:, 12:] = .5
        self.assertEqual(classify_states(healthy)['state'][0, 14], 'MEJORANDO')
        self.assertEqual(classify_states(weak)['state'][0, 14], 'RECUPERACION')

    def test_single_pulse_is_provisional_not_structural(self):
        scores = state_fixture()
        scores['monthly_flow_margin'][0, 12] = -.2
        scores['score'][0, 12] = 45
        output = classify_states(scores)
        self.assertEqual(output['state'][0, 12], 'BACHE')
        self.assertTrue(output['state_provisional'][0, 12])
        self.assertFalse(np.isin(output['state'], ['TORCIENDOSE', 'DETERIORO']).any())
        self.assertEqual(output['state'][0, 13], 'ESTABLE')

    def test_insufficient_coverage_or_comparable_history_is_pending(self):
        scores = state_fixture()
        scores['momentum'][:] = -.9
        scores['momentum_ready'][:, :20] = False
        scores['bank_quality'][:, 20:] = .2
        output = classify_states(scores)
        self.assertTrue((output['state'] == 'EVALUACION_PENDIENTE').all())

    def test_low_coverage_is_not_presented_as_solid_health(self):
        scores = state_fixture(85)
        scores['bank_quality'][:] = .2
        output = classify_states(scores)
        self.assertTrue((output['health_band'] == 'COBERTURA_LIMITADA').all())

    def test_hysteresis_does_not_reopen_an_episode_after_one_neutral_month(self):
        scores = state_fixture()
        scores['momentum'][:, 12:] = -.3
        scores['momentum'][0, 16] = 0
        scores['monthly_flow_margin'][:, 12:] = -.1
        output = classify_states(scores)
        self.assertEqual(output['state'][0, 16], 'TORCIENDOSE')
        self.assertEqual(output['state'][0, 17], 'TORCIENDOSE')

    def test_repeating_annual_pattern_is_not_new_structural_deterioration(self):
        scores = state_fixture()
        phase = np.sin(2 * np.pi * np.arange(36) / 12)
        scores['monthly_flow_margin'][0] = .2 + .1 * phase
        scores['momentum'][0] = np.where(np.cos(2 * np.pi * np.arange(36) / 12) < 0, -.3, .3)
        output = classify_states(scores)
        self.assertTrue(output['seasonality_available'][0, 24:].all())
        self.assertTrue((output['state'][0, 24:] == 'ESTABLE').all())

    def test_future_scores_do_not_change_past_states(self):
        scores = state_fixture()
        scores['momentum'][:, 12:] = -.3
        scores['monthly_flow_margin'][:, 12:] = -.1
        original = classify_states(scores)
        scores['momentum'][:, 20:] = .9
        scores['monthly_flow_margin'][:, 20:] = .9
        changed = classify_states(scores)
        for key in original:
            np.testing.assert_array_equal(original[key][:, :20], changed[key][:, :20], err_msg=key)

    def test_state_latching_prevented_when_opposing_momentum_occurs(self):
        scores = state_fixture()
        scores['momentum'][:, 12:15] = .3
        scores['monthly_flow_margin'][:, 12:15] = .5
        output = classify_states(scores)
        self.assertEqual(output['state'][0, 14], 'MEJORANDO')

        # In month 15, sharp reversal with negative momentum:
        scores['momentum'][0, 15] = -.3
        scores['monthly_flow_margin'][0, 15] = -.2
        output_reversal = classify_states(scores)
        # Must NOT latch to MEJORANDO when opposite negative momentum is active!
        self.assertNotEqual(output_reversal['state'][0, 15], 'MEJORANDO')
        self.assertEqual(output_reversal['state'][0, 15], 'ESTABLE')


if __name__ == '__main__':
    unittest.main()
