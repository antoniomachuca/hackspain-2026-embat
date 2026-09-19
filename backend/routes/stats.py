"""
Endpoints de estadísticas globales, KPIs de cartera, grupos corporativos y salud del backend (X-Ray).
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException

from backend.database import DB_PATH, query_dicts, query_one
from backend.schemas import (
    GroupCompanyItem,
    GroupDetailResponse,
    GroupItem,
    GroupListResponse,
    HealthResponse,
    StatsResponse,
)

router = APIRouter(tags=["Estadísticas y Salud"])


@router.get("/api/stats", response_model=StatsResponse)
def get_portfolio_stats():
    """
    KPIs globales a nivel de cartera ejecutiva:
    Total de empresas analizadas, desglose por estado, tasa de riesgo, media/mediana de solvencia
    y volumen acumulado de facturas en mora.
    """
    # Métricas agregadas de empresas y scores
    score_stats = query_one("""
        SELECT 
            count(*) AS total_companies,
            MAX(as_of) AS latest_as_of,
            ROUND(AVG(score), 2) AS average_score,
            ROUND(MEDIAN(score), 2) AS median_score,
            count(*) FILTER (WHERE state IN ('DETERIORO', 'TORCIENDOSE', 'BACHE')) AS risk_companies_count
        FROM v_latest_company_scores;
    """)

    total_companies = score_stats["total_companies"] if score_stats else 0
    latest_as_of = str(score_stats["latest_as_of"]) if score_stats and score_stats["latest_as_of"] else "2026-09-01"
    risk_count = score_stats["risk_companies_count"] if score_stats else 0
    risk_pct = round((risk_count / total_companies * 100.0), 2) if total_companies > 0 else 0.0
    avg_score = float(score_stats["average_score"]) if score_stats and score_stats["average_score"] is not None else 0.0
    med_score = float(score_stats["median_score"]) if score_stats and score_stats["median_score"] is not None else 0.0

    # Distribución por estados
    dist_rows = query_dicts("""
        SELECT state, count(*) AS count
        FROM v_latest_company_scores
        GROUP BY state
        ORDER BY count DESC;
    """)
    distribution = {row["state"]: row["count"] for row in dist_rows}

    # Métricas de facturación y mora
    inv_stats = query_one("""
        SELECT 
            count(*) AS total_invoices,
            COALESCE(SUM(pending_amount) FILTER (WHERE status = 'overdue' OR (due_date < '2026-09-01' AND (paid_date IS NULL OR paid_date > due_date))), 0.0) AS total_overdue_volume
        FROM invoices;
    """)
    total_invoices = inv_stats["total_invoices"] if inv_stats else 0
    total_overdue = round(float(inv_stats["total_overdue_volume"]), 2) if inv_stats else 0.0

    # Totales de transacciones y alertas
    trans_row = query_one("SELECT count(*) AS cnt FROM transactions;")
    total_trans = trans_row["cnt"] if trans_row else 0

    alerts_row = query_one("SELECT count(*) AS cnt FROM alerts;")
    total_alerts = alerts_row["cnt"] if alerts_row else 0

    return StatsResponse(
        total_companies=total_companies,
        latest_as_of=latest_as_of,
        distribution_by_state=distribution,
        risk_companies_count=risk_count,
        risk_percentage=risk_pct,
        average_score=avg_score,
        median_score=med_score,
        total_overdue_volume=total_overdue,
        total_invoices_count=total_invoices,
        total_transactions_count=total_trans,
        total_alerts_count=total_alerts,
    )


@router.get("/api/groups", response_model=GroupListResponse)
def get_groups():
    """
    Lista los grupos corporativos con métricas agregadas de empresas, score medio y riesgo.
    """
    rows = query_dicts("""
        SELECT 
            g.group_id,
            g.erp,
            count(s.company_id) AS company_count,
            ROUND(COALESCE(AVG(s.score), 0.0), 2) AS average_score,
            count(s.company_id) FILTER (WHERE s.state IN ('DETERIORO', 'TORCIENDOSE', 'BACHE')) AS risk_companies_count
        FROM groups g
        LEFT JOIN v_latest_company_scores s ON g.group_id = s.group_id
        GROUP BY g.group_id, g.erp
        ORDER BY company_count DESC, average_score ASC;
    """)

    groups = [
        GroupItem(
            group_id=row["group_id"],
            erp=row.get("erp"),
            company_count=int(row["company_count"]),
            average_score=float(row["average_score"]),
            risk_companies_count=int(row["risk_companies_count"]),
        )
        for row in rows
    ]

    return GroupListResponse(total=len(groups), groups=groups)


def normalize_group_id(raw_id: str) -> str:
    cleaned = raw_id.strip().upper()
    if cleaned.startswith("GROUP_") and cleaned[6:].isdigit():
        return f"GROUP_{cleaned[6:].zfill(4)}"
    elif cleaned.startswith("GROUP") and cleaned[5:].isdigit():
        return f"GROUP_{cleaned[5:].zfill(4)}"
    elif cleaned.isdigit():
        return f"GROUP_{cleaned.zfill(4)}"
    return cleaned


@router.get("/api/groups/{id}", response_model=GroupDetailResponse)
def get_group_detail(id: str):
    """
    Ficha analítica completa de un grupo corporativo:
    Score consolidado (65% media + 35% filial más débil), penalización por contagio y filiales.
    """
    gid = normalize_group_id(id)

    # Verificar existencia del grupo
    grp = query_one("SELECT group_id, erp FROM groups WHERE group_id = ?;", (gid,))
    if not grp:
        check_comp = query_one("SELECT 1 FROM companies WHERE group_id = ? LIMIT 1;", (gid,))
        if not check_comp:
            raise HTTPException(status_code=404, detail=f"Grupo '{gid}' no encontrado")
        grp = {"group_id": gid, "erp": None}

    # Obtener todas las filiales y sus scores en el último corte
    rows = query_dicts("""
        SELECT 
            company_id, score, base_health, state, momentum, delta_3m,
            erp, has_erp, state_eligible
        FROM v_latest_company_scores
        WHERE group_id = ?
        ORDER BY score ASC;
    """, (gid,))

    if not rows:
        raise HTTPException(status_code=404, detail=f"No hay empresas registradas para el grupo '{gid}'")

    scores = [float(r["score"]) for r in rows]
    avg_score = round(sum(scores) / len(scores), 2)
    worst_row = rows[0]
    best_row = rows[-1]

    worst_score = float(worst_row["score"])
    best_score = float(best_row["score"])
    consolidated = round(0.65 * avg_score + 0.35 * worst_score, 2)
    contagion_penalty = round(max(0.0, (40.0 - worst_score) * 0.25), 2) if worst_score < 40.0 else 0.0

    risk_count = sum(1 for r in rows if str(r["state"]) in ('DETERIORO', 'TORCIENDOSE', 'BACHE'))
    eligible_count = sum(1 for r in rows if bool(r.get("state_eligible", True)))
    coverage_pct = round((eligible_count / len(rows)) * 100.0, 1)

    companies = [
        GroupCompanyItem(
            company_id=r["company_id"],
            score=round(float(r["score"]), 2),
            base_health=round(float(r["base_health"]), 2),
            state=str(r["state"]),
            momentum=round(float(r["momentum"]), 4),
            delta_3m=round(float(r["delta_3m"]), 2),
            erp=r.get("erp"),
            has_erp=bool(r.get("has_erp", False)),
            state_eligible=bool(r.get("state_eligible", True)),
        )
        for r in rows
    ]

    return GroupDetailResponse(
        group_id=gid,
        erp=grp.get("erp"),
        company_count=len(companies),
        average_score=avg_score,
        consolidated_score=consolidated,
        contagion_penalty=contagion_penalty,
        worst_company_id=worst_row["company_id"],
        worst_company_score=round(worst_score, 2),
        best_company_id=best_row["company_id"],
        best_company_score=round(best_score, 2),
        risk_companies_count=risk_count,
        data_coverage_percentage=coverage_pct,
        companies=companies,
    )


@router.get("/api/health", response_model=HealthResponse)
def health_check():
    """
    Comprueba la conectividad de DuckDB y el estado operativo del microservicio.
    """
    tables = query_dicts("SHOW TABLES;")
    return HealthResponse(
        status="ok",
        database=DB_PATH.name,
        tables_count=len(tables),
        timestamp=datetime.now().isoformat(),
    )
