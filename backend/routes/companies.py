"""
Endpoints para la gestión, cartera analítica y detalle de empresas (X-Ray).
"""

import json
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response

from algorithm.score_decompose import history_with_reparto
from algorithm.score_episodes import empty_company_episodes, episodes_for_company
from algorithm.telegram_charts import generate_company_chart
from backend.database import get_cursor, normalize_company_id, query_dicts, query_one
from backend.routes.forecasts import _load_banks
from backend.routes.stats import normalize_group_id
from backend.schemas import (
    CompanyDetailResponse,
    CompanyHistoryResponse,
    CompanyInvoicesResponse,
    CompanyListItem,
    CompanyListResponse,
    CompanyPeersResponse,
    CompanyWaterfall,
    HistoryPoint,
    InvoiceItem,
    PeerPoint,
)
from backend.calendar import LAST_CLOSED_MONTH, closed_month_iso
from forecasting.structural import as_of_from_origin

router = APIRouter(prefix="/api/companies", tags=["Empresas y Cartera"])

RESULTS_DIR = Path(__file__).resolve().parents[2] / "algorithm" / "engine_results"


@lru_cache(maxsize=4)
def _read_score_panels(path: str, modified_ns: int) -> Dict[str, Any]:
    import numpy as np
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def _results_dir() -> Path:
    return Path(os.environ.get("XRAY_RESULTS_DIR", str(RESULTS_DIR)))


def _episodes_for(cid: str) -> Dict[str, Any]:
    """Episodios al vuelo sobre el recorte de la empresa. Vacío si no hay paneles."""
    panels_path = _results_dir() / "score_panels.npz"
    try:
        panels = _read_score_panels(str(panels_path), panels_path.stat().st_mtime_ns)
    except (FileNotFoundError, KeyError, ValueError, OSError):
        return empty_company_episodes()
    bank = None
    ap = None
    try:
        from algorithm.bank_panels import get_company_bank_slice
        bank_path = _results_dir() / "bank_inputs.npz"
        bank = get_company_bank_slice(cid, path=bank_path if bank_path.exists() else None)
    except (FileNotFoundError, KeyError, OSError):
        bank = None
    try:
        from algorithm.levers_objects import OBJECTS_PATH, ap_pending_vector
        if OBJECTS_PATH.exists():
            ap = ap_pending_vector([cid])
    except (FileNotFoundError, KeyError, OSError):
        ap = None
    try:
        return episodes_for_company(cid, panels, bank=bank, ap_pending=ap)
    except (KeyError, ValueError):
        return empty_company_episodes()


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
    Lista paginada y filtrable de empresas en el último corte analítico (as_of=2026-09-01).
    Ese corte cierra el mes de agosto de 2026; septiembre es foto de 1 día y no entra aquí.
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
        params.append(normalize_group_id(group_id))
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
        ORDER BY {order_by} {safe_order_dir}, company_id ASC
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
        from algorithm.levers_objects import get_company_objects
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

    # 7. Episodios de cambio (mismo recorte que el score; vacío si no hay paneles)
    ep_data = _episodes_for(cid)

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
        episodios=ep_data.get("episodios", []),
        episodio_destacado=ep_data.get("episodio_destacado"),
        perspectivas_sin_aviso=ep_data.get("perspectivas_sin_aviso", []),
        trayectoria_marcas=ep_data.get("trayectoria_marcas"),
        parametros_episodios=ep_data.get("parametros"),
        last_closed_month=LAST_CLOSED_MONTH.isoformat(),
    )


_REPARTO_CACHE: Dict[str, Dict[str, Any]] = {}
_REPARTO_LOCK = threading.Lock()


def _as_of_key(value) -> str:
    return str(value)[:10]


def _company_panel(bank, row):
    panel = {}
    for key, value in bank.items():
        ndim = getattr(value, "ndim", 0)
        panel[key] = value[row:row + 1].copy() if ndim == 2 else value
    return panel


def _reparto_lookup(cid: str, rows, banks=None):
    """DuckDB as_of → reparto, paired by series index.

    The bank panel labels months at the start of each interval (2024-09 … 2026-08);
    company_scores uses the following first-of-month (2024-10 … 2026-09). Same 24
    cuts, last score 45.6 both ways. Join with DuckDB dates so the chart mes matches.
    The public series also expose `closed_month` (bank-panel clock) so the UI never
    paints September 2026 as a complete month.
    """
    tables = banks if banks is not None else _load_banks()
    if cid not in tables or not rows:
        return {}
    bank, row = tables[cid]
    panel = _company_panel(bank, row)
    n_bank = int(panel["receipts"].shape[1])
    duck = [_as_of_key(item["as_of"]) for item in rows]
    if len(duck) >= n_bank:
        labels = duck[-n_bank:]
    else:
        pad = n_bank - len(duck)
        labels = [as_of_from_origin(step) for step in range(pad)] + duck
    body = history_with_reparto(panel, labels, company_id=cid, row=0)
    return {point["as_of"]: point["reparto"] for point in body["history"]}


def _cached_reparto_lookup(cid: str, rows):
    with _REPARTO_LOCK:
        hit = _REPARTO_CACHE.get(cid)
    if hit is not None:
        return hit
    found = _reparto_lookup(cid, rows)
    with _REPARTO_LOCK:
        _REPARTO_CACHE[cid] = found
    return found


@router.get("/{id}/history", response_model=CompanyHistoryResponse)
def get_company_history(
    id: str,
    months: int = Query(24, ge=1, le=48, description="Número de meses de histórico (por defecto 24)"),
):
    """
    Devuelve la serie temporal mensual del score, componentes y momentum.
    Cada punto anida `reparto` (bache vs tendencia) calculado sobre el panel bancario.
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

    by_as_of = _cached_reparto_lookup(cid, rows)

    # Tomar los últimos N meses solicitados
    if len(rows) > months:
        rows = rows[-months:]

    history = [
        HistoryPoint(
            as_of=_as_of_key(row["as_of"]),
            closed_month=closed_month_iso(row["as_of"]),
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
            reparto=by_as_of.get(_as_of_key(row["as_of"])),
        )
        for row in rows
    ]

    return CompanyHistoryResponse(
        company_id=cid,
        months=len(history),
        last_closed_month=LAST_CLOSED_MONTH.isoformat(),
        history=history,
    )


# -------------------------------------------------------------
# Cache y cálculo de Grupo de Pares (Peer Benchmark)
# -------------------------------------------------------------

_PEER_CACHE: Optional[Dict[str, Any]] = None
_PEER_LOCK = threading.Lock()


def _get_peer_data() -> Dict[str, Any]:
    """
    Carga y cachea la agrupación de cuartiles y la mediana mensual histórica
    de cada cuartil a partir de transacciones e historial de scores en DuckDB.
    """
    global _PEER_CACHE
    if _PEER_CACHE is not None:
        return _PEER_CACHE

    with _PEER_LOCK:
        if _PEER_CACHE is not None:
            return _PEER_CACHE

        with get_cursor() as cur:
            # 1. Cuartil por volumen de ingresos
            q_rows = cur.execute("""
                WITH comp_vol AS (
                    SELECT 
                        company_id,
                        NTILE(4) OVER (ORDER BY sum(case when amount > 0 then amount else 0 end) ASC) as quartile
                    FROM transactions
                    GROUP BY company_id
                )
                SELECT company_id, CAST(quartile AS INTEGER) as quartile FROM comp_vol;
            """).fetchall()
            company_quartiles = {str(r[0]): int(r[1]) for r in q_rows}

            # 2. Mediana mensual de scores por cuartil
            series_rows = cur.execute("""
                WITH comp_vol AS (
                    SELECT 
                        company_id,
                        NTILE(4) OVER (ORDER BY sum(case when amount > 0 then amount else 0 end) ASC) as quartile
                    FROM transactions
                    GROUP BY company_id
                )
                SELECT 
                    CAST(cv.quartile AS INTEGER) as quartile,
                    strftime(cs.as_of, '%Y-%m') as mes,
                    count(distinct cv.company_id) as n_companies,
                    round(COALESCE(median(case when cs.score != 50.0 then cs.score end), 50.0), 1) as median_score
                FROM company_scores cs
                JOIN comp_vol cv ON cs.company_id = cv.company_id
                GROUP BY cv.quartile, cs.as_of
                ORDER BY cv.quartile, cs.as_of;
            """).fetchall()

            quartile_labels = {
                1: "cuartil de tamaño Q1 (< 1M€)",
                2: "cuartil de tamaño Q2 (1M€ - 5M€)",
                3: "cuartil de tamaño Q3 (5M€ - 20M€)",
                4: "cuartil de tamaño Q4 (> 20M€)",
            }

            quartile_series: Dict[int, Dict[str, Any]] = {}
            for q_raw, mes, n, med in series_rows:
                q = int(q_raw)
                if q not in quartile_series:
                    quartile_series[q] = {
                        "n": int(n),
                        "label": quartile_labels.get(q, f"cuartil Q{q}"),
                        "history": [],
                    }
                quartile_series[q]["history"].append(
                    PeerPoint(mes=str(mes), closed_month=closed_month_iso(f"{mes}-01"), mediana=float(med))
                )

            # Suavizado de meses iniciales pre-operativos (2024-10 y 2024-11)
            for q, data in quartile_series.items():
                pts = data["history"]
                first_active = next((p.mediana for p in pts if p.mes >= "2024-12" and p.mediana != 50.0), 50.0)
                for p in pts:
                    if p.mes < "2024-12":
                        p.mediana = first_active

            _PEER_CACHE = {
                "company_quartiles": company_quartiles,
                "quartiles": quartile_series,
            }
            return _PEER_CACHE


@router.get("/{id}/peers", response_model=CompanyPeersResponse)
def get_company_peers(id: str):
    """
    Devuelve la trayectoria del grupo de pares (Peer Benchmark) para la empresa.
    Determina su cuartil de tamaño por volumen de facturación y devuelve la serie
    mensual de medianas agregada en DuckDB sobre las 1.286 empresas.
    """
    cid = normalize_company_id(id)
    cache = _get_peer_data()

    quartile = cache["company_quartiles"].get(cid)
    if quartile is None:
        comp = query_one("SELECT company_id FROM companies WHERE company_id = ?", (cid,))
        if not comp:
            raise HTTPException(status_code=404, detail=f"Empresa '{cid}' no encontrada")
        quartile = 1

    q_data = cache["quartiles"].get(quartile)
    if not q_data:
        raise HTTPException(status_code=404, detail=f"No hay datos de pares para el cuartil {quartile}")

    return CompanyPeersResponse(
        company_id=cid,
        quartile=quartile,
        label=q_data["label"],
        n_companies=q_data["n"],
        last_closed_month=LAST_CLOSED_MONTH.isoformat(),
        history=q_data["history"],
    )


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
        ORDER BY due_date DESC, issue_date DESC, invoice_id ASC
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
