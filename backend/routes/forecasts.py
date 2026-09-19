"""Read-only forecast artifacts, independent of the score/ERP DB variant."""
import json
import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.database import normalize_company_id

router = APIRouter(prefix='/api', tags=['Previsión'])
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[2]/'forecasting'/'artifacts'


@lru_cache(maxsize=4)
def _read(path, modified_ns):
    return json.loads(Path(path).read_text())


def artifact(filename):
    path = Path(os.environ.get('XRAY_FORECAST_DIR', DEFAULT_DIRECTORY))/filename
    try:
        return _read(str(path), path.stat().st_mtime_ns)
    except FileNotFoundError:
        raise HTTPException(503, 'Previsiones no generadas. Ejecuta python -m forecasting.benchmark --dataset data')
    except (ValueError, OSError):
        raise HTTPException(503, 'Artefacto de previsión no disponible')


@router.get('/companies/{id}/forecast')
def company_forecast(id: str):
    cid = normalize_company_id(id)
    row = artifact('forecasts.json')['companies'].get(cid)
    if row is None:
        raise HTTPException(404, f'Empresa {cid} no encontrada')
    return row


@router.get('/forecasts')
def forecast_catalog():
    data = artifact('forecasts.json')
    return {'run_id': data['run_id'], 'companies': [
        {k: c[k] for k in ('company_id', 'as_of', 'status', 'current_score')}
        for c in data['companies'].values()]}


@router.get('/benchmarks/forecasts')
def forecast_benchmark():
    data = artifact('benchmark.json')
    # Audit internals / synthetic donors need not travel to the browser.
    return {k: data[k] for k in ('run_id', 'protocol', 'horizons', 'context', 'versions')}
