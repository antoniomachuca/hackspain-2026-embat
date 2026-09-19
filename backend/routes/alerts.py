"""
Endpoints para la consulta y campanita de alertas de riesgo de tesorería (X-Ray).
"""

import json
from typing import Optional
from fastapi import APIRouter, Query

from backend.database import normalize_company_id, query_dicts, query_one
from backend.schemas import AlertItem, AlertListResponse

router = APIRouter(prefix="/api/alerts", tags=["Alertas de Riesgo"])


@router.get("", response_model=AlertListResponse)
def get_alerts(
    severity: Optional[str] = Query(None, description="Filtrar por severidad ('ALTA', 'MEDIA', 'INFORMATIVA')"),
    state: Optional[str] = Query(None, description="Filtrar por estado del monitor"),
    company_id: Optional[str] = Query(None, description="Filtrar por empresa"),
    direction: Optional[str] = Query(None, description="Filtrar por dirección ('deterioration', 'improvement', 'neutral')"),
    as_of: Optional[str] = Query(None, description="Filtrar por fecha de corte (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=200, description="Cantidad máxima de alertas a devolver"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
):
    """
    Feed histórico y en tiempo real de eventos de riesgo emitidos por el monitor de solvencia.
    Alimenta el panel de notificaciones y alertas urgentes para el tesorero.
    """
    conditions = []
    params = []

    if severity:
        conditions.append("severity = ?")
        params.append(severity.strip().upper())
    if state:
        conditions.append("state = ?")
        params.append(state.strip().upper())
    if company_id:
        cid = normalize_company_id(company_id)
        conditions.append("company_id = ?")
        params.append(cid)
    if direction:
        conditions.append("direction = ?")
        params.append(direction.strip().lower())
    if as_of:
        conditions.append("as_of = ?")
        params.append(as_of.strip())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Conteo total filtrado
    count_sql = f"SELECT count(*) AS total FROM alerts {where_clause};"
    count_row = query_one(count_sql, tuple(params))
    total = count_row["total"] if count_row else 0

    # Alertas ordenadas cronológicamente (más recientes primero, y con mayor prioridad las de menor score)
    data_sql = f"""
        SELECT 
            alert_id, company_id, group_id, as_of, state, severity, direction,
            score, delta_score, momentum, drivers_json, created_at
        FROM alerts
        {where_clause}
        ORDER BY as_of DESC, score ASC, alert_id ASC
        LIMIT ? OFFSET ?;
    """
    rows = query_dicts(data_sql, tuple(params + [limit, offset]))

    alerts = []
    for row in rows:
        drivers = []
        if row.get("drivers_json"):
            try:
                drivers = json.loads(row["drivers_json"])
            except Exception:
                pass

        alerts.append(
            AlertItem(
                alert_id=row["alert_id"],
                company_id=row["company_id"],
                group_id=row["group_id"],
                as_of=str(row["as_of"]),
                state=row["state"],
                severity=row["severity"],
                direction=row["direction"],
                score=round(float(row["score"]), 2),
                delta_score=round(float(row["delta_score"]), 2),
                momentum=round(float(row["momentum"]), 4),
                drivers=drivers,
                created_at=str(row["created_at"]) if row.get("created_at") else None,
            )
        )

    return AlertListResponse(total=total, limit=limit, offset=offset, alerts=alerts)
