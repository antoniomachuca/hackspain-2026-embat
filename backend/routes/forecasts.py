"""Forecast artifacts (lab) and live structural paths for the product chart."""
import json
import os
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.database import normalize_company_id, query_one
from backend.schemas import PrevisionEstructuralResponse
from forecasting.structural import load_company_banks, structural_prevision

router = APIRouter(prefix='/api', tags=['Previsión'])
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[2]/'forecasting'/'artifacts'

_banks = None
_banks_lock = threading.Lock()


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


def _load_banks():
    global _banks
    if _banks is None:
        with _banks_lock:
            if _banks is None:
                _banks = load_company_banks()
    return _banks


def _catalog_has_company(cid: str) -> bool:
    try:
        row = query_one(
            'SELECT company_id FROM v_latest_company_scores WHERE company_id = ?',
            (cid,),
        )
    except Exception:
        return False
    return row is not None


def _insufficient(cid: str, meses: int) -> dict:
    return {
        'company_id': cid,
        'model': 'structural_v2',
        'status': 'insufficient_history',
        'as_of': None,
        'meses': meses,
        'current_score': None,
        'alto': [],
        'medio': [],
        'bajo': [],
    }


@router.get('/companies/{id}/forecast')
def company_forecast(id: str):
    cid = normalize_company_id(id)
    row = artifact('forecasts.json')['companies'].get(cid)
    if row is None:
        raise HTTPException(404, f'Empresa {cid} no encontrada')
    return row


@router.get(
    '/companies/{id}/prevision-estructural',
    response_model=PrevisionEstructuralResponse,
)
def company_prevision_estructural(
    id: str,
    meses: int = Query(12, ge=1, le=24, description='Meses futuros a proyectar (t+1 … t+meses)'),
):
    """Tres sendas mensuales de score: proyecta la cuenta y aplica calculate_scores."""
    cid = normalize_company_id(id)
    banks = _load_banks()
    if cid not in banks:
        if not _catalog_has_company(cid):
            raise HTTPException(404, f"Empresa '{cid}' no encontrada")
        return _insufficient(cid, meses)
    payload = structural_prevision(cid, meses=meses, banks=banks)
    if payload is None:
        raise HTTPException(404, f"Empresa '{cid}' no encontrada")
    return payload


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
