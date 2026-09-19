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

from forecasting.country import normalize_country

INDICATORS = ('policy_rate', 'usd_eur', 'industrial_production', 'hicp', 'unemployment')
FIELDS = ('indicator', 'geo', 'sector', 'period', 'available_at', 'value',
          'availability_basis', 'source_url', 'retrieved_at')
EUROSTAT_LAG_DAYS = 45
FX_LAG_DAYS = 7


def month_start(period):
    text = period[:7] + '-01'
    return date.fromisoformat(text)


def next_month(day):
    return date(day.year + (day.month == 12), day.month % 12 + 1, 1)


def assumed_available_at(period, lag_days):
    return (next_month(month_start(period)) + timedelta(days=lag_days)).isoformat()


def load_context(path=None):
    if path is None:
        return []
    with Path(path).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    accepted = []
    for row in rows:
        if not set(FIELDS) <= row.keys():
            raise ValueError('External context requires provenance and availability fields')
        if row['indicator'] not in INDICATORS:
            continue
        row['value'] = float(row['value'])
        if not np.isfinite(row['value']):
            raise ValueError('Unknown indicator or invalid context value')
        if date.fromisoformat(row['available_at']) < date.fromisoformat(row['period']):
            raise ValueError('External data cannot be available before its observation period')
        if row['availability_basis'] not in ('official_effective_date', 'verified_publication',
                                             'retrieval_only_latest_revision', 'assumed_lag'):
            raise ValueError('Unknown availability basis')
        if row['availability_basis'] == 'retrieval_only_latest_revision' and row['available_at'] < row['retrieved_at']:
            raise ValueError('Latest revised values cannot be backdated before retrieval')
        accepted.append(row)
    return accepted


def context_features(companies, as_of, rows, allow_assumed=False):
    """Value, missingness and age. Strict timestamps prevent silent vintage leakage."""
    result = np.zeros((len(companies), len(as_of), len(INDICATORS) * 3))
    result[:, :, 1::3] = 1
    result[:, :, 2::3] = 999
    geos = [normalize_country(company.get('country')) for company in companies]
    sectors = [(company.get('sector') or '').strip() for company in companies]
    for k, indicator in enumerate(INDICATORS):
        candidates = [r for r in rows if r['indicator'] == indicator and
                      (allow_assumed or r['availability_basis'] != 'assumed_lag')]
        for i, (geo, sector) in enumerate(zip(geos, sectors)):
            for t, cutoff in enumerate(as_of):
                matching = [r for r in candidates if r['available_at'] <= cutoff and r['period'] < cutoff
                            and (r['geo'] == '*' or r['geo'] == geo)
                            and (r['sector'] == '*' or (sector and r['sector'] == sector))]
                if not matching:
                    continue
                latest = max(matching, key=lambda r: (r['period'], r['available_at']))
                age = (date.fromisoformat(cutoff) - date.fromisoformat(latest['period'])).days
                if age > 120 and indicator != 'policy_rate':
                    continue
                result[i, t, 3*k:3*k+3] = [latest['value'], 0, age]
    return result


def _eurostat_series(payload):
    dims, sizes = payload['id'], payload['size']
    time_pos = dims.index('time')
    if any(size != 1 for j, size in enumerate(sizes) if j != time_pos):
        raise ValueError('Eurostat query returned more than one series')
    periods = payload['dimension']['time']['category']['index']
    if isinstance(periods, list):
        periods = {p: i for i, p in enumerate(periods)}
    return periods, payload.get('value', {})


def fetch_context(output, start='2024-01', end='2026-08'):
    """Cache public ECB and Eurostat data, together with precise provenance.

    ECB FX monthly observations get a conservative lag only for sensitivity runs.
    Policy rates use the checked-in official dated decisions snapshot.
    Eurostat's API returns the latest revision, not an archived vintage; national
    series are dated with an assumed publication lag and tagged assumed_lag.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).date().isoformat()
    rows, errors, hashes = [], [], {}
    decisions_path = Path(__file__).with_name('policy_rates.json')
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
                rows.append(dict(zip(FIELDS, [indicator, '*', '*', period,
                    assumed_available_at(period, FX_LAG_DAYS), float(item['OBS_VALUE']),
                    'assumed_lag', response.url, retrieved])))
        except (requests.RequestException, KeyError, ValueError) as exc:
            errors.append({'indicator': indicator, 'error': str(exc)})
    eurostat = (
        ('industrial_production', 'sts_inpr_m', {'s_adj': 'SCA', 'unit': 'I21', 'nace_r2': 'B-D'}),
        ('hicp', 'prc_hicp_midx', {'coicop': 'CP00', 'unit': 'I15'}),
        ('unemployment', 'une_rt_m', {'s_adj': 'SA', 'sex': 'T', 'age': 'TOTAL', 'unit': 'PC_ACT'}),
    )
    for indicator, dataset, extra in eurostat:
        url = f'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}'
        try:
            params = {'lang': 'EN', 'geo': 'ES', 'sinceTimePeriod': start, 'untilTimePeriod': end, **extra}
            response = requests.get(url, params=params, timeout=45)
            response.raise_for_status()
            payload = response.json()
            hashes[indicator] = hashlib.sha256(response.content).hexdigest()
            periods, values = _eurostat_series(payload)
            for period, index in periods.items():
                value = values.get(str(index))
                if value is not None:
                    start_period = period[:7] + '-01'
                    rows.append(dict(zip(FIELDS, [indicator, 'ES', '*', start_period,
                        assumed_available_at(start_period, EUROSTAT_LAG_DAYS), float(value),
                        'assumed_lag', response.url, retrieved])))
        except (requests.RequestException, KeyError, ValueError) as exc:
            errors.append({'indicator': indicator, 'error': str(exc)})
    with output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    manifest = {'retrieved_at': retrieved, 'rows': len(rows), 'response_sha256': hashes, 'errors': errors,
                'lags_days': {'usd_eur': FX_LAG_DAYS, 'eurostat_monthly': EUROSTAT_LAG_DAYS},
                'strict_historical_use': (
                    'Dated ECB rate decisions eligible in strict mode. FX and Eurostat national '
                    'series use assumed publication lags and are only eligible in '
                    'conservative_publication_lag. Eurostat values are the latest revision, not an archived vintage.'
                )}
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).parent/'datasets/external/external_context_national_v1.csv')
    args = parser.parse_args()
    print(json.dumps(fetch_context(args.output), indent=2))
