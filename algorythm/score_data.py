import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

from algorythm.score_engine import divide, rolling_sum


INCOME_CATEGORIES = {'collection', 'bulk_collection', 'pos_settlement', 'cash_settlement', 'cash_settlements'}
EXPENSE_CATEGORIES = {'payment', 'bulk_payment', 'salary', 'social_security', 'tax', 'utility', 'fee'}
DEBT_CATEGORIES = {'debt_repayment', 'interest_charge'}


def rows(path):
    with path.open(newline='', encoding='utf-8') as source:
        yield from csv.DictReader(source)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def month_edges(start='2024-09-01', end='2026-09-01'):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first.day != 1 or last.day != 1 or first >= last:
        raise ValueError('start and end must be increasing first-of-month dates')
    result = [first]
    while result[-1] < last:
        current = result[-1]
        result.append(date(current.year + (current.month == 12), current.month % 12 + 1, 1))
    return result


def parse_day(value):
    return date.fromisoformat(value[:10]).toordinal() if value else -1


def normalize_transaction(row):
    amount = float(row['amount'])
    category = row['category']
    if category in INCOME_CATEGORIES and amount > 0:
        return 'receipts', amount
    if category == 'collection_refund' and amount < 0:
        return 'receipts', amount
    if category in EXPENSE_CATEGORIES:
        return 'expenses', -amount
    if category == 'payment_refund' and amount > 0:
        return 'expenses', -amount
    if category in DEBT_CATEGORIES and amount < 0:
        return 'debt_service', -amount
    return None, 0.0


def load_bank_panel(dataset: Path, start='2024-09-01', end='2026-09-01'):
    companies = sorted(rows(dataset / 'companies.csv'), key=lambda row: row['company_id'])
    index = {row['company_id']: i for i, row in enumerate(companies)}
    products = {row['product_id']: row for name in ('banking_products.csv', 'debt_products.csv') for row in rows(dataset / name)}
    edges = month_edges(start, end)
    ordinals = np.array([day.toordinal() for day in edges])
    shape = (len(companies), len(edges) - 1)
    names = ('receipts', 'expenses', 'debt_service', 'gross_receipts', 'refunds', 'recognized_absolute', 'native_absolute', 'booked_count', 'native_count')
    bank = {name: np.zeros(shape) for name in names}
    daily_net = np.zeros((shape[0], ordinals[-1] - ordinals[0]))
    customer_receipts = {}
    checks = Counter()
    for row in rows(dataset / 'transactions.csv'):
        i = index[row['company_id']]
        day = parse_day(row['date'])
        month = int(np.searchsorted(ordinals, day, side='right') - 1)
        if not 0 <= month < shape[1] or row['status'] != 'booked':
            checks['excluded_date_or_status'] += 1
            continue
        bank['booked_count'][i, month] += 1
        product = products.get(row['product_id'])
        if product is None or product['company_id'] != row['company_id']:
            checks['unknown_or_mismatched_product'] += 1
            continue
        if product['currency'] != companies[i]['currency'] or not row['exchange_rate'] or float(row['exchange_rate']) != 1:
            checks['excluded_currency_or_fx'] += 1
            continue
        amount = float(row['amount'])
        bank['native_count'][i, month] += 1
        bank['native_absolute'][i, month] += abs(amount)
        field, signed = normalize_transaction(row)
        if field is None:
            continue
        bank[field][i, month] += signed
        bank['recognized_absolute'][i, month] += abs(amount)
        daily_net[i, day - ordinals[0]] += signed if field == 'receipts' else -signed
        if field == 'receipts' and signed > 0:
            bank['gross_receipts'][i, month] += signed
            if row['counterparty_id']:
                key = (i, row['counterparty_id'])
                customer_receipts.setdefault(key, np.zeros(shape[1]))[month] += signed
        if field == 'receipts' and signed < 0:
            bank['refunds'][i, month] -= signed
    bank['receipts'] = np.maximum(bank['receipts'], 0)
    bank['expenses'] = np.maximum(bank['expenses'], 0)
    bank['native_share'] = np.nan_to_num(divide(bank['native_count'], bank['booked_count']), nan=0)
    bank['classified_share'] = np.nan_to_num(divide(bank['recognized_absolute'], bank['native_absolute']), nan=0)
    bank['quality'] = np.minimum(bank['native_share'], bank['classified_share'])
    bank['funding_gap'] = np.full(shape, np.nan)
    for month in range(shape[1]):
        block = daily_net[:, ordinals[month] - ordinals[0]:ordinals[month + 1] - ordinals[0]].cumsum(axis=1)
        gross_gap = np.maximum(-np.min(block, axis=1), 0)
        terminal_deficit = np.maximum(-block[:, -1], 0)
        gap = np.maximum(gross_gap - terminal_deficit, 0)
        bank['funding_gap'][:, month] = np.where(bank['native_count'][:, month] > 0, gap, np.nan)
    bank['hhi'], bank['hhi_quality'] = customer_concentration(customer_receipts, bank['gross_receipts'])
    checks['bank_hhi_endpoint_available'] = int(np.isfinite(bank['hhi'][:, -1]).sum())
    return companies, edges, bank, dict(checks)


def customer_concentration(customer_receipts, gross_receipts):
    shape = gross_receipts.shape
    known = np.zeros(shape)
    squared = np.zeros(shape)
    for (company, _), amounts in customer_receipts.items():
        trailing = rolling_sum(amounts[None, :], 3)[0]
        known[company] += np.nan_to_num(trailing, nan=0)
        squared[company] += np.nan_to_num(trailing, nan=0) ** 2
    total = rolling_sum(gross_receipts, 3)
    coverage = divide(known, total)
    hhi = divide(squared, known ** 2)
    hhi = np.where(coverage >= .95, hhi, np.nan)
    return hhi, np.where(np.isfinite(hhi), coverage, 0)


def add_cash_observations(bank, companies, edges, path):
    shape = bank['receipts'].shape
    for key in ('cash_balance', 'commitments_30d', 'negative_balance_fraction'):
        bank[key] = np.full(shape, np.nan)
    index = {row['company_id']: i for i, row in enumerate(companies)}
    cutoffs = {day.isoformat(): month for month, day in enumerate(edges[1:])}
    seen = set()
    for row in rows(path):
        if row['as_of'] not in cutoffs:
            continue
        if not row.get('observed_at') or parse_day(row['observed_at']) > parse_day(row['as_of']):
            raise ValueError('cash observation requires an observed_at date no later than its as_of date')
        i, month = index[row['company_id']], cutoffs[row['as_of']]
        if row['currency'] != companies[i]['currency']:
            raise ValueError('cash observation currency differs from company currency')
        if (i, month) in seen:
            raise ValueError('duplicate company/as_of cash observation')
        seen.add((i, month))
        for key in ('cash_balance', 'commitments_30d', 'negative_balance_fraction'):
            bank[key][i, month] = float(row[key]) if row.get(key) else np.nan


def load_erp_snapshot(dataset, companies, edges, bank, snapshot_as_of='2026-09-01'):
    shape = bank['receipts'].shape
    names = ('dso_days', 'late_fraction', 'conversion', 'sales_growth', 'hhi')
    erp = {name: np.full(shape, np.nan) for name in names}
    erp.update(quality=np.zeros(shape), hhi_quality=np.zeros(shape))
    cutoffs = [day.isoformat() for day in edges[1:]]
    if snapshot_as_of not in cutoffs:
        return erp, {'snapshot_not_in_evaluation_cutoffs': True}
    month = cutoffs.index(snapshot_as_of)
    if month < 5:
        return erp, {'insufficient_window': True}
    cutoff = parse_day(snapshot_as_of)
    recent_start = edges[month - 2].toordinal()
    previous_start = edges[month - 5].toordinal()
    index = {row['company_id']: i for i, row in enumerate(companies)}
    sums = {name: np.zeros(shape[0]) for name in ('sales', 'previous_sales', 'pending', 'matured', 'late', 'converted', 'recent_count', 'all_count', 'valid_count', 'known_customer')}
    customers = {}
    checks = Counter()
    observed_companies = set()
    for row in rows(dataset / 'invoices.csv'):
        i = index[row['company_id']]
        observed_companies.add(i)
        amount = float(row['amount'])
        issued = parse_day(row['issuance_date'])
        if row['document_type'] != 'invoice' or amount <= 0 or issued > cutoff or row['status'] == 'cancel':
            continue
        sums['all_count'][i] += 1
        if row['currency'] != companies[i]['currency'] or row['accounting_currency'] != companies[i]['currency'] or not row['exchange_rate'] or float(row['exchange_rate']) != 1:
            checks['excluded_currency_or_fx'] += 1
            continue
        due = parse_day(row['due_date'])
        pending = float(row['pending_amount']) if row['pending_amount'] else np.nan
        if due < issued or due > issued + 365 or not 0 <= pending <= amount:
            checks['excluded_invalid_due_or_pending'] += 1
            continue
        sums['valid_count'][i] += 1
        sums['pending'][i] += pending
        if recent_start <= due < cutoff:
            sums['matured'][i] += amount
            sums['late'][i] += pending
        if recent_start <= issued < cutoff:
            sums['sales'][i] += amount
            sums['converted'][i] += amount - pending
            sums['recent_count'][i] += 1
            if row['counterparty_id']:
                key = (i, row['counterparty_id'])
                customers[key] = customers.get(key, 0) + amount
                sums['known_customer'][i] += amount
        if previous_start <= issued < recent_start:
            sums['previous_sales'][i] += amount
    erp['dso_days'][:, month] = divide((cutoff - recent_start) * sums['pending'], sums['sales'])
    erp['late_fraction'][:, month] = divide(sums['late'], sums['matured'])
    cash = bank['receipts'][:, month - 2:month + 1].sum(axis=1)
    erp['conversion'][:, month] = np.minimum(np.clip(divide(sums['converted'], sums['sales']), 0, 1), np.clip(divide(cash, sums['sales']), 0, 1))
    erp['sales_growth'][:, month] = divide(sums['sales'] - sums['previous_sales'], sums['sales'] + sums['previous_sales'])
    adequate = (sums['recent_count'] >= 5) & (sums['matured'] > 0)
    quality = np.nan_to_num(divide(sums['valid_count'], sums['all_count']), nan=0)
    erp['quality'][:, month] = quality * adequate
    squared = np.zeros(shape[0])
    for (i, _), amount in customers.items():
        squared[i] += amount ** 2
    customer_share = divide(sums['known_customer'], sums['sales'])
    erp['hhi'][:, month] = np.where(customer_share >= .95, divide(squared, sums['known_customer'] ** 2), np.nan)
    erp['hhi_quality'][:, month] = np.where(np.isfinite(erp['hhi'][:, month]), customer_share, 0)
    checks['companies_with_any_invoice'] = len(observed_companies)
    checks['companies_with_usable_snapshot'] = int(np.sum(erp['quality'][:, month] > 0))
    checks['assumes_positive_invoice_amount_is_sale'] = True
    checks['payment_date_used_to_infer_payment'] = False
    checks['snapshot_as_of'] = snapshot_as_of
    return erp, dict(checks)
