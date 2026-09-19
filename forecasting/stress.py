"""Paired adversarial monthly panels, anchored only to training donors/prefix.

Public customer stories inform business archetypes, never customer financials.
Generated shocks and oracle labels stay separate from model inputs.
"""
import numpy as np

from algorythm.behavior_benchmark import eligible_history, metric_summary
from algorythm.score_engine import calculate_scores
from algorythm.score_monitor import directional_event_matrix
from algorythm.score_states import classify_states

PROFILES = (
    {'id': 'delivery_expansion', 'sector': 'hospitality', 'country': 'ES', 'inspiration': 'VICIO',
     'source': 'https://www.embat.io/es/casos-de-exito/vicio',
     'public_fact': 'Restauración, cobros multicanal y expansión de locales.'},
    {'id': 'construction_projects', 'sector': 'construction', 'country': 'ES', 'inspiration': 'Grupo Construcía',
     'source': 'https://www.embat.io/es/casos-de-exito/grupo-construcia',
     'public_fact': 'Grupo de construcción y economía circular; gestión consolidada de tesorería.'},
    {'id': 'international_services', 'sector': 'services', 'country': 'MX', 'inspiration': 'Grupo Viko',
     'source': 'https://www.embat.io/es/casos-de-exito/viko',
     'public_fact': 'Grupo de marketing con filiales en España y México.'},
)
SCENARIOS = ('control', 'seasonality', 'temporary_dip', 'deterioration', 'improvement',
             'late_collections', 'rate_shock', 'fx_shock', 'expansion_cash_squeeze',
             'customer_loss', 'refinancing', 'group_contagion', 'refund_wave',
             'data_outage', 'cold_start', 'compound_crisis', 'zero_activity', 'debt_balloon', 'recovery')


def generate_stress(bank, companies, groups, protocol, seed=None):
    rng = np.random.default_rng(protocol['stress_seed'] if seed is None else seed)
    prefix = protocol['train_target_end_index']+1
    eligible = np.array([groups[c['group_id']] == 'train' for c in companies])
    eligible &= (bank['quality'][:, :prefix] >= .8).all(axis=1)
    eligible &= (bank['receipts'][:, :prefix] > 0).all(axis=1)
    donors = np.flatnonzero(eligible)
    if not len(donors):
        raise ValueError('No training donors with complete history; cannot calibrate synthetic generator')
    n, months, change = (protocol[k] for k in ('stress_companies_per_case', 'stress_months', 'stress_change_index'))
    if n < 1 or change < 6 or months < change+6:
        raise ValueError('Stress requires positive companies, six months warm-up and six future months')
    source_fields = ('receipts', 'expenses', 'debt_service', 'gross_receipts', 'refunds', 'funding_gap', 'hhi', 'hhi_quality')
    result = []
    for case_index, scenario in enumerate(SCENARIOS):
        chosen = rng.choice(donors, n)
        # Three-month block bootstrap keeps local flow/expense/debt covariance.
        blocks = rng.integers(0, prefix-2, size=(n, (months+2)//3))
        time_idx = (blocks[:, :, None]+np.arange(3)).reshape(n, -1)[:, :months]
        base = {k: np.nan_to_num(bank[k][chosen[:, None], time_idx], nan=0).copy()
                for k in source_fields if k in bank}
        base['quality'] = np.ones((n, months))
        base.setdefault('funding_gap', np.zeros((n, months)))
        base.setdefault('hhi', np.full((n, months), .15))
        base.setdefault('hhi_quality', np.ones((n, months)))
        scale = rng.lognormal(0, .7, (n, 1))
        for k in source_fields:
            if k in base and k not in ('hhi', 'hhi_quality'):
                base[k] *= scale
        # Business archetypes change the generated flows, not merely their labels.
        # All magnitudes below are scenario assumptions, not customer statistics.
        for i in range(n):
            if i % 3 == 0:  # Restaurant: smoother frequent collections, expansion expenses.
                base['receipts'][i] = .5*base['receipts'][i]+.5*np.mean(base['receipts'][i])
            elif i % 3 == 1:  # Construction: quarterly milestone collections conserve total receipts.
                original = base['receipts'][i].copy()
                for t in range(0, months-2, 3):
                    base['receipts'][i, t:t+3] = original[t:t+3].sum()*np.array([.15, .15, .7])
            else:  # Services: payroll is less variable than collections.
                base['expenses'][i] = .3*base['expenses'][i]+.7*np.mean(base['expenses'][i])
        base['gross_receipts'] = base['receipts']+base['refunds']
        stressed = {k: v.copy() for k, v in base.items()}
        r, e, d = (stressed[k] for k in ('receipts', 'expenses', 'debt_service'))
        age = np.arange(1, months-change+1)[None, :]
        severity = rng.uniform(.7, 1.3, (n, 1))
        direction = 0
        if scenario == 'seasonality':
            cycle = 1+.35*np.sin(2*np.pi*np.arange(months)/12)
            r *= cycle
            e *= 1+.15*np.sin(2*np.pi*np.arange(months)/12)
        elif scenario == 'temporary_dip':
            held = .6*r[:, change].copy()
            r[:, change] -= held
            r[:, change+1] += held
        elif scenario in ('deterioration', 'improvement'):
            direction = 1 if scenario == 'improvement' else -1
            r[:, change:] *= np.exp(direction*.035*severity*age)
        elif scenario == 'late_collections':
            direction = -1
            held = .45*r[:, change:].copy()
            r[:, change:] -= held
            r[:, change+2:] += held[:, :-2]
            stressed['funding_gap'][:, change:] += .45*e[:, change:]
        elif scenario == 'rate_shock':
            direction = -1
            d[:, change:] += .12*severity*e[:, change:]
        elif scenario == 'fx_shock':
            direction = -1
            e[:, change:] *= 1+.30*severity
        elif scenario == 'expansion_cash_squeeze':
            direction = -1
            r[:, change:] *= 1+.02*age
            e[:, change:] *= 1.6+.02*age
        elif scenario in ('customer_loss', 'group_contagion', 'compound_crisis'):
            direction = -1
            # Same group-wide shock in contagion scenario; independent severity elsewhere.
            loss = np.full((n, 1), .45) if scenario == 'group_contagion' else .45*severity
            r[:, change:] *= 1-loss
            stressed['hhi'][:, change:] = .8
            stressed['hhi_quality'][:, change:] = 1
            if scenario == 'compound_crisis':
                e[:, change:] *= 1.35
                d[:, change:] += .15*e[:, change:]
        elif scenario == 'refinancing':
            direction = 1
            d[:, change:] *= .2
        elif scenario == 'refund_wave':
            direction = -1
            refunds = .35*r[:, change:].copy()
            r[:, change:] -= refunds
            stressed['refunds'][:, change:] += refunds
        elif scenario == 'data_outage':
            for k in ('receipts', 'expenses', 'debt_service'):
                stressed[k][:, change:change+3] = np.nan
            stressed['quality'][:, change:change+3] = 0
        elif scenario == 'cold_start':
            for k in ('receipts', 'expenses', 'debt_service'):
                stressed[k][:, :change] = np.nan
            stressed['quality'][:, :change] = 0
        elif scenario == 'zero_activity':
            for k in ('receipts', 'expenses', 'debt_service', 'refunds', 'gross_receipts', 'funding_gap'):
                stressed[k][:, change:] = 0
        elif scenario == 'debt_balloon':
            direction = -1
            d[:, change+3] += 12*np.mean(e[:, :change], axis=1)
        elif scenario == 'recovery':
            direction = 1
            r[:, :change] *= .45
            # Recovery oracle is relative to the distressed pre-event path.
            base['receipts'] *= .45
            base['gross_receipts'] = base['receipts']+base['refunds']
        stressed['gross_receipts'] = np.maximum(np.nan_to_num(r), 0)+stressed['refunds']
        profile_rows = []
        for i in range(n):
            profile = PROFILES[i % len(PROFILES)]
            profile_rows.append({'company_id': f'SYN_{case_index:02}_{i:04}',
                'group_id': f'SYN_G_{case_index:02}_{i//3:04}', 'country': profile['country'],
                'sector': profile['sector'], 'currency': 'EUR', 'profile': profile['id'],
                'donor_id': companies[chosen[i]]['company_id']})
        buffer = rng.uniform(1, 5, (n, 1))*np.mean(base['expenses'][:, :change], axis=1, keepdims=True)
        cash = buffer+np.cumsum(np.nan_to_num(r[:, change:]-e[:, change:]-d[:, change:]), axis=1)
        result.append((scenario, stressed, base, profile_rows,
                       {'change': change, 'expected_direction': direction, 'cash_after_change': cash}))
    return result


def synthetic_erp(bank, scenario, change):
    """Explicit simulated ERP evidence, kept out of the bank-only forecasting target."""
    shape = bank['receipts'].shape
    erp = {'dso_days': np.full(shape, 45.), 'late_fraction': np.full(shape, .1),
           'quality': bank['quality'].copy(), 'conversion': np.full(shape, .9),
           'sales_growth': np.zeros(shape)}
    if scenario in ('late_collections', 'customer_loss', 'compound_crisis', 'group_contagion'):
        erp['dso_days'][:, change:] = 105
        erp['late_fraction'][:, change:] = .65
        erp['conversion'][:, change:] = .4
    elif scenario in ('improvement', 'recovery'):
        erp['dso_days'][:, change:] = 20
        erp['late_fraction'][:, change:] = .02
    elif scenario == 'expansion_cash_squeeze':
        erp['sales_growth'][:, change:] = .6
        erp['conversion'][:, change:] = .35
    return erp


def stress_score_report(bank, control, oracle, erp=None, control_erp=None):
    output = calculate_scores(bank)
    paired = calculate_scores(control)
    output.update(classify_states(output))
    events = directional_event_matrix(output)
    eligible = eligible_history(bank, output)
    report = metric_summary(events, eligible, oracle)
    c = oracle['change']
    delta = output['score'][:, c:]-paired['score'][:, c:]
    expected = oracle['expected_direction']
    report.update(paired_score_delta_median=float(np.median(delta)),
                  expected_direction=expected,
                  paired_direction_fraction=float(np.mean(delta*expected > 0)) if expected else None,
                  finite_bounded_scores=bool(np.isfinite(output['score']).all() and
                      (output['score'] >= 0).all() and (output['score'] <= 100).all()),
                  low_quality_scoring_months=int((output['monthly_data_quality'] < .8).sum()),
                  additive_max_error=float(np.max(np.abs(output['score']-sum(output[k] for k in
                      ('liquidity_points', 'collections_points', 'debt_points', 'momentum_points',
                       'growth_points', 'fragility_points', 'clipping_points'))))))
    if erp is not None:
        enhanced = calculate_scores(bank, erp)
        enhanced_control = calculate_scores(control, control_erp)
        report['erp_stress'] = {'paired_score_delta_median': float(np.median(
            enhanced['score'][:, c:]-enhanced_control['score'][:, c:])),
            'finite_bounded_scores': bool(np.isfinite(enhanced['score']).all() and
                (enhanced['score'] >= 0).all() and (enhanced['score'] <= 100).all()),
            'source': 'Simulated ERP assumptions, not historical organizer invoice labels'}
    return report
