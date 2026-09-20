"""
Endpoints de estadísticas globales, KPIs de cartera, grupos corporativos y salud del backend (X-Ray).
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from backend.calendar import DATA_CUTOFF, calendar_fields, closed_month_iso
from backend.database import DB_PATH, query_dicts, query_one
from backend.schemas import (
    DataCalendar,
    GroupCompanyItem,
    PortfolioCompanyItem,
    PortfolioHistogramBucket,
    PortfolioResponse,
    PortfolioSegment,
    PortfolioTrajectoryPoint,
    GroupDetailResponse,
    GroupItem,
    GroupListResponse,
    HealthResponse,
    StatsResponse,
)

router = APIRouter(tags=["Estadísticas y Salud"])


@router.get("/api/calendar", response_model=DataCalendar)
def get_data_calendar():
    """
    Tres relojes del dataset congelado.

    `as_of` es el corte oficial (snapshot ERP/saldos y último score).
    `last_closed_month` es agosto de 2026, el último ciclo completo de
    transacciones. `partial_month` es el 1-sep: un día suelto que no entra
    en medias ni comparativas mensuales.
    """
    return DataCalendar(**calendar_fields())


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
    latest_as_of = str(score_stats["latest_as_of"]) if score_stats and score_stats["latest_as_of"] else DATA_CUTOFF.isoformat()
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
        calendar=DataCalendar(**calendar_fields()),
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


# ── Cartera Embat ──────────────────────────────────────────────────────
# Segmentación determinista sobre el último corte. Es una regla, no un modelo:
# la misma que aplica el front en lib/cartera.ts, y debe cambiarse en los dos sitios.
#   APOSTAR   → sana y creciendo: candidata a línea de crédito / módulo gratis.
#   VIGILAR   → se tuerce o deteriora: retención, ofrecer ayuda antes de perderla.
#   ACOMPANAR → bache puntual: seguimiento, sin actuar todavía.
SEGMENT_SQL = """
    CASE
        WHEN state_eligible AND score >= 60
             AND (state IN ('MEJORANDO', 'RECUPERACION') OR delta_3m >= 10) THEN 'APOSTAR'
        WHEN state IN ('TORCIENDOSE', 'DETERIORO') THEN 'VIGILAR'
        WHEN state = 'BACHE' THEN 'ACOMPANAR'
        ELSE NULL
    END
"""

SEGMENTS = [
    ("APOSTAR", "Apostar", "Sana y creciendo. Candidata a línea de crédito o módulo sin coste."),
    ("VIGILAR", "Vigilar", "Empieza a torcerse. Retención: ofrecer ayuda antes de perder al cliente."),
    ("ACOMPANAR", "Acompañar", "Bache puntual. Seguimiento cercano, sin actuar todavía."),
]

PORTFOLIO_COLS = f"""
    company_id, group_id, erp, score, state, momentum, delta_3m, health_band, state_eligible,
    {SEGMENT_SQL} AS segment
"""


def _portfolio_item(row) -> PortfolioCompanyItem:
    return PortfolioCompanyItem(
        company_id=row["company_id"],
        group_id=row["group_id"],
        erp=row.get("erp"),
        score=round(float(row["score"]), 2),
        state=str(row["state"]),
        momentum=round(float(row["momentum"]), 4),
        delta_3m=round(float(row["delta_3m"]), 2),
        health_band=row.get("health_band"),
        state_eligible=bool(row["state_eligible"]),
        segment=row.get("segment"),
    )


@router.get("/api/portfolio", response_model=PortfolioResponse)
def get_portfolio(top: int = 10, per_segment: int = 8):
    """
    Vista de cartera para Embat en una sola llamada: KPIs, distribución, histograma,
    trayectoria media a 24 meses, rankings y segmentos de oportunidad.
    Los rankings solo consideran empresas con historia suficiente (state_eligible).
    """
    top = max(1, min(top, 50))
    per_segment = max(1, min(per_segment, 50))

    kpi = query_one("""
        SELECT
            count(*) AS total_companies,
            count(*) FILTER (WHERE state_eligible) AS eligible_companies,
            MAX(as_of) AS latest_as_of,
            ROUND(AVG(score) FILTER (WHERE state_eligible), 2) AS average_score,
            ROUND(MEDIAN(score) FILTER (WHERE state_eligible), 2) AS median_score,
            count(*) FILTER (WHERE state IN ('DETERIORO', 'TORCIENDOSE', 'BACHE')) AS risk_companies_count,
            count(*) FILTER (WHERE state IN ('MEJORANDO', 'RECUPERACION')) AS improving_companies_count
        FROM v_latest_company_scores;
    """) or {}
    as_of = str(kpi.get("latest_as_of") or DATA_CUTOFF.isoformat())

    alerts_row = query_one("SELECT count(*) AS cnt FROM alerts WHERE as_of = ?;", (as_of,))

    dist_state = {r["state"]: int(r["count"]) for r in query_dicts(
        "SELECT state, count(*) AS count FROM v_latest_company_scores GROUP BY state ORDER BY count DESC;")}
    dist_band = {str(r["health_band"] or "SIN_BANDA"): int(r["count"]) for r in query_dicts(
        "SELECT health_band, count(*) AS count FROM v_latest_company_scores GROUP BY health_band ORDER BY count DESC;")}

    hist_rows = query_dicts("""
        SELECT CAST(LEAST(FLOOR(score / 10) * 10, 90) AS INTEGER) AS bucket, count(*) AS count
        FROM v_latest_company_scores
        WHERE state_eligible
        GROUP BY bucket ORDER BY bucket;
    """)
    hist_map = {int(r["bucket"]): int(r["count"]) for r in hist_rows}
    histogram = [PortfolioHistogramBucket(bucket=b, count=hist_map.get(b, 0)) for b in range(0, 100, 10)]

    # Media de la cartera mes a mes. Los primeros meses nadie es elegible (arranque
    # del motor), así que se cae a la media de todas para no dejar huecos.
    traj_rows = query_dicts("""
        SELECT
            as_of,
            ROUND(COALESCE(AVG(score) FILTER (WHERE state_eligible), AVG(score)), 2) AS average_score,
            ROUND(COALESCE(MEDIAN(score) FILTER (WHERE state_eligible), MEDIAN(score)), 2) AS median_score,
            count(*) FILTER (WHERE state_eligible) AS eligible_companies
        FROM company_scores
        GROUP BY as_of ORDER BY as_of;
    """)
    trajectory = [
        PortfolioTrajectoryPoint(
            as_of=str(r["as_of"]),
            closed_month=closed_month_iso(r["as_of"]),
            average_score=float(r["average_score"]),
            median_score=float(r["median_score"]),
            eligible_companies=int(r["eligible_companies"]),
        )
        for r in traj_rows
    ]

    def ranking(order: str) -> list:
        rows = query_dicts(f"""
            SELECT {PORTFOLIO_COLS}
            FROM v_latest_company_scores
            WHERE state_eligible
            ORDER BY {order}, company_id
            LIMIT ?;
        """, (top,))
        return [_portfolio_item(r) for r in rows]

    segments = []
    for key, label, action in SEGMENTS:
        cnt = query_one(
            f"SELECT count(*) AS cnt FROM v_latest_company_scores WHERE {SEGMENT_SQL} = ?;", (key,)
        ) or {"cnt": 0}
        # Dentro del segmento, primero quien más se mueve en la dirección que importa.
        order = "delta_3m DESC" if key == "APOSTAR" else "delta_3m ASC"
        rows = query_dicts(f"""
            SELECT {PORTFOLIO_COLS}
            FROM v_latest_company_scores
            WHERE {SEGMENT_SQL} = ?
            ORDER BY {order}, score DESC, company_id
            LIMIT ?;
        """, (key, per_segment))
        segments.append(PortfolioSegment(
            key=key, label=label, action=action,
            count=int(cnt["cnt"]), items=[_portfolio_item(r) for r in rows],
        ))

    return PortfolioResponse(
        as_of=as_of,
        calendar=DataCalendar(**calendar_fields()),
        total_companies=int(kpi.get("total_companies") or 0),
        eligible_companies=int(kpi.get("eligible_companies") or 0),
        average_score=float(kpi.get("average_score") or 0.0),
        median_score=float(kpi.get("median_score") or 0.0),
        risk_companies_count=int(kpi.get("risk_companies_count") or 0),
        improving_companies_count=int(kpi.get("improving_companies_count") or 0),
        alerts_last_month=int(alerts_row["cnt"]) if alerts_row else 0,
        distribution_by_state=dist_state,
        distribution_by_band=dist_band,
        histogram=histogram,
        trajectory=trajectory,
        top_score=ranking("score DESC"),
        top_growth=ranking("delta_3m DESC"),
        top_decline=ranking("delta_3m ASC"),
        segments=segments,
    )


@router.get("/api/groups", response_model=GroupListResponse)
def get_groups(limit: int = Query(250, ge=1, le=500, description="Cantidad máxima de grupos a devolver")):
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
        ORDER BY company_count DESC, average_score ASC, g.group_id ASC
        LIMIT ?;
    """, (limit,))

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

    total_row = query_one("SELECT count(*) AS total FROM groups;")
    total = int(total_row["total"]) if total_row else 0
    return GroupListResponse(total=total, groups=groups)


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
