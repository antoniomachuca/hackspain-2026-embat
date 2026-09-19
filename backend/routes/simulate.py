"""
POST /api/simulate — contrafactual honest rescoring.
GET  /api/simulate/catalog
GET  /api/simulate/rankings?company_id=
"""

from fastapi import APIRouter, HTTPException, Query

from algorythm.levers import LEVER_CATALOG, simulate_levers
from algorythm.levers_search import recommend_levers
from backend.database import normalize_company_id
from backend.schemas import RankingsResponse, SimulateRequest, SimulateResponse

router = APIRouter(prefix="/api/simulate", tags=["Simulador de Palancas"])


@router.get("/catalog")
def list_lever_catalog():
    return {
        "levers": [
            {"id": lever_id, **meta}
            for lever_id, meta in LEVER_CATALOG.items()
        ]
    }


@router.get("/rankings", response_model=RankingsResponse)
def get_rankings(company_id: str = Query(..., json_schema_extra={"example": "COMP_0031"})):
    cid = normalize_company_id(company_id)
    result = recommend_levers(cid)
    if not result.get("ok", True) and result.get("error") == "empresa_no_encontrada":
        raise HTTPException(status_code=404, detail=f"Empresa '{cid}' no encontrada")
    if result.get("ok") is False:
        raise HTTPException(status_code=422, detail=result)
    return RankingsResponse(**result)


@router.post("", response_model=SimulateResponse)
def run_simulate(req: SimulateRequest):
    cid = normalize_company_id(req.company_id)
    levers = [item.model_dump(exclude_none=True) for item in req.levers]
    for item in levers:
        if "id" not in item and "lever_id" in item:
            item["id"] = item.pop("lever_id")

    try:
        result = simulate_levers(cid, levers)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en simulación: {exc}") from exc

    if not result.get("ok"):
        err = str(result.get("error") or "")
        code = 422
        if err == "empresa_no_encontrada":
            code = 404
        elif err == "inaplicable" or err.startswith("mutuamente") or err in (
            "sin_evidencia_score", "missing_agreement_type", "invalid_agreement_type",
        ):
            code = 422
        else:
            code = 400
        raise HTTPException(status_code=code, detail=result)

    return SimulateResponse(
        company_id=result["company_id"],
        as_of=result["as_of"],
        month_mutated=result["month_mutated"],
        model_version=result["model_version"],
        baseline=result["baseline"],
        projected=result["projected"],
        delta_score=result["delta_score"],
        caja_liberada_eur=result["caja_liberada_eur"],
        effects=result["effects"],
        levers=result["levers"],
        modo=result.get("modo"),
        warnings=result.get("warnings"),
        eur_año=result.get("eur_año"),
        delta_bps=result.get("delta_bps"),
        efecto_score_informativo=result.get("efecto_score_informativo"),
        assumptions=result.get("assumptions"),
    )
