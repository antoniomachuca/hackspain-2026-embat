/**
 * Cliente del motor X-Ray (FastAPI + DuckDB).
 *
 * Todo lo que el backend ya da se lee de aquí. Lo que aún no existe queda
 * marcado con FALTA y se rellena en el adaptador de lib/data.ts.
 * Base configurable con NEXT_PUBLIC_API_URL; por defecto, el puerto local.
 */
export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function get<T>(ruta: string): Promise<T | null> {
  try {
    const r = await fetch(`${API}${ruta}`, { cache: "no-store" });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;   // sin motor, el front cae al modo demo
  }
}

async function post<T>(ruta: string, cuerpo: unknown): Promise<T | null> {
  try {
    const r = await fetch(`${API}${ruta}`, {
      method: "POST", cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
    if (!r.ok) {
      try {
        const errJson = await r.json();
        return errJson as T;
      } catch {
        return null;
      }
    }
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

// ── Formas que devuelve el motor ─────────────────────────────────────
export type ApiWaterfall = {
  liquidity_points: number; collections_points: number; debt_points: number;
  momentum_points: number; growth_points: number; fragility_points: number;
  clipping_points: number;
};

export type ApiDriver = { field: string; delta_points: number; unit: string };

export type ApiAlert = {
  alert_id: string; company_id: string; group_id: string; as_of: string;
  state: string; severity: string; direction: string;
  score: number; delta_score: number; momentum: number; drivers: ApiDriver[];
};

export type ApiEpisodioSenal = {
  senal: string; antes: number; en_deteccion: number; delta_puntos: number;
};

export type ApiEpisodio = {
  direccion: "deterioro" | "mejora"; estado: "activo" | "cerrado";
  cierre: string | null; motivo_cierre: string | null;
  deteccion: string; estado_deteccion: string; score_deteccion: number;
  escaladas: { as_of: string; estado: string }[];
  inicio_estimado: string; referencia_base_health: number;
  referencia_as_of: string | null;
  cambio_material: string | null; criterio: string | null;
  estado_confirmacion: "confirmado" | "pendiente" | "no_confirmado";
  meses_anticipacion: number | null;
  perspectiva: {
    as_of: string; outlook: string; score_observado: number;
    score_proyectado: number; meses_antes_deteccion: number;
  } | null;
  senales: ApiEpisodioSenal[]; familia: string; texto: string;
};

export type ApiCamino = {
  as_of: string;
  outlook?: string;
  score_observado?: number;
  score_proyectado: number;
  familia?: string;
};

export type ApiTrayectoriaMarcas = {
  deteccion: { as_of: string; state: string; score: number; direccion: string } | null;
  camino: ApiCamino | null;
  texto: string;
};

export type ApiEmpresa = {
  company_id: string; group_id: string; currency: string;
  country: string | null; erp: string | null; has_erp: boolean;
  as_of: string; score: number; base_health: number; state: string;
  momentum: number; delta_3m: number; health_band: string | null;
  data_confidence_index: number; state_eligible: boolean;
  waterfall: ApiWaterfall;
  total_balance: number | null;
  overdue_invoices_count: number; overdue_invoices_amount: number;
  total_pending_amount: number;
  latest_alert: ApiAlert | null;
  episodios?: ApiEpisodio[];
  episodio_destacado?: number | null;
  trayectoria_marcas?: ApiTrayectoriaMarcas | null;
  suggested_action: string | null;
  dso?: number;
  dpo?: number;
  dias_caja?: number;
  annual_revenue?: number;
  line_utilization?: number;
  customer_hhi?: number | null;
  daily_burn?: number;
};

/**
 * El reparto del Δ del mes entre tendencia y bache, anidado en cada punto de
 * la historia. Mientras FastAPI no lo sirva llega `undefined` y el anillo no
 * se pinta; nunca se sustituye por el cálculo del cliente.
 */
export type ApiRepartoDriver = {
  field: string;
  etiqueta: string;
  points: number;
  kind: "estructural" | "coyuntural";
  family: "salud" | "circulante" | "dato" | "formula";
  reason: string;
  razon: string;
};

export type ApiReparto = {
  delta: number;
  pct_tendencia: number;
  pct_bache: number;
  struct_pts: number;
  circ_pts: number;
  drivers: ApiRepartoDriver[];
};

export type ApiHistoria = {
  company_id: string; months: number;
  history: Array<{
    as_of: string; score: number; base_health: number; state: string;
    momentum: number; data_confidence_index: number;
    reparto?: ApiReparto;
  } & Omit<ApiWaterfall, "clipping_points">>;
};

export type ApiPeerPoint = { mes: string; mediana: number };

export type ApiPeersResponse = {
  company_id: string;
  quartile: number;
  label: string;
  n_companies: number;
  history: ApiPeerPoint[];
};

export type ApiPalanca = {
  id: string; familia: string; mutator: string; excluido_con: string[];
  es_aplicable: boolean; motivo_rechazo: string | null;
  needs_agreement: boolean; agreement_types: string[];
};

export type ApiSugerencia = {
  id: string; familia: string; delta_score: number;
  caja_liberada_eur: number | null; eur_año: number | null;
  days: number | null; pct: number | null; haircut: number | null;
  agreement_type: string | null; warnings: string[]; label: string;
};

export type ApiRankings = {
  ok: boolean; company_id: string; as_of: string; modo: string;
  model_version: string; n_sims: number; sugerencias: ApiSugerencia[];
  opciones_circulante?: ApiSugerencia[];
  recomendado?: ApiSugerencia | null;
};

export type ApiWhatIfResponse = {
  company_id: string;
  group_id: string;
  as_of: string;
  current_score: number;
  current_state: string;
  injection_amount: number;
  is_optimal_computed: boolean;
  delta_score: number;
  projected_score: number;
  projected_state: string;
  liquidity_gain: number;
  fragility_gain: number;
  fragility_reduction: number;
  collections_gain: number;
  recommended_product: string;
  product_rationale: string;
  executive_message: string;
};

export type ApiStats = {
  total_companies: number; latest_as_of: string;
  distribution_by_state: Record<string, number>;
  risk_companies_count: number; risk_percentage: number;
  average_score: number; median_score: number;
  total_overdue_volume: number; total_invoices_count: number;
  total_transactions_count: number; total_alerts_count: number;
};

export type ApiGrupoCompany = {
  company_id: string;
  score: number;
  base_health: number;
  state: string;
  momentum: number;
  delta_3m: number;
  erp: string | null;
  has_erp: boolean;
  state_eligible: boolean;
};

export type ApiGrupoDetalle = {
  group_id: string;
  erp: string | null;
  company_count: number;
  average_score: number;
  consolidated_score: number;
  contagion_penalty: number;
  worst_company_id: string;
  worst_company_score: number;
  best_company_id: string;
  best_company_score: number;
  risk_companies_count: number;
  data_coverage_percentage: number;
  companies: ApiGrupoCompany[];
};

// ── Llamadas ─────────────────────────────────────────────────────────
export const apiSalud     = () => get<{ status: string; tables_count: number }>("/api/health");
export const apiStats     = () => get<ApiStats>("/api/stats");
export const apiEmpresa   = (id: string) => get<ApiEmpresa>(`/api/companies/${id}`);
export const apiHistoria  = (id: string, meses = 24) => get<ApiHistoria>(`/api/companies/${id}/history?months=${meses}`);
export const apiPeers     = (id: string) => get<ApiPeersResponse>(`/api/companies/${id}/peers`);
export const apiPalancas  = (id: string) => get<{ company_id: string; as_of: string; palancas: ApiPalanca[] }>(`/api/palancas?company_id=${id}`);
export const apiRankings  = (id: string) => get<ApiRankings>(`/api/simulate/rankings?company_id=${id}`);
export const apiAlertas   = (id?: string, limite = 20) =>
  get<{ total: number; alerts: ApiAlert[] }>(`/api/alerts?limit=${limite}${id ? `&company_id=${id}` : ""}`);
export const apiGrupos    = (limite = 250) => get<{ total: number; groups: Array<{ group_id: string; erp: string | null; company_count: number; average_score: number; risk_companies_count: number }> }>(`/api/groups?limit=${limite}`);
export const apiGrupo     = (gid: string) => get<ApiGrupoDetalle>(`/api/groups/${gid}`);
export const apiEmpresas = (params?: { state?: string; search?: string; limit?: number; offset?: number; order_by?: string; order_dir?: string }) => {
  const q = new URLSearchParams();
  if (params?.state) q.set("state", params.state);
  if (params?.search) q.set("search", params.search);
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.offset) q.set("offset", String(params.offset));
  if (params?.order_by) q.set("order_by", params.order_by);
  if (params?.order_dir) q.set("order_dir", params.order_dir);
  const qs = q.toString();
  return get<{ total: number; items: ApiEmpresa[] }>(`/api/companies${qs ? `?${qs}` : ""}`);
};
export const apiEmpresasDeGrupo = (gid: string) =>
  get<{ total: number; items: ApiEmpresa[] }>(`/api/companies?group_id=${gid}&limit=100`);
export type ApiSimulateScore = {
  score: number;
  state?: string | null;
  liquidity_points?: number | null;
  collections_points?: number | null;
  debt_points?: number | null;
  momentum_points?: number | null;
};

export type ApiSimulateResponse = {
  company_id?: string;
  as_of?: string;
  month_mutated?: number;
  model_version?: string;
  baseline?: ApiSimulateScore;
  projected?: ApiSimulateScore;
  delta_score?: number | null;
  caja_liberada_eur?: number;
  effects?: Array<{
    lever_id: string;
    family: string;
    mutator: string;
    euros: number;
    eur_año?: number | null;
    delta_score_allowed: boolean;
    warnings?: string[];
  }>;
  warnings?: string[];
  eur_año?: number | null;
  delta_bps?: number | null;
  efecto_score_informativo?: number | null;
  detail?: {
    ok?: boolean;
    error?: string;
    motivo_rechazo?: string;
    lever_id?: string;
  };
};

export const apiSimular = (id: string, levers: Array<Record<string, unknown>>) =>
  post<ApiSimulateResponse>("/api/simulate", { company_id: id, levers });
export const apiWhatIf    = (id: string, inyeccion?: number) =>
  post<ApiWhatIfResponse>("/api/whatif", { company_id: id, ...(inyeccion ? { injection_amount: inyeccion } : {}) });

/** Etiquetas legibles de los seis bloques del waterfall. */
export const BLOQUES: Array<{ campo: keyof ApiWaterfall; etiqueta: string; codigo: string }> = [
  { campo: "liquidity_points",   etiqueta: "Liquidez",    codigo: "LIQ-02" },
  { campo: "collections_points", etiqueta: "Cobros",      codigo: "COB-01" },
  { campo: "debt_points",        etiqueta: "Deuda",       codigo: "DEU-03" },
  { campo: "momentum_points",    etiqueta: "Momentum",    codigo: "MOM-01" },
  { campo: "growth_points",      etiqueta: "Crecimiento", codigo: "CRE-02" },
  { campo: "fragility_points",   etiqueta: "Fragilidad",  codigo: "FRA-01" },
];

// ── Cartera Embat ────────────────────────────────────────────────────
export type ApiPortfolioItem = {
  company_id: string; group_id: string; erp: string | null;
  score: number; state: string; momentum: number; delta_3m: number;
  health_band: string | null; state_eligible: boolean;
  segment: "APOSTAR" | "VIGILAR" | "ACOMPANAR" | null;
};

export type ApiPortfolioSegment = {
  key: "APOSTAR" | "VIGILAR" | "ACOMPANAR"; label: string; action: string;
  count: number; items: ApiPortfolioItem[];
};

export type ApiPortfolio = {
  as_of: string;
  total_companies: number; eligible_companies: number;
  average_score: number; median_score: number;
  risk_companies_count: number; improving_companies_count: number; alerts_last_month: number;
  distribution_by_state: Record<string, number>;
  distribution_by_band: Record<string, number>;
  histogram: Array<{ bucket: number; count: number }>;
  trajectory: Array<{ as_of: string; average_score: number; median_score: number; eligible_companies: number }>;
  top_score: ApiPortfolioItem[]; top_growth: ApiPortfolioItem[]; top_decline: ApiPortfolioItem[];
  segments: ApiPortfolioSegment[];
};

export const apiPortfolio = (top = 10, porSegmento = 8) =>
  get<ApiPortfolio>(`/api/portfolio?top=${top}&per_segment=${porSegmento}`);

// ── Flujos intragrupo (inferidos: mismo día, mismo importe, mismo grupo) ──
export type ApiGrafoNodo = {
  company_id: string; score: number; state: string; health_band: string | null;
  state_eligible: boolean; delta_3m: number; segment: string | null;
  eur_out: number; eur_in: number;
};
export type ApiGrafoArista = { source: string; target: string; matches: number; eur: number; last_date: string };
export type ApiGrafo = { group_id: string; min_matches: number; nodes: ApiGrafoNodo[]; edges: ApiGrafoArista[] };
export type ApiGrafoResumen = {
  min_matches: number; groups_with_flows: number; total_edges: number; total_eur: number;
  groups: Array<{ group_id: string; companies: number; edges: number; matches: number; eur: number; average_score: number; worst_score: number }>;
};

export const apiGrafoResumen = (limite = 30, minCoincidencias = 2) =>
  get<ApiGrafoResumen>(`/api/graph?limit=${limite}&min_matches=${minCoincidencias}`);
export const apiGrafo = (gid: string, minCoincidencias = 2) =>
  get<ApiGrafo>(`/api/graph/${gid}?min_matches=${minCoincidencias}`);

/**
* Las dos familias del catálogo no son una etiqueta: son dos clases de
* decisión distintas para quien firma.
*   · salud      → cambia el negocio. La mejora es real.
*   · circulante → mueve caja de sitio. Da oxígeno hoy y lo quita mañana.
*/

/**
 * Las dos familias del catálogo no son una etiqueta: son dos clases de
 * decisión distintas para quien firma.
 *   · salud      → cambia el negocio. La mejora es real.
 *   · circulante → mueve caja de sitio. Da oxígeno hoy y lo quita mañana.
 */
export type Familia = "salud" | "circulante";

export const FAMILIAS: Record<Familia, { label: string; nota: string; color: string; fondo: string }> = {
  salud: {
    label: "Salud",
    nota: "Cambia el negocio: la mejora del score es real",
    color: "#80efa2", fondo: "rgba(128,239,162,.16)",
  },
  circulante: {
    label: "Circulante",
    nota: "Mueve caja de sitio: alivia hoy y hay que devolverlo",
    color: "#dfb631", fondo: "rgba(223,182,49,.16)",
  },
};

/**
 * Previsión estructural a 12 meses. No es un modelo sobre el índice: el motor
 * proyecta la cuenta (cobros, gastos, deuda) por tres caminos y puntúa cada mes
 * futuro con el mismo `calculate_scores` de producción. Alto es el camino que
 * ayuda al score, no "más caja".
 */
export type ApiPrevisionEstructural = {
  company_id: string;
  model: string;
  status?: string;
  as_of: string;
  meses: number;
  current_score: number;
  alto: number[];
  medio: number[];
  bajo: number[];
};

export const apiPrevisionEstructural = (id: string, meses = 12) =>
  get<ApiPrevisionEstructural>(
    `/api/companies/${encodeURIComponent(id)}/prevision-estructural?meses=${meses}`,
  );
