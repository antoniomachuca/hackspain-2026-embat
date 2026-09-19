"""
Endpoints para la gestión, cartera analítica y detalle de empresas (X-Ray).
"""

import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response

from algorythm.telegram_charts import generate_company_chart
from backend.database import normalize_company_id, query_dicts, query_one
from backend.schemas import (
    CompanyDetailResponse,
    CompanyHistoryResponse,
    CompanyInvoicesResponse,
    CompanyListItem,
    CompanyListResponse,
    CompanyWaterfall,
    HistoryPoint,
    InvoiceItem,
)

router = APIRouter(prefix="/api/companies", tags=["Empresas y Cartera"])


@router.get("", response_model=CompanyListResponse)
def get_companies(
    state: Optional[str] = Query(None, description="Filtrar por estado (DETERIORO, TORCIENDOSE, BACHE, ESTABLE, MEJORANDO, SOLVENTE)"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Puntuación mínima"),
    max_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Puntuación máxima"),
    group_id: Optional[str] = Query(None, description="Filtrar por ID de grupo corporativo"),
    has_erp: Optional[bool] = Query(None, description="Filtrar por presencia de integración ERP"),
    search: Optional[str] = Query(None, description="Búsqueda por prefijo/subcadena en company_id o group_id"),
    order_by: str = Query("score", description="Campo de ordenación", pattern="^(score|company_id|group_id|momentum|delta_3m|data_confidence_index)$"),
    order_dir: str = Query("desc", description="Dirección ('asc' o 'desc')", pattern="^(asc|desc|ASC|DESC)$"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad máxima de resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
):
    """
    Lista paginada y filtrable de empresas en el último corte mensual analítico (2026-09-01).
    Utilizada para alimentar la tabla de cartera del CFO.
    """
    conditions = []
    params = []

    if state:
        conditions.append("state = ?")
        params.append(state.strip().upper())
    if min_score is not None:
        conditions.append("score >= ?")
        params.append(min_score)
    if max_score is not None:
        conditions.append("score <= ?")
        params.append(max_score)
    if group_id:
        conditions.append("group_id = ?")
        params.append(group_id.strip().upper())
    if has_erp is not None:
        conditions.append("has_erp = ?")
        params.append(has_erp)
    if search:
        s = f"%{search.strip().upper()}%"
        conditions.append("(company_id LIKE ? OR group_id LIKE ?)")
        params.extend([s, s])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Conteo total con filtros
    count_sql = f"SELECT count(*) AS total FROM v_latest_company_scores {where_clause};"
    count_row = query_one(count_sql, tuple(params))
    total = count_row["total"] if count_row else 0

    # Consulta paginada ordenada
    safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"
    data_sql = f"""
        SELECT *
        FROM v_latest_company_scores
        {where_clause}
        ORDER BY {order_by} {safe_order_dir}
        LIMIT ? OFFSET ?;
    """
    query_params = tuple(params + [limit, offset])
    rows = query_dicts(data_sql, query_params)

    items = [
        CompanyListItem(
            company_id=row["company_id"],
            group_id=row["group_id"],
            currency=row["currency"],
            country=row.get("country"),
            erp=row.get("erp"),
            has_erp=bool(row["has_erp"]),
            as_of=str(row["as_of"]),
            score=round(float(row["score"]), 2),
            base_health=round(float(row["base_health"]), 2),
            state=str(row["state"]),
            momentum=round(float(row["momentum"]), 4),
            delta_3m=round(float(row["delta_3m"]), 2),
            health_band=row.get("health_band"),
            data_confidence_index=round(float(row["data_confidence_index"]), 4),
            state_eligible=bool(row["state_eligible"]),
            liquidity_points=round(float(row["liquidity_points"]), 2),
            collections_points=round(float(row["collections_points"]), 2),
            debt_points=round(float(row["debt_points"]), 2),
            momentum_points=round(float(row["momentum_points"]), 2),
            growth_points=round(float(row["growth_points"]), 2),
            fragility_points=round(float(row["fragility_points"]), 2),
            clipping_points=round(float(row["clipping_points"]), 2),
        )
        for row in rows
    ]

    return CompanyListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{id}", response_model=CompanyDetailResponse)
def get_company_detail(id: str):
    """
    Ficha ejecutiva completa de una empresa:
    Score actual, estado, variación 3M, desglose Waterfall, saldos de tesorería y facturas vencidas.
    """
    cid = normalize_company_id(id)

    # 1. Datos analíticos del último corte
    comp = query_one("SELECT * FROM v_latest_company_scores WHERE company_id = ?", (cid,))
    if not comp:
        raise HTTPException(status_code=404, detail=f"Empresa '{cid}' no encontrada en el catálogo")

    # 2. Saldos bancarios consolidados
    bal_row = query_one(
        "SELECT COALESCE(SUM(balance), 0.0) AS total_balance FROM balances WHERE company_id = ?",
        (cid,)
    )
    total_balance = float(bal_row["total_balance"]) if bal_row else None

    # 3. Resumen de facturas e impagos ERP
    inv_row = query_one("""
        SELECT 
            count(*) FILTER (WHERE status = 'overdue' OR (due_date < '2026-09-01' AND (paid_date IS NULL OR paid_date > due_date))) AS overdue_count,
            COALESCE(SUM(pending_amount) FILTER (WHERE status = 'overdue' OR (due_date < '2026-09-01' AND (paid_date IS NULL OR paid_date > due_date))), 0.0) AS overdue_amount,
            COALESCE(SUM(pending_amount), 0.0) AS total_pending
        FROM invoices
        WHERE company_id = ?;
    """, (cid,))

    overdue_count = int(inv_row["overdue_count"]) if inv_row else 0
    overdue_amount = round(float(inv_row["overdue_amount"]), 2) if inv_row else 0.0
    total_pending = round(float(inv_row["total_pending"]), 2) if inv_row else 0.0

    # 4. Última alerta de riesgo registrada
    alert_row = query_one("""
        SELECT 
            alert_id, company_id, group_id, as_of, state, severity, direction, score, delta_score, momentum, drivers_json, created_at
        FROM alerts
        WHERE company_id = ?
        ORDER BY as_of DESC, created_at DESC
        LIMIT 1;
    """, (cid,))

    latest_alert = None
    if alert_row:
        drivers = []
        if alert_row.get("drivers_json"):
            try:
                drivers = json.loads(alert_row["drivers_json"])
            except Exception:
                pass
        latest_alert = {
            "alert_id": alert_row["alert_id"],
            "as_of": str(alert_row["as_of"]),
            "state": alert_row["state"],
            "severity": alert_row["severity"],
            "direction": alert_row["direction"],
            "score": round(float(alert_row["score"]), 2),
            "delta_score": round(float(alert_row["delta_score"]), 2),
            "momentum": round(float(alert_row["momentum"]), 4),
            "drivers": drivers,
        }

    # 5. Recomendación financiera inteligente
    suggested_action = None
    l_pts = float(comp["liquidity_points"])
    f_pts = float(comp["fragility_points"])
    c_pts = float(comp["collections_points"])

    if l_pts < 25.0:
        suggested_action = "Anticipar facturas pendientes con Embat para restaurar liquidez a 30 días."
    elif abs(f_pts) > 3.0:
        suggested_action = "Activar línea de crédito revolving de tesorería para absorber picos de volatilidad."
    elif c_pts < 15.0:
        suggested_action = "Conectar conciliación automática ERP para reducir DSO y recobrar impagos."
    elif comp["state"] in ("DETERIORO", "TORCIENDOSE"):
        suggested_action = "Intervención prioritaria con inyección de circulante antes del próximo vencimiento."

    # 6. Ratios operacionales reales (DSO, DPO, Días de caja, Facturación anual)
    dso = 0.0
    dpo = 0.0
    dias_caja = 0.0
    annual_revenue = 0.0
    line_utilization = 0.0
    customer_hhi = None
    daily_burn = 0.0

    try:
        import numpy as np
        from algorythm.levers_objects import get_company_objects
        obj = get_company_objects(cid)
        if obj:
            if obj.receipts_m23 > 0:
                annual_revenue = round(float(obj.receipts_m23) * 12.0, 2)
                dso = round(float(obj.ar_pending_eur) / (float(obj.receipts_m23) / 30.0), 1)
            elif total_pending > 0:
                annual_revenue = round(total_pending * 4.0, 2)
                dso = 45.0

            if obj.ap_expenses_m23 > 0:
                dpo = round(float(obj.ap_pending_eur) / (float(obj.ap_expenses_m23) / 30.0), 1)

            monthly_expenses = float(obj.opex_m23) + float(obj.ap_expenses_m23)
            if monthly_expenses > 0:
                daily_burn = round(monthly_expenses / 30.0, 2)
                cash = float(obj.checking_balance) if obj.checking_balance is not None and not np.isnan(obj.checking_balance) else (total_balance or 0.0)
                if daily_burn > 0:
                    dias_caja = round(max(0.0, cash) / daily_burn, 1)

            if obj.loc_granted > 0:
                line_utilization = round((float(obj.loc_outstanding) / float(obj.loc_granted)) * 100.0, 1)

            if obj.hhi is not None and not np.isnan(obj.hhi):
                customer_hhi = round(float(obj.hhi), 4)
    except Exception:
        pass

    return CompanyDetailResponse(
        company_id=comp["company_id"],
        group_id=comp["group_id"],
        currency=comp["currency"],
        country=comp.get("country"),
        erp=comp.get("erp"),
        has_erp=bool(comp["has_erp"]),
        created_at=str(comp.get("company_created_at")) if comp.get("company_created_at") else None,
        as_of=str(comp["as_of"]),
        score=round(float(comp["score"]), 2),
        base_health=round(float(comp["base_health"]), 2),
        state=str(comp["state"]),
        momentum=round(float(comp["momentum"]), 4),
        delta_3m=round(float(comp["delta_3m"]), 2),
        health_band=comp.get("health_band"),
        data_confidence_index=round(float(comp["data_confidence_index"]), 4),
        state_eligible=bool(comp["state_eligible"]),
        waterfall=CompanyWaterfall(
            liquidity_points=round(float(comp["liquidity_points"]), 2),
            collections_points=round(float(comp["collections_points"]), 2),
            debt_points=round(float(comp["debt_points"]), 2),
            momentum_points=round(float(comp["momentum_points"]), 2),
            growth_points=round(float(comp["growth_points"]), 2),
            fragility_points=round(float(comp["fragility_points"]), 2),
            clipping_points=round(float(comp["clipping_points"]), 2),
        ),
        total_balance=total_balance,
        overdue_invoices_count=overdue_count,
        overdue_invoices_amount=overdue_amount,
        total_pending_amount=total_pending,
        latest_alert=latest_alert,
        suggested_action=suggested_action,
        dso=dso,
        dpo=dpo,
        dias_caja=dias_caja,
        annual_revenue=annual_revenue,
        line_utilization=line_utilization,
        customer_hhi=customer_hhi,
        daily_burn=daily_burn,
    )


@router.get("/{id}/history", response_model=CompanyHistoryResponse)
def get_company_history(
    id: str,
    months: int = Query(24, ge=1, le=48, description="Número de meses de histórico (por defecto 24)"),
):
    """
    Devuelve la serie temporal mensual del score, componentes y momentum.
    Diseñado para alimentar directamente gráficos de líneas/área en Recharts o Chart.js.
    """
    cid = normalize_company_id(id)

    rows = query_dicts("""
        SELECT 
            as_of, score, base_health, state, momentum,
            liquidity_points, collections_points, debt_points,
            momentum_points, growth_points, fragility_points,
            data_confidence_index
        FROM company_scores
        WHERE company_id = ?
        ORDER BY as_of ASC;
    """, (cid,))

    if not rows:
        raise HTTPException(status_code=404, detail=f"Empresa '{cid}' no encontrada")

    # Tomar los últimos N meses solicitados
    if len(rows) > months:
        rows = rows[-months:]

    history = [
        HistoryPoint(
            as_of=str(row["as_of"]),
            score=round(float(row["score"]), 2),
            base_health=round(float(row["base_health"]), 2),
            state=str(row["state"]),
            momentum=round(float(row["momentum"]), 4),
            liquidity_points=round(float(row["liquidity_points"]), 2),
            collections_points=round(float(row["collections_points"]), 2),
            debt_points=round(float(row["debt_points"]), 2),
            momentum_points=round(float(row["momentum_points"]), 2),
            growth_points=round(float(row["growth_points"]), 2),
            fragility_points=round(float(row["fragility_points"]), 2),
            data_confidence_index=round(float(row["data_confidence_index"]), 4),
        )
        for row in rows
    ]

    return CompanyHistoryResponse(company_id=cid, months=len(history), history=history)


@router.get("/{id}/invoices", response_model=CompanyInvoicesResponse)
def get_company_invoices(
    id: str,
    status: Optional[str] = Query(None, description="Filtrar por estado ('overdue', 'pending', 'paid')"),
    limit: int = Query(20, ge=1, le=200, description="Facturas por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
):
    """
    Detalle de facturación e impagos ERP de la empresa.
    Permite auditar la causa raíz del estrés comercial o retraso de cobros.
    """
    cid = normalize_company_id(id)

    conditions = ["company_id = ?"]
    params = [cid]

    if status:
        stat_norm = status.strip().lower()
        if stat_norm == "overdue":
            conditions.append("(status = 'overdue' OR (due_date < '2026-09-01' AND (paid_date IS NULL OR paid_date > due_date)))")
        else:
            conditions.append("status = ?")
            params.append(stat_norm)

    where_clause = f"WHERE {' AND '.join(conditions)}"

    # Agregados generales de la empresa
    summary_sql = """
        SELECT 
            count(*) AS total_count,
            count(*) FILTER (WHERE status = 'overdue' OR (due_date < '2026-09-01' AND (paid_date IS NULL OR paid_date > due_date))) AS overdue_count,
            COALESCE(SUM(pending_amount), 0.0) AS total_pending
        FROM invoices
        WHERE company_id = ?;
    """
    summary_row = query_one(summary_sql, (cid,))
    overdue_count = int(summary_row["overdue_count"]) if summary_row else 0
    total_pending = round(float(summary_row["total_pending"]), 2) if summary_row else 0.0

    # Total de facturas según filtro
    count_filtered_sql = f"SELECT count(*) AS count_filtered FROM invoices {where_clause};"
    count_row = query_one(count_filtered_sql, tuple(params))
    total_filtered = count_row["count_filtered"] if count_row else 0

    # Facturas paginadas
    inv_sql = f"""
        SELECT 
            invoice_id, company_id, document_type, issue_date, due_date, paid_date,
            total_amount, pending_amount, currency, status, concept, counterparty_id
        FROM invoices
        {where_clause}
        ORDER BY due_date DESC, issue_date DESC
        LIMIT ? OFFSET ?;
    """
    rows = query_dicts(inv_sql, tuple(params + [limit, offset]))

    invoices = [
        InvoiceItem(
            invoice_id=row["invoice_id"],
            company_id=row["company_id"],
            document_type=row.get("document_type"),
            issue_date=str(row["issue_date"]) if row.get("issue_date") else None,
            due_date=str(row["due_date"]) if row.get("due_date") else None,
            paid_date=str(row["paid_date"]) if row.get("paid_date") else None,
            total_amount=round(float(row["total_amount"]), 2),
            pending_amount=round(float(row["pending_amount"]), 2),
            currency=row.get("currency"),
            status=str(row["status"]),
            concept=row.get("concept"),
            counterparty_id=row.get("counterparty_id"),
        )
        for row in rows
    ]

    return CompanyInvoicesResponse(
        company_id=cid,
        total=total_filtered,
        overdue_count=overdue_count,
        total_pending_amount=total_pending,
        limit=limit,
        offset=offset,
        invoices=invoices,
    )


@router.get("/{id}/chart")
def get_company_chart_png(id: str):
    """
    Genera y devuelve la imagen PNG de la trayectoria de 24 meses generada por telegram_charts.py.
    Permite incrustar la previsualización gráfica instantáneamente en Next.js con una etiqueta <img>.
    """
    cid = normalize_company_id(id)
    try:
        png_bytes = generate_company_chart(cid)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar gráfica: {str(e)}")

    return Response(content=png_bytes, media_type="image/png")
