"""Full CSV audit for arquitectura-astra-carlos.md. Requires duckdb.

Run from the repository root:
  python research/arquitectura_carlos/audit.py --db /tmp/embat-audit.duckdb
Raw CSVs are read in full, never modified. JSON contains aggregates only.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb

parser = argparse.ArgumentParser()
parser.add_argument('--data', type=Path, default=Path('data'))
parser.add_argument('--db', default='/tmp/embat-audit.duckdb')
parser.add_argument('--out', type=Path, default=Path('research/arquitectura_carlos/audit_results.json'))
args = parser.parse_args()
start = time.perf_counter()
db = duckdb.connect(args.db)
db.execute("SET threads=4")

def query(sql):
    cur = db.execute(sql)
    return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

result = {'duckdb_version': duckdb.__version__, 'tables': {}, 'checks': {}}
pks = {'groups': 'group_id', 'companies': 'company_id', 'transactions': 'transaction_id',
       'invoices': 'operation_id'}
for path in sorted(args.data.glob('*.csv')):
    name = path.stem
    db.execute(f'CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv(?, header=true, all_varchar=true, sample_size=-1)', [str(path)])
    cols = [r[0] for r in db.execute(f'DESCRIBE {name}').fetchall()]
    pk = pks.get(name, 'product_id')
    summary = query(f'SELECT count(*) AS rows, count(DISTINCT {pk}) AS unique_pk FROM {name}')[0]
    summary['columns'] = cols
    summary['bytes'] = path.stat().st_size
    with path.open('rb') as stream:
        summary['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    summary['nulls'] = query('SELECT '+ ', '.join(f'count(*) FILTER (WHERE "{c}" IS NULL) AS "{c}"' for c in cols)+f' FROM {name}')[0]
    summary['dates'] = {}
    for c in cols:
        if c.endswith('_date') or c in ('date', 'created_at'):
            summary['dates'][c] = query(f'SELECT min("{c}") AS min, max("{c}") AS max, count(*) FILTER (WHERE "{c}" IS NOT NULL AND try_cast("{c}" AS TIMESTAMP) IS NULL) AS invalid FROM {name}')[0]
    summary['domains'] = {}
    for c in ['type', 'country', 'currency', 'accounting_currency', 'erp', 'status', 'accounting_status', 'category', 'document_type', 'interest_type', 'amortising_frequency']:
        if c in cols:
            summary['domains'][c] = query(f'SELECT "{c}" AS value, count(*) AS n FROM {name} GROUP BY 1 ORDER BY 2 DESC')
    result['tables'][name] = summary
    print(name, summary['rows'], flush=True)

db.execute('CREATE OR REPLACE TABLE products AS SELECT product_id,company_id,type,currency,created_at FROM banking_products UNION ALL SELECT product_id,company_id,type,currency,created_at FROM debt_products')
checks = result['checks']
for table in ['banking_products','debt_products','debt_schedule_config','transactions','invoices','balances']:
    checks[table+'_company_orphans'] = query(f'SELECT count(*) AS n FROM {table} t ANTI JOIN companies c USING(company_id)')[0]['n']
for table in ['transactions','balances','debt_schedule_config']:
    checks[table+'_product_orphans'] = query(f'SELECT count(*) AS n FROM {table} t ANTI JOIN products p USING(product_id)')[0]['n']
    checks[table+'_owner_mismatch'] = query(f'SELECT count(*) AS n FROM {table} t JOIN products p USING(product_id) WHERE t.company_id <> p.company_id')[0]['n']
checks['company_group_orphans'] = query('SELECT count(*) AS n FROM companies ANTI JOIN groups USING(group_id)')[0]['n']
checks['product_id_overlap'] = query('SELECT count(*) AS n FROM banking_products JOIN debt_products USING(product_id)')[0]['n']
checks['group_size'] = query('SELECT min(n) AS min, median(n) AS median, max(n) AS max FROM (SELECT group_id,count(*) n FROM companies GROUP BY 1)')[0]
checks['group_declared_mismatch'] = query('SELECT count(*) AS n FROM groups g JOIN (SELECT group_id,count(*) n FROM companies GROUP BY 1) c USING(group_id) WHERE cast(g.n_companies_in_sample AS INT) <> c.n')[0]['n']
for table in ['transactions','invoices']:
    checks[table+'_counterparties'] = query(f'SELECT count(DISTINCT counterparty_id) AS distinct_ids, count(*) FILTER (WHERE counterparty_id IS NOT NULL) AS resolved_rows, count(*) FILTER (WHERE counterparty_id IN (SELECT company_id FROM companies)) AS direct_company_matches FROM {table}')[0]
checks['shared_counterparties'] = query('SELECT count(*) AS n FROM (SELECT DISTINCT counterparty_id FROM transactions WHERE counterparty_id IS NOT NULL) t JOIN (SELECT DISTINCT counterparty_id FROM invoices WHERE counterparty_id IS NOT NULL) i USING(counterparty_id)')[0]['n']
checks['transaction_product_types'] = query('SELECT p.type,count(*) n FROM transactions t JOIN products p USING(product_id) GROUP BY 1 ORDER BY 2 DESC')
checks['tx_months'] = query("SELECT substr(date,1,7) AS month,count(*) AS n,count(DISTINCT company_id) AS companies FROM transactions GROUP BY 1 ORDER BY 1")
checks['tx_history'] = query("SELECT count(*) AS companies, min(months) AS min_months, median(months) AS median_months, count(*) FILTER (WHERE months<12) AS under_12, quantile_cont(n/(730.0/7),0.1) AS p10_per_calendar_week, median(n/(730.0/7)) AS median_per_calendar_week FROM (SELECT company_id,count(DISTINCT substr(date,1,7)) AS months,count(*) n FROM transactions WHERE date<'2026-09-01' GROUP BY 1)")[0]
checks['companies_no_transactions'] = query('SELECT count(*) n FROM companies ANTI JOIN (SELECT DISTINCT company_id FROM transactions) t USING(company_id)')[0]['n']
checks['companies_no_invoices'] = query('SELECT count(*) n FROM companies ANTI JOIN (SELECT DISTINCT company_id FROM invoices) i USING(company_id)')[0]['n']
checks['debt_coverage'] = query('SELECT type,count(*) products,count(DISTINCT company_id) companies,count(*) FILTER (WHERE granted IS NOT NULL) with_granted,count(*) FILTER (WHERE outstanding IS NOT NULL) with_outstanding FROM debt_products GROUP BY 1 ORDER BY 2 DESC')
checks['schedule_coverage'] = query("SELECT count(*) AS schedules,count(DISTINCT company_id) AS companies,count(*) FILTER (WHERE annual_interest_rate_or_spread IS NOT NULL) AS rates,count(*) FILTER (WHERE cast(next_payment_date AS TIMESTAMP)<'2026-09-01') AS next_payment_in_past, min(try_cast(annual_interest_rate_or_spread AS DOUBLE)) AS min_rate,max(try_cast(annual_interest_rate_or_spread AS DOUBLE)) AS max_rate FROM debt_schedule_config")[0]
checks['schedule_settlement_missing'] = query('SELECT count(*) n FROM debt_schedule_config d ANTI JOIN products p ON d.settlement_product_id=p.product_id')[0]['n']
checks['invoice_signs'] = query("SELECT document_type,status,count(*) n,count(*) FILTER (WHERE cast(amount AS DOUBLE)>0) positives,count(*) FILTER (WHERE cast(amount AS DOUBLE)<0) negatives,count(*) FILTER (WHERE cast(amount AS DOUBLE)=0) zeros FROM invoices GROUP BY 1,2 ORDER BY 1,2")
checks['invoice_anomalies'] = query("SELECT count(*) FILTER (WHERE payment_date<issuance_date) AS paid_before_issue,count(*) FILTER (WHERE due_date<issuance_date) AS due_before_issue,count(*) FILTER (WHERE payment_date>'2026-09-01 23:59:59') AS future_payments,count(*) FILTER (WHERE status='paid' AND payment_date IS NULL) AS paid_without_date,count(*) FILTER (WHERE status='paid' AND cast(pending_amount AS DOUBLE)<>0) AS paid_with_pending,count(*) FILTER (WHERE abs(cast(pending_amount AS DOUBLE))>abs(cast(amount AS DOUBLE))) AS pending_over_amount,count(*) FILTER (WHERE abs(cast(pending_amount AS DOUBLE))>0 AND abs(cast(pending_amount AS DOUBLE))<abs(cast(amount AS DOUBLE))) AS partial_pending FROM invoices")[0]
checks['fx_invoices'] = query('SELECT currency,accounting_currency,count(*) n, min(try_cast(exchange_rate AS DOUBLE)) min_rate,max(try_cast(exchange_rate AS DOUBLE)) max_rate FROM invoices GROUP BY 1,2 ORDER BY 3 DESC')
checks['fx_transactions'] = query('SELECT p.currency,count(*) n,min(try_cast(t.exchange_rate AS DOUBLE)) min_rate,max(try_cast(t.exchange_rate AS DOUBLE)) max_rate FROM transactions t JOIN products p USING(product_id) GROUP BY 1 ORDER BY 2 DESC')
checks['currency_mismatches'] = query('SELECT count(*) FILTER (WHERE p.currency<>c.currency) AS products_vs_company FROM products p JOIN companies c USING(company_id)')[0]
checks['transaction_categories_signs'] = query('SELECT category,count(*) n,count(*) FILTER (WHERE cast(amount AS DOUBLE)>0) positives,count(*) FILTER (WHERE cast(amount AS DOUBLE)<0) negatives FROM transactions GROUP BY 1 ORDER BY 2 DESC')
checks['transaction_temporal_anomalies'] = query('SELECT count(*) FILTER (WHERE t.date<c.created_at) AS before_company_onboarding,count(*) FILTER (WHERE t.date<p.created_at) AS before_product_onboarding,count(*) FILTER (WHERE t.date<>t.value_date) AS different_value_date FROM transactions t JOIN companies c USING(company_id) JOIN products p USING(product_id)')[0]
checks['balances_coverage'] = query('SELECT p.type,count(*) products,count(b.product_id) with_balance,count(*) FILTER (WHERE cast(b.balance AS DOUBLE)<0) negative_balances FROM products p LEFT JOIN balances b USING(product_id) GROUP BY 1 ORDER BY 2 DESC')
checks['debt_signs'] = query('SELECT type,count(*) FILTER (WHERE cast(outstanding AS DOUBLE)<0) negative,count(*) FILTER (WHERE cast(outstanding AS DOUBLE)>0) positive,count(*) FILTER (WHERE cast(granted AS DOUBLE)<=0) nonpositive_granted FROM debt_products GROUP BY 1')
checks['balance_dates'] = query('SELECT date,count(*) n FROM balances GROUP BY 1 ORDER BY 1')
checks['invoice_bank_pair_coverage'] = query('SELECT count(*) AS invoices,count(*) FILTER (WHERE EXISTS(SELECT 1 FROM transactions t WHERE t.company_id=i.company_id AND t.counterparty_id=i.counterparty_id)) AS same_company_counterparty FROM invoices i')[0]
checks['invoice_payment_semantics'] = query("SELECT status,count(*) AS n,count(*) FILTER (WHERE payment_date IS NOT NULL) AS with_payment_date,count(*) FILTER (WHERE payment_date=due_date) AS payment_equals_due,count(*) FILTER (WHERE cast(pending_amount AS DOUBLE)=0) AS zero_pending FROM invoices GROUP BY 1 ORDER BY 2 DESC")
checks['bad_fx'] = {
    t: query(f'SELECT count(*) AS n FROM {t} WHERE try_cast(exchange_rate AS DOUBLE)<=0')[0]['n']
    for t in ['invoices','transactions']
}
checks['extreme_invoice_dates'] = query("SELECT count(*) FILTER (WHERE due_date>='2100') AS due_after_2099,count(*) FILTER (WHERE payment_date>='2100') AS payment_after_2099 FROM invoices")[0]
checks['invoice_sign_matching_probe'] = query("""
WITH candidates AS (
 SELECT i.operation_id, sign(cast(i.amount AS DECIMAL(24,6))) AS invoice_sign,
        sign(cast(t.amount AS DECIMAL(24,6))) AS transaction_sign
 FROM invoices i JOIN transactions t
 ON i.company_id=t.company_id AND i.counterparty_id=t.counterparty_id
 AND abs(cast(i.amount AS DECIMAL(24,6)))=abs(cast(t.amount AS DECIMAL(24,6)))
 JOIN products p ON t.product_id=p.product_id
 WHERE i.document_type='invoice' AND i.status='paid' AND t.status='booked'
 AND i.currency=p.currency AND cast(i.amount AS DOUBLE)<>0
 AND abs(date_diff('day',cast(i.payment_date AS TIMESTAMP),cast(t.date AS TIMESTAMP)))<=3
), unique_matches AS (
 SELECT operation_id,min(invoice_sign) AS si,min(transaction_sign) AS st
 FROM candidates GROUP BY 1 HAVING count(*)=1
)
SELECT count(*) AS unique_invoice_candidates,count(*) FILTER (WHERE si=st) AS same_sign,
       count(*) FILTER (WHERE si<>st) AS opposite_sign FROM unique_matches
""")[0]
result['elapsed_seconds'] = round(time.perf_counter()-start,3)
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
print('Saved',args.out, 'in',result['elapsed_seconds'],'seconds')
