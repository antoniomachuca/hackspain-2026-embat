"""
Endpoint para el Simulador Contrafactual What-If de X-Ray.
"""

from fastapi import APIRouter, HTTPException

from algorithm.score_whatif import simulate_whatif
from backend.database import normalize_company_id
from backend.schemas import WhatIfRequest, WhatIfResponse

router = APIRouter(prefix="/api/whatif", tags=["Simulador What-If"])


@router.post("", response_model=WhatIfResponse)
def run_whatif_simulation(req: WhatIfRequest):
    """
    Ejecuta el motor de simulación contrafactual para modelar el impacto de una inyección
    de tesorería o anticipo de facturas sobre el score de solvencia de la empresa.
    
    Si 'injection_amount' no se proporciona o es <= 0, el motor calcula automáticamente
    el tramo mínimo óptimo requerido para rescatar a la empresa a un estado solvente (score >= 60).
    """
    cid = normalize_company_id(req.company_id)
    try:
        res = simulate_whatif(company_id=cid, injection_amount=req.injection_amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la simulación: {str(e)}")

    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"Empresa '{cid}' no encontrada para la simulación contrafactual"
        )

    f_gain = round(float(res.get("fragility_gain", 0.0)), 2)

    return WhatIfResponse(
        company_id=res["company_id"],
        group_id=res.get("group_id", ""),
        as_of=str(res.get("as_of", "")),
        current_score=round(float(res["current_score"]), 2),
        current_state=str(res["current_state"]),
        injection_amount=round(float(res["injection_amount"]), 2),
        is_optimal_computed=bool(res.get("is_optimal_computed", False)),
        delta_score=round(float(res["delta_score"]), 2),
        projected_score=round(float(res["projected_score"]), 2),
        projected_state=str(res["projected_state"]),
        liquidity_gain=round(float(res.get("liquidity_gain", 0.0)), 2),
        fragility_gain=f_gain,
        fragility_reduction=f_gain,
        collections_gain=round(float(res.get("collections_gain", 0.0)), 2),
        recommended_product=str(res.get("recommended_product", "")),
        product_rationale=str(res.get("product_rationale", "")),
        executive_message=str(res.get("summary_html", "")),
    )
