import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
