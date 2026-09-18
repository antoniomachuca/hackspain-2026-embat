"""Exploratory forecast benchmark, NOT a validated financial health score.

Requires the database created by audit.py, numpy, scipy and scikit-learn.
Temporal holdout AND five group holdouts; no target or parameter tuning.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb
import numpy as np
import scipy
import sklearn
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

parser = argparse.ArgumentParser()
parser.add_argument('--db', default='/tmp/embat-audit.duckdb')
parser.add_argument('--out',type=Path,default=Path('research/arquitectura_carlos/experiment_results.json'))
args = parser.parse_args()
start = time.perf_counter()
db = duckdb.connect(args.db,read_only=True)
threadpool_limits(limits=2)

# No FX guesses: retain companies whose entire supplied product inventory is EUR.
# Snapshot inventory is an exploratory cohort filter, not a historical feature.
# Gross operational proxy excludes transfers, unknown categories, debt and investments.
rows = db.execute("""
SELECT t.company_id, c.group_id, substr(t.date,1,7) AS month,
sum(greatest(cast(t.amount AS DOUBLE),0)) AS inflow,
sum(greatest(-cast(t.amount AS DOUBLE),0)) AS outflow, count(*) AS n
FROM transactions t JOIN products p USING(product_id) JOIN companies c ON t.company_id=c.company_id
WHERE t.status='booked' AND p.type IN ('checking','saving')
AND t.date<'2026-09-01' AND c.currency='EUR'
AND NOT EXISTS (SELECT 1 FROM products p2 WHERE p2.company_id=t.company_id AND p2.currency<>'EUR')
AND t.category IN ('collection','bulk_collection','payment','bulk_payment','utility',
 'salary','social_security','tax','tax_refund','fee','pos_settlement',
 'collection_refund','payment_refund')
GROUP BY 1,2,3 ORDER BY 1,3
""").fetchall()
series = {}
for company,group,month,inc,out,n in rows:
    if company not in series:
        series[company] = {'group':group,'cash':np.zeros((24,3))}
    year,mon = map(int,month.split('-'))
    index = (year-2024)*12+mon-9
    series[company]['cash'][index] = [inc,out,n]

X,y,folds,origins,baseline,company_ids = [],[],[],[],[],[]
for company,info in series.items():
    cash = info['cash']
    inc,out,n = cash.T
    gross = inc+out
    margin = np.divide(inc-out,gross,out=np.zeros(24),where=gross>0)
    fold = int(hashlib.sha256(info['group'].encode()).hexdigest()[:8],16)%5
    def ratio(lo,hi):
        g = gross[lo:hi].sum()
        return (inc[lo:hi].sum()-out[lo:hi].sum())/g if g else 0.
    for t in range(5,21):
        # Consecutive observed activity prevents treating missing history as zero.
        if not np.all(n[t-5:t+1]>0) or not np.all(n[t+1:t+4]>0):
            continue
        m3,m6 = ratio(t-2,t+1),ratio(t-5,t+1)
        x = [margin[t],m3,m6,float(margin[t-5:t+1].std()),
             float(np.mean(margin[t-5:t+1]<0)),
             float(np.polyfit(np.arange(6),margin[t-5:t+1],1)[0]),
             float(np.log1p(inc[t-5:t+1].mean())),float(np.log1p(out[t-5:t+1].mean())),
             float(np.log1p(n[t-5:t+1].mean())),
             float(np.log1p(inc[t-2:t+1].mean())-np.log1p(inc[t-5:t-2].mean()))]
        X.append(x); y.append(ratio(t+1,t+4)); folds.append(fold); origins.append(t)
        baseline.append([margin[t],m3,m6,ratio(t-11,t-8) if t>=11 else 0.])
        company_ids.append(company)
X,y,folds,origins,baseline = map(np.asarray,[X,y,folds,origins,baseline])
predictions = {n:[] for n in ['last_month','trailing_3m','trailing_6m','seasonal_previous_year','ridge','hist_gradient_boosting']}
truth=[]; fold_report=[]; evaluated_groups=[]
for fold in range(5):
    train=(folds!=fold)&(origins<=14)  # Last training target ends Feb 2026.
    test=(folds==fold)&(origins>=17)   # Future targets Mar-Aug 2026.
    truth.extend(y[test]); evaluated_groups.extend([series[c]['group'] for c,ok in zip(company_ids,test) if ok])
    report={'fold':fold,'train':int(train.sum()),'test':int(test.sum())}
    for j,name in enumerate(list(predictions)[:4]):
        predictions[name].extend(baseline[test,j])
    models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=10)),
            'hist_gradient_boosting':HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=7,
                  min_samples_leaf=30,l2_regularization=10,early_stopping=False,random_state=42)}
    for name,model in models.items():
        model.fit(X[train],y[train]); p=np.clip(model.predict(X[test]),-1,1)
        predictions[name].extend(p)
        report[name+'_mae']=float(np.mean(abs(p-y[test])))
    fold_report.append(report)
    print(report,flush=True)
truth=np.asarray(truth); evaluated_groups=np.asarray(evaluated_groups)
metrics={}
for name,p in predictions.items():
    p=np.asarray(p)
    group_errors=[float(np.mean(abs(p[evaluated_groups==g]-truth[evaluated_groups==g]))) for g in np.unique(evaluated_groups)]
    metrics[name]={'mae':float(np.mean(abs(p-truth))), 'spearman':float(spearmanr(p,truth).statistic),
                   'direction_accuracy':float(np.mean((p>=0)==(truth>=0))),
                   'macro_group_mae':float(np.mean(group_errors))}

# Controlled detector experiments: fixed hypotheses, no fitted health labels.
# 1000 paths per scenario, sigma=2 score points, first shift in month index 12.
rng=np.random.default_rng(42)
def detect(a,method):
    if method=='ols6_median3_persist3':
        slopes=[np.polyfit(np.arange(6),a[t-5:t+1],1)[0] for t in range(5,len(a))]
        smoothed=[np.median(slopes[j-2:j+1]) for j in range(2,len(slopes))]
        for j in range(2,len(smoothed)):
            w=np.asarray(smoothed[j-2:j+1])
            if np.all(w>1) or np.all(w < -1): return j+7
    elif method=='ewma_fast_slow_persist2':
        fast=slow=a[:8].mean(); streak=0; prev=0
        for t in range(8,len(a)):
            fast=.5*a[t]+.5*fast; slow=.15*a[t]+.85*slow
            sign=int(np.sign(fast-slow)) if abs(fast-slow)>3 else 0
            streak=streak+1 if sign and sign==prev else int(bool(sign)); prev=sign
            if streak>=2:return t
    elif method=='cusum':
        mu=a[:8].mean(); sd=max(a[:8].std(ddof=1),1.); pos=neg=0.
        for t in range(8,len(a)):
            z=(a[t]-mu)/sd;pos=max(0,pos+z-.5);neg=min(0,neg+z+.5)
            if pos>5 or neg < -5:return t
    return None
detectors={}
for scenario in ['stable','pulse','deterioration','improvement']:
    paths=50+rng.normal(0,2,(1000,24))
    if scenario=='pulse': paths[:,12]-=12
    if scenario in ('deterioration','improvement'):
        paths[:,12:]+=np.arange(1,13)*(-2 if scenario=='deterioration' else 2)
    detectors[scenario]={}
    for method in ['ols6_median3_persist3','ewma_fast_slow_persist2','cusum']:
        hits=[detect(a,method) for a in paths]
        delays=[h-12 for h in hits if h is not None and h>=12]
        detectors[scenario][method]={'any_alert_fraction':sum(h is not None for h in hits)/1000,
            'pre_event_fraction':sum(h is not None and h<12 for h in hits)/1000,
            'post_event_detection_fraction':len(delays)/1000,
            'median_delay_months':float(np.median(delays)) if delays else None}

result={'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__},
 'cohort_companies':len(series),'cohort_transactions':int(sum(row[5] for row in rows)),
 'samples':len(y),'test_samples':len(truth),'test_companies':len(set(c for c,t in zip(company_ids,origins) if t>=17)),
 'test_groups':len(set(evaluated_groups)),
 'target':'Sum(inflow-outflow)/sum(inflow+outflow) over next 3 months, restricted operational proxy',
 'limitations':['Not financial health ground truth','Cohort uses final product metadata and complete future activity',
                'Current booked/category values lack historical versioning','Overlapping evaluation horizons',
                'Only euro inventory companies, checking/saving, allowlisted categories',
                'Synthetic detector test is not empirical anticipation on Embat'],
 'forecast_metrics':metrics,'folds':fold_report,'controlled_detectors':detectors,
 'elapsed_seconds':round(time.perf_counter()-start,3)}
args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(result,indent=2))
