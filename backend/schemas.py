"""
Modelos Pydantic v2 para validación y serialización de la API REST de X-Ray.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from backend.calendar import (
    DATA_CUTOFF,
    LAST_CLOSED_MONTH,
    PARTIAL_MONTH,
    PARTIAL_MONTH_DAYS,
    PARTIAL_MONTH_LABEL,
)


# -------------------------------------------------------------
# 1. Esquemas de Empresas y Cartera CFO
# -------------------------------------------------------------

class CompanyWaterfall(BaseModel):
    liquidity_points: float = Field(..., description="Puntos aportados por cobertura de liquidez (0..50)")
    collections_points: float = Field(..., description="Puntos aportados por calidad y rotación de cobros (0..30)")
    debt_points: float = Field(..., description="Puntos aportados por cobertura del servicio de deuda (0..20)")
    momentum_points: float = Field(..., description="Ajuste por inercia o tendencia reciente de caja (-15..+15)")
    growth_points: float = Field(..., description="Ajuste por crecimiento sostenible de facturación (-10..+10)")
    fragility_points: float = Field(..., description="Penalización por volatilidad y estrés de tesorería (-8..0)")
    clipping_points: float = Field(..., description="Ajuste de acotación para mantener el score en [0, 100]")


class CompanyListItem(BaseModel):
    company_id: str = Field(..., json_schema_extra={"example": "COMP_0010"})
    group_id: str = Field(..., json_schema_extra={"example": "GROUP_0055"})
    currency: str = Field(..., json_schema_extra={"example": "EUR"})
    country: Optional[str] = Field(None, json_schema_extra={"example": "ES"})
    erp: Optional[str] = Field(None, json_schema_extra={"example": "businessOne"})
    has_erp: bool = Field(..., json_schema_extra={"example": True})
    as_of: str = Field(..., json_schema_extra={"example": "2026-09-01"})
    score: float = Field(..., json_schema_extra={"example": 58.4})
    base_health: float = Field(..., json_schema_extra={"example": 60.1})
    state: str = Field(..., json_schema_extra={"example": "DETERIORO"})
    momentum: float = Field(..., json_schema_extra={"example": -0.21})
    delta_3m: float = Field(..., json_schema_extra={"example": -6.5})
    health_band: Optional[str] = Field(None, json_schema_extra={"example": "REGULAR"})
    data_confidence_index: float = Field(..., json_schema_extra={"example": 0.85})
    state_eligible: bool = Field(..., json_schema_extra={"example": True})
    liquidity_points: float = Field(...)
    collections_points: float = Field(...)
    debt_points: float = Field(...)
    momentum_points: float = Field(...)
    growth_points: float = Field(...)
    fragility_points: float = Field(...)
    clipping_points: float = Field(...)


class CompanyListResponse(BaseModel):
    total: int = Field(..., description="Total de empresas que cumplen los filtros")
    limit: int = Field(..., description="Límite por página")
    offset: int = Field(..., description="Desplazamiento aplicado")
    items: List[CompanyListItem] = Field(..., description="Lista de empresas")


# -------------------------------------------------------------
# 1b. Episodios de cambio (ver algorithm/EPISODIOS.md)
# -------------------------------------------------------------

class EpisodeSignal(BaseModel):
    senal: str
    antes: float
    en_deteccion: float
    delta_puntos: float


class EpisodeEscalada(BaseModel):
    as_of: str
    estado: str


class Episode(BaseModel):
    direccion: str = Field(..., description="deterioro | mejora")
    estado: str = Field(..., description="activo | cerrado")
    cierre: Optional[str] = None
    motivo_cierre: Optional[str] = None
    deteccion: str
    estado_deteccion: str
    score_deteccion: float
    escaladas: List[EpisodeEscalada] = []
    inicio_estimado: str
    referencia_base_health: float
    referencia_as_of: Optional[str] = None
    cambio_material: Optional[str] = None
    criterio: Optional[str] = None
    estado_confirmacion: str
    meses_anticipacion: Optional[int] = None
    perspectiva: Optional[Dict[str, Any]] = None
    senales: List[EpisodeSignal] = []
    familia: str = "salud"
    texto: str = ""


class TrayectoriaDeteccion(BaseModel):
    as_of: str
    state: str
    score: float
    direccion: str


class TrayectoriaMarcas(BaseModel):
    deteccion: Optional[TrayectoriaDeteccion] = None
    camino: Optional[Dict[str, Any]] = None
    texto: str = ""


class EpisodiosParametros(BaseModel):
    persistence_months: int = 3
    neutral_persistence_months: int = 2
    material_delta: float = 10.0
    material_persistence: int = 2
    bands: List[float] = [40.0, 70.0]


class CompanyDetailResponse(BaseModel):
    company_id: str
    group_id: str
    currency: str
    country: Optional[str] = None
    erp: Optional[str] = None
    has_erp: bool
    created_at: Optional[str] = None
    as_of: str
    score: float
    base_health: float
    state: str
    momentum: float
    delta_3m: float
    health_band: Optional[str] = None
    data_confidence_index: float
    state_eligible: bool
    waterfall: CompanyWaterfall
    total_balance: Optional[float] = Field(None, description="Saldo bancario total consolidado")
    overdue_invoices_count: int = Field(0, description="Número de facturas vencidas impagadas")
    overdue_invoices_amount: float = Field(0.0, description="Volumen total en mora de facturas vencidas")
    total_pending_amount: float = Field(0.0, description="Volumen pendiente total de facturación")
    latest_alert: Optional[Dict[str, Any]] = Field(None, description="Última alerta de riesgo registrada")
    suggested_action: Optional[str] = Field(None, description="Recomendación o producto financiero sugerido")
    dso: float = Field(0.0, description="Días de cobro pendientes (DSO)")
    dpo: float = Field(0.0, description="Días de pago a proveedores (DPO)")
    dias_caja: float = Field(0.0, description="Días de caja / Runway de liquidez")
    annual_revenue: float = Field(0.0, description="Facturación anual estimada / observada")
    line_utilization: float = Field(0.0, description="Utilización de línea de crédito (%)")
    customer_hhi: Optional[float] = Field(None, description="Concentración de clientes (HHI)")
    daily_burn: float = Field(0.0, description="Gasto operativo diario medio (€/día)")
    episodios: List[Episode] = Field([], description="Episodios de cambio detectados (ambas direcciones)")
    episodio_destacado: Optional[int] = Field(None, description="Índice del episodio destacado (activo o último cerrado)")
    perspectivas_sin_aviso: List[Dict[str, Any]] = Field([], description="Perspectivas caducadas sin episodio asociado")
    trayectoria_marcas: Optional[TrayectoriaMarcas] = Field(None, description="Marcas del episodio destacado para la trayectoria")
    parametros_episodios: Optional[EpisodiosParametros] = Field(None, description="Umbrales declarados del motor de episodios")
    last_closed_month: str = Field(
        default=LAST_CLOSED_MONTH.isoformat(),
        description="Último mes con ciclo completo. El as_of es el corte; este campo es el mes de actividad.",
    )


# -------------------------------------------------------------
# 2. Esquema de Serie Histórica Temporal
# -------------------------------------------------------------

class RepartoDriver(BaseModel):
    field: str
    etiqueta: str
    points: float
    kind: str
    family: str
    reason: str
    razon: str


class Reparto(BaseModel):
    delta: float = 0.0
    pct_tendencia: int = 0
    pct_bache: int = 0
    struct_pts: float = 0.0
    circ_pts: float = 0.0
    drivers: List[RepartoDriver] = []


class HistoryPoint(BaseModel):
    as_of: str = Field(..., json_schema_extra={"example": "2026-09-01"})
    closed_month: str = Field(
        ...,
        json_schema_extra={"example": "2026-08-01"},
        description="Mes de transacciones que cierra este corte (as_of menos un mes).",
    )
    score: float = Field(..., json_schema_extra={"example": 65.2})
    base_health: float = Field(..., json_schema_extra={"example": 63.8})
    state: str = Field(..., json_schema_extra={"example": "ESTABLE"})
    momentum: float = Field(..., json_schema_extra={"example": 0.05})
    liquidity_points: float = Field(...)
    collections_points: float = Field(...)
    debt_points: float = Field(...)
    momentum_points: float = Field(...)
    growth_points: float = Field(...)
    fragility_points: float = Field(...)
    data_confidence_index: float = Field(...)
    reparto: Optional[Reparto] = None


class CompanyHistoryResponse(BaseModel):
    company_id: str
    months: int
    last_closed_month: str = Field(
        default=LAST_CLOSED_MONTH.isoformat(),
        description="Último mes con ciclo completo de transacciones.",
    )
    history: List[HistoryPoint]


# -------------------------------------------------------------
# 2b. Esquema de Grupo de Pares (Peer Benchmark)
# -------------------------------------------------------------

class PeerPoint(BaseModel):
    mes: str = Field(..., json_schema_extra={"example": "2024-10"}, description="YYYY-MM del as_of (reloj de corte).")
    closed_month: str = Field(..., json_schema_extra={"example": "2024-09-01"})
    mediana: float = Field(..., json_schema_extra={"example": 57.3})


class CompanyPeersResponse(BaseModel):
    company_id: str
    quartile: int = Field(..., description="Cuartil de tamaño por volumen de transacciones/facturación (1 a 4)")
    label: str = Field(..., description="Etiqueta descriptiva del cuartil de pares")
    n_companies: int = Field(..., description="Número de empresas en el cuartil")
    last_closed_month: str = Field(default=LAST_CLOSED_MONTH.isoformat())
    history: List[PeerPoint] = Field(..., description="Serie histórica de 24 meses con la mediana del score del cuartil")


# -------------------------------------------------------------
# 3. Esquemas de Facturas e Impagos
# -------------------------------------------------------------

class InvoiceItem(BaseModel):
    invoice_id: str = Field(..., json_schema_extra={"example": "INV_019283"})
    company_id: str = Field(..., json_schema_extra={"example": "COMP_0010"})
    document_type: Optional[str] = Field(None, json_schema_extra={"example": "invoice"})
    issue_date: Optional[str] = Field(None, json_schema_extra={"example": "2026-07-15"})
    due_date: Optional[str] = Field(None, json_schema_extra={"example": "2026-08-15"})
    paid_date: Optional[str] = Field(None, json_schema_extra={"example": None})
    total_amount: float = Field(..., json_schema_extra={"example": 12500.0})
    pending_amount: float = Field(..., json_schema_extra={"example": 12500.0})
    currency: Optional[str] = Field(None, json_schema_extra={"example": "EUR"})
    status: str = Field(..., json_schema_extra={"example": "overdue"})
    concept: Optional[str] = Field(None, json_schema_extra={"example": "Suministro de componentes"})
    counterparty_id: Optional[str] = Field(None, json_schema_extra={"example": "COUNTERPARTY_1044"})


class CompanyInvoicesResponse(BaseModel):
    company_id: str
    total: int
    overdue_count: int
    total_pending_amount: float
    limit: int
    offset: int
    invoices: List[InvoiceItem]


# -------------------------------------------------------------
# 4. Esquemas del Simulador What-If
# -------------------------------------------------------------

class WhatIfRequest(BaseModel):
    company_id: str = Field(..., json_schema_extra={"example": "COMP_0010"}, description="Identificador de la empresa")
    injection_amount: Optional[float] = Field(
        None,
        json_schema_extra={"example": 25000.0},
        description="Monto de inyección en €. Si es nulo o 0, calcula el tramo óptimo mínimo."
    )


class WhatIfResponse(BaseModel):
    company_id: str
    group_id: str
    as_of: str
    current_score: float
    current_state: str
    injection_amount: float
    is_optimal_computed: bool
    delta_score: float
    projected_score: float
    projected_state: str
    liquidity_gain: float
    fragility_gain: float
    fragility_reduction: float
    collections_gain: float
    recommended_product: str
    product_rationale: str
    executive_message: str


# -------------------------------------------------------------
# 5. Esquemas de Alertas
# -------------------------------------------------------------

class AlertItem(BaseModel):
    alert_id: str
    company_id: str
    group_id: str
    as_of: str
    state: str
    severity: str
    direction: str
    score: float
    delta_score: float
    momentum: float
    drivers: List[Dict[str, Any]]
    created_at: Optional[str] = None


class AlertListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    alerts: List[AlertItem]


# -------------------------------------------------------------
# 6. Esquemas de Estadísticas Globales y Grupos
# -------------------------------------------------------------

class DataCalendar(BaseModel):
    """Tres relojes del dataset: corte oficial, último mes cerrado y foto parcial."""
    as_of: str = Field(default=DATA_CUTOFF.isoformat(), description="Corte oficial: snapshot ERP/saldos y último score.")
    last_closed_month: str = Field(
        default=LAST_CLOSED_MONTH.isoformat(),
        description="Último mes con ciclo completo de transacciones. Usar en medias y ejes mensuales.",
    )
    partial_month: str = Field(
        default=PARTIAL_MONTH.isoformat(),
        description="Mes calendario incompleto. Si se muestra, rotularlo; no entra en medias.",
    )
    partial_month_label: str = Field(default=PARTIAL_MONTH_LABEL)
    partial_month_days: int = Field(default=PARTIAL_MONTH_DAYS)


class StatsResponse(BaseModel):
    total_companies: int
    latest_as_of: str
    calendar: DataCalendar = Field(default_factory=DataCalendar)
    distribution_by_state: Dict[str, int]
    risk_companies_count: int
    risk_percentage: float
    average_score: float
    median_score: float
    total_overdue_volume: float
    total_invoices_count: int
    total_transactions_count: int
    total_alerts_count: int


class PortfolioCompanyItem(BaseModel):
    """Fila resumida de la cartera Embat: lo justo para rankings y segmentos."""
    company_id: str
    group_id: str
    erp: Optional[str] = None
    score: float
    state: str
    momentum: float
    delta_3m: float
    health_band: Optional[str] = None
    state_eligible: bool
    segment: Optional[str] = Field(None, description="APOSTAR · VIGILAR · ACOMPANAR · None")


class PortfolioSegment(BaseModel):
    key: str
    label: str
    action: str
    count: int
    items: List[PortfolioCompanyItem]


class PortfolioHistogramBucket(BaseModel):
    bucket: int = Field(..., description="Límite inferior del tramo de 10 puntos")
    count: int


class PortfolioTrajectoryPoint(BaseModel):
    as_of: str
    closed_month: str
    average_score: float
    median_score: float
    eligible_companies: int


class PortfolioResponse(BaseModel):
    as_of: str
    calendar: DataCalendar = Field(default_factory=DataCalendar)
    total_companies: int
    eligible_companies: int
    average_score: float
    median_score: float
    risk_companies_count: int
    improving_companies_count: int
    alerts_last_month: int
    distribution_by_state: Dict[str, int]
    distribution_by_band: Dict[str, int]
    histogram: List[PortfolioHistogramBucket]
    trajectory: List[PortfolioTrajectoryPoint]
    top_score: List[PortfolioCompanyItem]
    top_growth: List[PortfolioCompanyItem]
    top_decline: List[PortfolioCompanyItem]
    segments: List[PortfolioSegment]


# -------------------------------------------------------------
# Mapa de flujos intragrupo (inferidos por emparejamiento)
# -------------------------------------------------------------

class GraphNode(BaseModel):
    company_id: str
    score: float
    state: str
    health_band: Optional[str] = None
    state_eligible: bool
    delta_3m: float
    segment: Optional[str] = None
    eur_out: float = Field(0.0, description="Euros que salen hacia otras sociedades del grupo")
    eur_in: float = Field(0.0, description="Euros que llegan desde otras sociedades del grupo")


class GraphEdge(BaseModel):
    source: str
    target: str
    matches: int = Field(..., description="Movimientos emparejados (mismo día, mismo importe)")
    eur: float
    last_date: str


class GraphResponse(BaseModel):
    group_id: str
    min_matches: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class GraphGroupSummary(BaseModel):
    group_id: str
    companies: int
    edges: int
    matches: int
    eur: float
    average_score: float
    worst_score: float


class GraphSummaryResponse(BaseModel):
    min_matches: int
    groups_with_flows: int
    total_edges: int
    total_eur: float
    groups: List[GraphGroupSummary]


class GroupItem(BaseModel):
    group_id: str
    erp: Optional[str] = None
    company_count: int
    average_score: float
    risk_companies_count: int


class GroupListResponse(BaseModel):
    total: int
    groups: List[GroupItem]


class GroupCompanyItem(BaseModel):
    company_id: str
    score: float
    base_health: float
    state: str
    momentum: float
    delta_3m: float
    erp: Optional[str] = None
    has_erp: bool = False
    state_eligible: bool = True


class GroupDetailResponse(BaseModel):
    group_id: str
    erp: Optional[str] = None
    company_count: int
    average_score: float
    consolidated_score: float
    contagion_penalty: float
    worst_company_id: str
    worst_company_score: float
    best_company_id: str
    best_company_score: float
    risk_companies_count: int
    data_coverage_percentage: float
    companies: List[GroupCompanyItem]


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str
    tables_count: int
    timestamp: str


# -------------------------------------------------------------
# 7. Simulador de palancas (rescoring honesto · capa intermedia)
# -------------------------------------------------------------

class SimulateLeverLine(BaseModel):
    facturas: Optional[List[str]] = Field(None, description="Ids de factura (operation_id)")
    clientes: Optional[List[str]] = Field(None, description="Contrapartes AR")
    proveedores: Optional[List[str]] = Field(None, description="Contrapartes AP")
    dias: Optional[int] = None
    days: Optional[int] = None
    tasa_descuento: Optional[float] = Field(None, description="Haircut 0..1; 0 = sin descuento")
    tasa: Optional[float] = None
    haircut: Optional[float] = None
    proposed_cost_pct: Optional[float] = None

    @model_validator(mode='after')
    def facturas_xor_clientes(self):
        n = sum(bool(value) for value in (self.facturas, self.clientes, self.proveedores))
        if n > 1:
            raise ValueError('una línea admite facturas o clientes, no ambos')
        return self


class SimulateLeverItem(BaseModel):
    id: str = Field(..., description="Id de palanca del catálogo", json_schema_extra={"example": "adelantar_cobros"})
    amount_eur: Optional[float] = Field(None, description="Euros a adelantar / liberar")
    pct: Optional[float] = Field(None, description="Fracción 0..1 para opex/refi/dpo/refunds")
    haircut: Optional[float] = Field(None, description="Descuento / haircut sobre cobros")
    descuento_pct: Optional[float] = None
    opex_pct: Optional[float] = None
    refi_pct: Optional[float] = None
    dpo_pct: Optional[float] = None
    couple_interest_pct: Optional[float] = Field(
        None, description="Si amortizar_linea: fracción de debt_service a bajar"
    )
    agreement_type: Optional[str] = Field(
        None, description="D2C/D3C: grupo_intragrupo | presion_comercial | contrato_ya_firmado | descuento | ..."
    )
    proposed_cost_pct: Optional[float] = None
    euros: Optional[float] = None
    days: Optional[int] = Field(None, description="Días de adelanto 7/15/30")
    dias: Optional[int] = None
    clientes: Optional[List[str]] = None
    facturas: Optional[List[str]] = None
    proveedores: Optional[List[str]] = None
    tasa_descuento: Optional[float] = None
    lineas: Optional[List[SimulateLeverLine]] = None

    @model_validator(mode='after')
    def top_level_targets_xor(self):
        if self.lineas:
            return self
        n = sum(bool(value) for value in (self.facturas, self.clientes, self.proveedores))
        if n > 1:
            raise ValueError('una línea admite facturas o clientes, no ambos')
        return self


class SimulateRequest(BaseModel):
    company_id: str = Field(..., json_schema_extra={"example": "COMP_0010"})
    levers: List[SimulateLeverItem] = Field(..., min_length=1)


class SimulateScoreSnapshot(BaseModel):
    score: float
    state: Optional[Any] = None
    liquidity_points: Optional[float] = None
    collections_points: Optional[float] = None
    debt_points: Optional[float] = None
    momentum_points: Optional[float] = None
    is_prior: Optional[bool] = None


class SimulateResponse(BaseModel):
    company_id: str
    as_of: str
    month_mutated: int
    model_version: str
    baseline: SimulateScoreSnapshot
    projected: SimulateScoreSnapshot
    delta_score: Optional[float] = None
    caja_liberada_eur: float
    effects: List[Dict[str, Any]]
    levers: List[Dict[str, Any]]
    modo: Optional[str] = "contrafactual_de_corte"
    warnings: Optional[List[str]] = None
    eur_año: Optional[float] = None
    delta_bps: Optional[float] = None
    efecto_score_informativo: Optional[float] = None
    assumptions: Optional[Dict[str, Any]] = None


class PalancaItem(BaseModel):
    id: str
    familia: str
    mutator: str
    excluido_con: List[str] = []
    es_aplicable: bool
    motivo_rechazo: Optional[str] = None
    needs_agreement: bool = False
    agreement_types: List[str] = []


class PalancasResponse(BaseModel):
    company_id: str
    as_of: str = "2026-09-01"
    palancas: List[PalancaItem]


class RankingRow(BaseModel):
    id: str
    familia: str
    delta_score: Optional[float] = None
    caja_liberada_eur: float = 0.0
    eur_año: Optional[float] = None
    days: Optional[int] = None
    pct: Optional[float] = None
    haircut: Optional[float] = None
    agreement_type: Optional[str] = None
    warnings: Optional[List[str]] = None
    label: Optional[str] = None


class RankingsResponse(BaseModel):
    ok: bool = True
    company_id: str
    as_of: str
    modo: Optional[str] = None
    model_version: Optional[str] = None
    n_sims: int = 0
    sugerencias: List[Dict[str, Any]] = []
    opciones_circulante: List[Dict[str, Any]] = []
    recomendado: Optional[Dict[str, Any]] = None


class PrevisionEstructuralResponse(BaseModel):
    company_id: str = Field(..., json_schema_extra={"example": "COMP_0010"})
    model: str = Field("structural_v2", json_schema_extra={"example": "structural_v2"})
    status: str = Field(..., json_schema_extra={"example": "available"})
    as_of: Optional[str] = Field(None, json_schema_extra={"example": "2026-08-01"})
    meses: int = Field(..., json_schema_extra={"example": 12})
    current_score: Optional[float] = Field(None, json_schema_extra={"example": 61.4})
    alto: List[float] = Field(..., description="Score del escenario optimista, t+1 … t+meses")
    medio: List[float] = Field(..., description="Score del escenario central, t+1 … t+meses")
    bajo: List[float] = Field(..., description="Score del escenario pesimista, t+1 … t+meses")
