"""Factor split vs OLS-on-score vs 3m photocopy. Labels are the data-generating process."""
import unittest

import numpy as np

from algorithm.score_decompose import (
    DRIVER_MIN_ABS, FIELD_ETIQUETA, REASON_ETIQUETA, attribute_month,
    classify_driver, copy_bank, decompose_series, factor_to_reparto,
    history_with_reparto, ols_reparto, photocopy_reparto,
)
from algorithm.score_engine import calculate_scores


SHOCK = 12
MONTHS = 24


def steady_bank(months=MONTHS, receipts=120.0, expenses=80.0, debt=12.0):
    shape = (1, months)
    rec = np.full(shape, receipts)
    ref = 0.02 * rec
    return {
        'receipts': rec.copy(),
        'expenses': np.full(shape, expenses),
        'debt_service': np.full(shape, debt),
        'refunds': ref.copy(),
        'gross_receipts': rec + ref,
        'quality': np.ones(shape),
        'funding_gap': np.zeros(shape),
        'hhi': np.full(shape, 0.15),
        'hhi_quality': np.ones(shape),
    }


def case_opex_cut():
    bank = steady_bank()
    bank['expenses'][:, SHOCK:] *= 0.75
    return 'opex_cut', bank, 'estructural'


def case_collect_early():
    bank = steady_bank()
    held = 0.40 * bank['receipts'][0, SHOCK]
    bank['receipts'][0, SHOCK] += held
    bank['receipts'][0, SHOCK + 1] -= held
    bank['gross_receipts'] = bank['receipts'] + bank['refunds']
    return 'collect_early', bank, 'coyuntural'


def case_temporary_dip():
    bank = steady_bank()
    held = 0.60 * bank['receipts'][0, SHOCK]
    bank['receipts'][0, SHOCK] -= held
    bank['receipts'][0, SHOCK + 1] += held
    bank['gross_receipts'] = bank['receipts'] + bank['refunds']
    return 'temporary_dip', bank, 'coyuntural'


def case_deterioration():
    bank = steady_bank()
    age = np.arange(1, MONTHS - SHOCK + 1)
    bank['receipts'][0, SHOCK:] *= np.exp(-0.04 * age)
    bank['gross_receipts'] = bank['receipts'] + bank['refunds']
    return 'deterioration', bank, 'estructural'


def case_seasonality():
    bank = steady_bank()
    cycle = 1 + 0.35 * np.sin(2 * np.pi * np.arange(MONTHS) / 12)
    bank['receipts'] *= cycle
    bank['refunds'] = 0.02 * bank['receipts']
    bank['gross_receipts'] = bank['receipts'] + bank['refunds']
    return 'seasonality', bank, 'coyuntural'


def case_dpo_once():
    bank = steady_bank()
    held = 0.35 * bank['expenses'][0, SHOCK]
    bank['expenses'][0, SHOCK] -= held
    bank['expenses'][0, SHOCK + 1] += held
    return 'dpo_once', bank, 'coyuntural'


def case_rate_shock():
    bank = steady_bank()
    bank['debt_service'][:, SHOCK:] += 0.20 * bank['expenses'][:, SHOCK:]
    return 'rate_shock', bank, 'estructural'


def case_control():
    bank = steady_bank()
    return 'control', bank, 'neutro'


CASES = (case_opex_cut, case_collect_early, case_temporary_dip, case_deterioration,
         case_seasonality, case_dpo_once, case_rate_shock, case_control)


def winner(row, method):
    block = row[method]
    if abs(block['delta']) < 0.15:
        return 'neutro'
    return 'estructural' if block['pct_tendencia'] >= 50 else 'coyuntural'


def mean_split(bank, method, start=SHOCK, stop=SHOCK + 3, series=None):
    series = series if series is not None else decompose_series(bank)
    chunks = [row[method] for row in series if start <= row['t'] < stop and abs(row['delta']) >= 0.15]
    if not chunks:
        return 0.0, 0.0, 0
    tend = float(np.mean([c['pct_tendencia'] for c in chunks]))
    bache = float(np.mean([c['pct_bache'] for c in chunks]))
    return tend, bache, len(chunks)


WINDOWS = {
    'seasonality': (18, 21),
}


def compare_cases(start=SHOCK, stop=SHOCK + 3):
    """Empirics for the research note / canvas. Not a test assertion by itself."""
    rows = []
    for factory in CASES:
        name, bank, label = factory()
        series = decompose_series(bank)
        a, b = WINDOWS.get(name, (start, stop))
        for method in ('ols', 'fotocopia', 'factor'):
            tend, bache, n = mean_split(bank, method, a, b, series=series)
            calls = [winner(row, method) for row in series if a <= row['t'] < b]
            judged = [c for c in calls if c != 'neutro']
            if label == 'neutro':
                acc = float(np.mean([c == 'neutro' for c in calls])) if calls else 1.0
            else:
                acc = float(np.mean([c == label for c in judged])) if judged else float('nan')
            rows.append({
                'case': name, 'label': label, 'method': method,
                'pct_tendencia': tend, 'pct_bache': bache, 'n': n, 'accuracy': acc,
            })
    return rows


class FactorDecompositionTests(unittest.TestCase):
    def test_opex_cut_is_structural_on_day_one_ols_calls_it_a_dip(self):
        _, bank, _ = case_opex_cut()
        scores = calculate_scores(bank)['score'][0]
        ols = ols_reparto(scores, SHOCK)
        factor = attribute_month(bank, SHOCK)
        self.assertGreater(factor['pct_tendencia'], 60, factor)
        self.assertLess(ols['pct_tendencia'], 50, ols)
        expenses = next(d for d in factor['drivers'] if d.field == 'expenses')
        self.assertEqual(expenses.kind, 'estructural')
        self.assertEqual(expenses.reason, 'opex')

    def test_collecting_early_one_month_is_circumstantial(self):
        _, bank, _ = case_collect_early()
        shock = attribute_month(bank, SHOCK)
        rebound = attribute_month(bank, SHOCK + 1)
        self.assertGreater(shock['pct_bache'], 60, shock)
        self.assertGreater(rebound['pct_bache'], 60, rebound)
        receipts = next(d for d in shock['drivers'] if d.field == 'receipts')
        self.assertEqual(receipts.kind, 'coyuntural')

    def test_temporary_dip_reverses_and_is_not_a_new_regime(self):
        _, bank, _ = case_temporary_dip()
        shock = attribute_month(bank, SHOCK)
        self.assertGreater(shock['pct_bache'], 60, shock)
        self.assertEqual(classify_driver('receipts', bank, SHOCK)[0], 'coyuntural')

    def test_deterioration_is_volume_not_a_pulse(self):
        _, bank, _ = case_deterioration()
        kind, reason = classify_driver('receipts', bank, SHOCK + 2)
        self.assertEqual(kind, 'estructural')
        self.assertEqual(reason, 'volumen')
        tend, _, n = mean_split(bank, 'factor', SHOCK, SHOCK + 6)
        self.assertGreater(n, 0)
        self.assertGreater(tend, 50)

    def test_paying_suppliers_late_once_is_circumstantial_for_expenses(self):
        _, bank, _ = case_dpo_once()
        shock = attribute_month(bank, SHOCK)
        expenses = next(d for d in shock['drivers'] if d.field == 'expenses')
        self.assertEqual(expenses.kind, 'coyuntural')
        self.assertGreater(shock['pct_bache'], 50, shock)

    def test_dpo_without_next_month_keeps_the_opex_prior(self):
        _, bank, _ = case_dpo_once()
        truncated = {key: np.array(val[:, :SHOCK + 1]) for key, val in bank.items()}
        kind, reason = classify_driver('expenses', truncated, SHOCK)
        self.assertEqual(kind, 'estructural')
        self.assertEqual(reason, 'opex')

    def test_rate_shock_lands_on_debt_service(self):
        _, bank, _ = case_rate_shock()
        factor = attribute_month(bank, SHOCK)
        debt = next(d for d in factor['drivers'] if d.field == 'debt_service')
        self.assertEqual(debt.kind, 'estructural')
        self.assertLess(debt.points, -0.5)
        self.assertGreater(factor['pct_tendencia'], 50, factor)

    def test_first_month_of_slow_decline_is_still_confused_with_last_year(self):
        """A 4%/month drop is inside the 6% YoY deadband on impact. Honest hole."""
        _, bank, _ = case_deterioration()
        kind, reason = classify_driver('receipts', bank, SHOCK)
        self.assertEqual((kind, reason), ('coyuntural', 'estacion'))
        kind, reason = classify_driver('receipts', bank, SHOCK + 2)
        self.assertEqual((kind, reason), ('estructural', 'volumen'))

    def test_seasonal_receipts_match_last_year(self):
        _, bank, _ = case_seasonality()
        kind, reason = classify_driver('receipts', bank, 18)
        self.assertEqual(kind, 'coyuntural')
        self.assertEqual(reason, 'estacion')

    def test_dso_jump_overrides_volume(self):
        bank = steady_bank()
        bank['receipts'][0, SHOCK] *= 0.7
        bank['gross_receipts'] = bank['receipts'] + bank['refunds']
        erp = {
            'dso_days': np.full((1, MONTHS), 30.0),
            'late_fraction': np.zeros((1, MONTHS)),
            'quality': np.ones((1, MONTHS)),
            'conversion': np.full((1, MONTHS), 0.9),
            'sales_growth': np.zeros((1, MONTHS)),
        }
        erp['dso_days'][0, SHOCK] = 50.0
        kind, reason = classify_driver('receipts', bank, SHOCK, erp=erp)
        self.assertEqual((kind, reason), ('coyuntural', 'dso'))

    def test_identity_drivers_sum_to_delta(self):
        _, bank, _ = case_opex_cut()
        factor = attribute_month(bank, SHOCK)
        reconstructed = sum(d.points for d in factor['drivers'])
        self.assertAlmostEqual(reconstructed, factor['delta'], places=4)

    def test_no_lookahead_mutating_future_receipts_does_not_change_past_points(self):
        _, bank, _ = case_opex_cut()
        original = attribute_month(bank, SHOCK)
        tweaked = copy_bank(bank)
        tweaked['receipts'][0, SHOCK + 3] *= 3
        tweaked['gross_receipts'] = tweaked['receipts'] + tweaked['refunds']
        again = attribute_month(tweaked, SHOCK)
        self.assertAlmostEqual(original['delta'], again['delta'], places=6)
        self.assertAlmostEqual(original['struct_pts'], again['struct_pts'], places=4)

    def test_control_months_are_flat(self):
        _, bank, _ = case_control()
        factor = attribute_month(bank, SHOCK)
        self.assertLess(abs(factor['delta']), 0.15)
        self.assertEqual(factor['pct_tendencia'], 0.0)

    def test_photocopy_still_calls_opex_cut_mostly_a_dip_in_the_shock_month(self):
        """The 3m run-rate only swallows 1/3 of a level shift on impact.

        This is why 'smooth the inputs, then apply f' is not the same as
        knowing that expenses are opex.
        """
        _, bank, _ = case_opex_cut()
        photo = photocopy_reparto(bank, SHOCK)
        factor = attribute_month(bank, SHOCK)
        self.assertLess(photo['pct_tendencia'], factor['pct_tendencia'])
        self.assertLess(photo['pct_tendencia'], 50)

    def test_comparison_table_has_every_case(self):
        table = compare_cases()
        names = {row['case'] for row in table}
        self.assertEqual(names, {factory()[0] for factory in CASES})
        methods = {row['method'] for row in table}
        self.assertEqual(methods, {'ols', 'fotocopia', 'factor'})

    def test_api_json_filters_tiny_drivers_and_translates(self):
        _, bank, _ = case_opex_cut()
        payload = factor_to_reparto(attribute_month(bank, SHOCK))
        self.assertEqual(payload['pct_tendencia'], 100)
        self.assertEqual(payload['pct_bache'], 0)
        fields = {d['field'] for d in payload['drivers']}
        self.assertIn('expenses', fields)
        for driver in payload['drivers']:
            self.assertGreaterEqual(abs(driver['points']), DRIVER_MIN_ABS)
            self.assertEqual(driver['etiqueta'], FIELD_ETIQUETA[driver['field']])
            self.assertEqual(driver['razon'], REASON_ETIQUETA[driver['reason']])
        gastos = next(d for d in payload['drivers'] if d['field'] == 'expenses')
        self.assertEqual(gastos['kind'], 'estructural')
        self.assertEqual(gastos['reason'], 'opex')

    def test_history_with_reparto_aligns_month_zero_empty(self):
        _, bank, _ = case_collect_early()
        dates = [f'2024-{m:02d}-01' for m in range(1, 13)] + [
            f'2025-{m:02d}-01' for m in range(1, 13)
        ]
        body = history_with_reparto(bank, dates, company_id='DEMO_COBROS')
        self.assertEqual(body['months'], 24)
        self.assertEqual(len(body['history']), 24)
        self.assertEqual(body['history'][0]['reparto']['drivers'], [])
        shock = body['history'][SHOCK]['reparto']
        self.assertEqual(shock['pct_bache'], 100)
        cobros = next(d for d in shock['drivers'] if d['field'] == 'receipts')
        self.assertEqual(cobros['reason'], 'pulso_cobros')

    def test_one_off_cobro_is_a_dip_when_it_lands_and_when_the_window_forgets_it(self):
        bank = steady_bank(receipts=0.0, expenses=40.0, debt=0.0)
        bank['receipts'][0, :] = 0.0
        bank['receipts'][0, SHOCK] = 800.0
        bank['refunds'][0, :] = 0.0
        bank['gross_receipts'] = bank['receipts'] + bank['refunds']
        landing = attribute_month(bank, SHOCK)
        receipts = next(d for d in landing['drivers'] if d.field == 'receipts')
        self.assertEqual((receipts.kind, receipts.reason), ('coyuntural', 'cobro_puntual'))
        self.assertGreater(landing['pct_bache'], 60, landing)
        fade = attribute_month(bank, SHOCK + 3)
        arrastre = next(d for d in fade['drivers'] if d.field == 'arrastre')
        self.assertEqual((arrastre.kind, arrastre.reason), ('coyuntural', 'cobro_puntual'))
        self.assertGreater(fade['pct_bache'], 60, fade)
        self.assertLess(fade['delta'], -1)


if __name__ == '__main__':
    unittest.main()
