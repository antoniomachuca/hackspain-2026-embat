"""Point-in-time external context. Never infer sector or country from an ID/currency.

Revised statistical observations are usable only from retrieval unless a real
historical publication timestamp is supplied. Assumed publication dates can be
included in a separately labelled sensitivity experiment, never the strict run.
"""
import argparse
import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

INDICATORS = ('policy_rate', 'usd_eur', 'industrial_production', 'construction', 'retail')
FIELDS = ('indicator', 'geo', 'sector', 'period', 'available_at', 'value',
          'availability_basis', 'source_url', 'retrieved_at')


def load_context(path=None):
    if path is None:
        return []
    with Path(path).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if not set(FIELDS) <= row.keys():
            raise ValueError('External context requires provenance and availability fields')
        row['value'] = float(row['value'])
        if row['indicator'] not in INDICATORS or not np.isfinite(row['value']):
            raise ValueError('Unknown indicator or invalid context value')
        if date.fromisoformat(row['available_at']) < date.fromisoformat(row['period']):
            raise ValueError('External data cannot be available before its observation period')
        if row['availability_basis'] not in ('official_effective_date', 'verified_publication',
                                             'retrieval_only_latest_revision', 'assumed_lag'):
            raise ValueError('Unknown availability basis')
        if row['availability_basis'] == 'retrieval_only_latest_revision' and row['available_at'] < row['retrieved_at']:
            raise ValueError('Latest revised values cannot be backdated before retrieval')
    return rows


def context_features(companies, as_of, rows, allow_assumed=False):
    """Value, missingness and age. Strict timestamps prevent silent vintage leakage."""
    result = np.zeros((len(companies), len(as_of), len(INDICATORS) * 3))
    result[:, :, 1::3] = 1
    result[:, :, 2::3] = 999
    for k, indicator in enumerate(INDICATORS):
        candidates = [r for r in rows if r['indicator'] == indicator and
                      (allow_assumed or r['availability_basis'] != 'assumed_lag')]
        for i, company in enumerate(companies):
            for t, cutoff in enumerate(as_of):
                matching = [r for r in candidates if r['available_at'] <= cutoff and r['period'] < cutoff
                            and (r['geo'] == '*' or r['geo'] == company.get('country'))
                            and (r['sector'] == '*' or r['sector'] == company.get('sector'))]
                if not matching:
                    continue
                latest = max(matching, key=lambda r: (r['period'], r['available_at']))
                age = (date.fromisoformat(cutoff) - date.fromisoformat(latest['period'])).days
                if age > 120 and indicator != 'policy_rate':
                    continue
                result[i, t, 3*k:3*k+3] = [latest['value'], 0, age]
    return result


def fetch_context(output, start='2024-01', end='2026-08'):
    """Cache public ECB and Eurostat data, together with precise provenance.

    ECB FX monthly observations get a conservative lag only for sensitivity runs.
    Policy rates use the checked-in official dated decisions snapshot.
    Eurostat's API returns the latest revision, not an archived vintage.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).date().isoformat()
    rows, errors, hashes = [], [], {}
    decisions_path = Path(__file__).with_name('forecast_policy_rates.json')
    decisions = json.loads(decisions_path.read_text())
    hashes['policy_rate'] = hashlib.sha256(decisions_path.read_bytes()).hexdigest()
    for effective_date, value in decisions['observations']:
        if effective_date[:7] <= end:
            rows.append(dict(zip(FIELDS, ['policy_rate', '*', '*', effective_date, effective_date,
                value, decisions['availability_basis'], decisions['source_url'], decisions['retrieved_at']])))
    series = [('usd_eur', 'EXR', 'M.USD.EUR.SP00.A')]
    for indicator, flow, key in series:
        url = f'https://data-api.ecb.europa.eu/service/data/{flow}/{key}'
        try:
            response = requests.get(url, params={'startPeriod': start, 'endPeriod': end, 'format': 'csvdata'}, timeout=45)
            response.raise_for_status()
            hashes[indicator] = hashlib.sha256(response.content).hexdigest()
            items = list(csv.DictReader(io.StringIO(response.text)))
            for item in items:
                period = item['TIME_PERIOD'][:7] + '-01'
                first = date.fromisoformat(period)
                following = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
                rows.append(dict(zip(FIELDS, [indicator, '*', '*', period,
                    (following + timedelta(days=7)).isoformat(), float(item['OBS_VALUE']),
                    'assumed_lag', response.url, retrieved])))
        except (requests.RequestException, KeyError, ValueError) as exc:
            errors.append({'indicator': indicator, 'error': str(exc)})
    for indicator, dataset, sector, nace in [('industrial_production', 'sts_inpr_m', 'industry', 'B-D'),
                                            ('construction', 'sts_copr_m', 'construction', 'F'),
                                            ('retail', 'sts_trtu_m', 'retail', 'G47')]:
        url = f'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}'
        try:
            params = {'lang': 'EN', 'geo': 'ES', 'sinceTimePeriod': start,
                      'untilTimePeriod': end, 's_adj': 'SCA', 'unit': 'I21', 'nace_r2': nace}
            if indicator == 'retail':
                params['indic_bt'] = 'VOL_SLS'
            response = requests.get(url, params=params, timeout=45)
            response.raise_for_status()
            payload = response.json()
            hashes[indicator] = hashlib.sha256(response.content).hexdigest()
            dims, sizes = payload['id'], payload['size']
            time_pos = dims.index('time')
            # Refuse ambiguous units/adjustments instead of mixing multiple series.
            if any(size != 1 for j, size in enumerate(sizes) if j != time_pos):
                raise ValueError('Eurostat query returned more than one series')
            periods = payload['dimension']['time']['category']['index']
            if isinstance(periods, list):
                periods = {p: i for i, p in enumerate(periods)}
            for period, index in periods.items():
                value = payload.get('value', {}).get(str(index))
                if value is not None:
                    rows.append(dict(zip(FIELDS, [indicator, 'ES', sector, period[:7]+'-01', retrieved,
                        float(value), 'retrieval_only_latest_revision', response.url, retrieved])))
        except (requests.RequestException, KeyError, ValueError) as exc:
            errors.append({'indicator': indicator, 'error': str(exc)})
    with output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    manifest = {'retrieved_at': retrieved, 'rows': len(rows), 'response_sha256': hashes, 'errors': errors,
                'strict_historical_use': 'Dated ECB rate decisions eligible; FX lag assumptions excluded; revised Eurostat series available from retrieval.'}
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('algorythm/forecast_results/external_context.csv'))
    args = parser.parse_args()
    print(json.dumps(fetch_context(args.output), indent=2))
