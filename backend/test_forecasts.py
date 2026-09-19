import json

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes import forecasts as forecasts_mod
from backend.routes.forecasts import router


def test_forecast_unavailable_unknown_and_abstention(tmp_path, monkeypatch):
    monkeypatch.setenv('XRAY_FORECAST_DIR', str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get('/api/companies/10/forecast').status_code == 503
    row = {'company_id': 'COMP_0010', 'status': 'insufficient_history', 'as_of': '2026-09-01',
           'current_score': 50, 'points': []}
    (tmp_path/'forecasts.json').write_text(json.dumps({'run_id': 'test', 'companies': {'COMP_0010': row}}))
    assert client.get('/api/companies/10/forecast').json() == row
    assert client.get('/api/companies/9999/forecast').status_code == 404
    assert client.get('/api/forecasts').json()['companies'][0]['status'] == 'insufficient_history'
    # Cache invalidates when the artifact is replaced.
    row['status'] = 'available'
    (tmp_path/'forecasts.json').write_text(json.dumps({'run_id': 'updated', 'companies': {'COMP_0010': row}}))
    assert client.get('/api/forecasts').json()['run_id'] == 'updated'


def _panel(months):
    receipts = 100. + 4. * np.arange(months)
    expenses, debt = np.full(months, 80.), np.full(months, 10.)
    refunds = 0.1 * receipts
    return {k: v[None].copy() for k, v in dict(
        receipts=receipts, expenses=expenses, debt_service=debt, refunds=refunds,
        quality=np.ones(months), gross_receipts=receipts + refunds,
    ).items()}


def test_prevision_estructural_available_unknown_and_short(monkeypatch):
    banks = {'COMP_0010': (_panel(24), 0)}
    monkeypatch.setattr(forecasts_mod, '_load_banks', lambda: banks)
    monkeypatch.setattr(forecasts_mod, '_catalog_has_company', lambda cid: cid == 'COMP_0099')
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    ok = client.get('/api/companies/10/prevision-estructural')
    assert ok.status_code == 200
    data = ok.json()
    assert data['company_id'] == 'COMP_0010'
    assert data['model'] == 'structural_v2'
    assert data['status'] == 'available'
    assert data['meses'] == 12
    assert data['as_of'] == '2026-08-01'
    assert len(data['alto']) == len(data['medio']) == len(data['bajo']) == 12
    assert all(0 <= v <= 100 for v in data['alto'] + data['medio'] + data['bajo'])

    six = client.get('/api/companies/COMP_0010/prevision-estructural?meses=6').json()
    assert six['meses'] == 6
    assert len(six['medio']) == 6

    assert client.get('/api/companies/COMP_9999/prevision-estructural').status_code == 404

    empty = client.get('/api/companies/COMP_0099/prevision-estructural').json()
    assert empty['status'] == 'insufficient_history'
    assert empty['alto'] == []

    monkeypatch.setattr(forecasts_mod, '_load_banks', lambda: {'COMP_0010': (_panel(2), 0)})
    short = client.get('/api/companies/10/prevision-estructural').json()
    assert short['status'] == 'insufficient_history'
