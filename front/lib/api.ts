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
    if (!r.ok) return null;
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
  suggested_action: string | null;
};

export type ApiHistoria = {
  company_id: string; months: number;
  history: Array<{
    as_of: string; score: number; base_health: number; state: string;
    momentum: number; data_confidence_index: number;
  } & Omit<ApiWaterfall, "clipping_points">>;
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
export const apiPalancas  = (id: string) => get<{ company_id: string; as_of: string; palancas: ApiPalanca[] }>(`/api/palancas?company_id=${id}`);
export const apiRankings  = (id: string) => get<ApiRankings>(`/api/simulate/rankings?company_id=${id}`);
export const apiAlertas   = (id?: string, limite = 20) =>
  get<{ total: number; alerts: ApiAlert[] }>(`/api/alerts?limit=${limite}${id ? `&company_id=${id}` : ""}`);
export const apiGrupos    = (limite = 250) => get<{ total: number; groups: Array<{ group_id: string; erp: string | null; company_count: number; average_score: number; risk_companies_count: number }> }>(`/api/groups?limit=${limite}`);
export const apiGrupo     = (gid: string) => get<ApiGrupoDetalle>(`/api/groups/${gid}`);
export const apiEmpresasDeGrupo = (gid: string) =>
  get<{ total: number; items: ApiEmpresa[] }>(`/api/companies?group_id=${gid}&limit=100`);
export const apiSimular   = (id: string, levers: Array<Record<string, unknown>>) =>
  post<Record<string, unknown>>("/api/simulate", { company_id: id, levers });
export const apiWhatIf    = (id: string, inyeccion?: number) =>
  post<Record<string, unknown>>("/api/whatif", { company_id: id, ...(inyeccion ? { injection_amount: inyeccion } : {}) });

/** Etiquetas legibles de los seis bloques del waterfall. */
export const BLOQUES: Array<{ campo: keyof ApiWaterfall; etiqueta: string; codigo: string }> = [
  { campo: "liquidity_points",   etiqueta: "Liquidez",    codigo: "LIQ-02" },
  { campo: "collections_points", etiqueta: "Cobros",      codigo: "COB-01" },
  { campo: "debt_points",        etiqueta: "Deuda",       codigo: "DEU-03" },
  { campo: "momentum_points",    etiqueta: "Momentum",    codigo: "MOM-01" },
  { campo: "growth_points",      etiqueta: "Crecimiento", codigo: "CRE-02" },
  { campo: "fragility_points",   etiqueta: "Fragilidad",  codigo: "FRA-01" },
];
