"""GET /api/palancas — catálogo ancho con es_aplicable por empresa."""

from fastapi import APIRouter, HTTPException, Query

from algorithm.levers_catalog import AS_OF
from algorithm.levers_gates import evaluate_catalog
from backend.database import normalize_company_id
from backend.schemas import PalancaItem, PalancasResponse

router = APIRouter(prefix="/api/palancas", tags=["Palancas"])


@router.get("", response_model=PalancasResponse)
def get_palancas(company_id: str = Query(..., description="COMP_XXXX")):
    cid = normalize_company_id(company_id)
    try:
        rows = evaluate_catalog(cid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Empresa '{cid}' no encontrada") from exc
    return PalancasResponse(
        company_id=cid,
        as_of=AS_OF,
        palancas=[PalancaItem(**row) for row in rows],
    )
