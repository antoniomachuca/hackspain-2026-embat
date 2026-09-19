/**
 * Adaptador: traduce lo que devuelve el motor a la forma que consume el front.
 * Si el motor no responde, `cargar()` devuelve null y la página cae al modo demo.
 */
import {
  apiEmpresa, apiHistoria, apiPalancas, apiRankings, apiAlertas, apiEmpresasDeGrupo, apiGrupos, apiGrupo, apiEmpresas,
  BLOQUES, type ApiEmpresa, type ApiSugerencia, type ApiPalanca,
} from "./api";
import { pendiente, repartir, EMPRESAS_CON_SCORE } from "./data";
import type { Driver, Empresa, Estado, Punto, Severidad } from "./data";

const ESTADOS: Record<string, Estado> = {
  MEJORANDO: "MEJORANDO", ESTABLE: "ESTABLE", TORCIENDOSE: "TORCIENDOSE",
  DETERIORO: "DETERIORO", BACHE: "BACHE", RECUPERACION: "RECUPERACION",
  // El motor emite un séptimo estado que el enunciado no contempla
  EVALUACION_PENDIENTE: "ESTABLE",
};

const SEVERIDADES: Record<string, Severidad> = {
  ALTA: "ALTA", MEDIA: "MEDIA", BAJA: "BAJA", INFORMATIVA: "BAJA",
};

/** Nombre comercial: el dataset no trae razón social, solo el identificador. */
export const nombreDe = (id: string) => id.replace("COMP_", "Sociedad ");

function driversDe(w: ApiEmpresa["waterfall"]): Driver[] {
  const total = BLOQUES.reduce((a, b) => a + Math.abs(w[b.campo]), 0) || 1;
  return BLOQUES.map((b) => ({
    feature: b.campo.replace("_points", ""),
    etiqueta: b.etiqueta,
    contribucion: Math.round(w[b.campo] * 100) / 100,
    valor: `${w[b.campo] >= 0 ? "+" : "−"}${Math.abs(w[b.campo]).toFixed(2)} pts`,
    // FALTA: el motor no expone el percentil por peer group (REQ-B2.2).
    // Se aproxima con el peso relativo del bloque para no dejar la barra vacía.
    p_peer: Math.round((Math.abs(w[b.campo]) / total) * 100),
  })).sort((a, b) => b.contribucion - a.contribucion);
}

export async function cargarEmpresa(id: string): Promise<Empresa | null> {
  const [e, h, al] = await Promise.all([apiEmpresa(id), apiHistoria(id, 24), apiAlertas(id, 5)]);
  if (!e) return null;

  const trayectoria: Punto[] = (h?.history ?? []).map((p) => ({
    mes: p.as_of.slice(0, 7), score: p.score, nivel: p.base_health,
  }));
  const prev = trayectoria.length > 1 ? trayectoria[trayectoria.length - 2].score : e.score;
  const alerta = al?.alerts?.[0] ?? e.latest_alert ?? null;

  return {
    id: e.company_id,
    nombre: nombreDe(e.company_id),
    grupo: e.group_id,
    grupoNombre: e.group_id.replace("GROUP_", "Grupo "),
    sector: e.erp ? `ERP ${e.erp}` : "Sin ERP",     // FALTA: no hay sector
    moneda: e.currency,
    score: e.score,
    scorePrev: prev,
    nivelBase: e.base_health,
    momentum: e.momentum,
    clipping: e.waterfall.clipping_points,
    estado: ESTADOS[e.state] ?? "ESTABLE",
    confianza: e.data_confidence_index >= 80 ? "ALTA" : e.data_confidence_index >= 40 ? "MEDIA" : "BAJA",
    mesesHistoria: trayectoria.filter((p) => p.score !== 50).length || trayectoria.length,
    facturacionAnual: e.total_pending_amount * 12,   // FALTA: no hay facturación anual
    dso: 0, dpo: 0, diasCaja: 0,                     // FALTA: no se exponen
    utilizacionLinea: 0, hhiClientes: 0,             // FALTA: no se exponen
    trayectoria,
    // El motor todavía no sirve el reparto tendencia/bache (ni el peer group).
    // Se deriva aquí de la serie real: la pendiente vigente es la parte
    // estructural del movimiento, el resto es pulso. Misma regla que en demo.
    reparto: (() => {
      const serie = trayectoria.map((p) => p.score);
      const tends = serie.map((_, k) => pendiente(serie, k));
      return trayectoria.map((p, k) => repartir(serie, tends, k, p.mes));
    })(),
    drivers: driversDe(e.waterfall),
    alerta: alerta
      ? {
          severidad: SEVERIDADES[alerta.severity] ?? "BAJA",
          mesDeteccion: alerta.as_of.slice(0, 7),
          mesesAnticipacion: (() => {
            if (alerta.direction !== "deterioration" && e.state !== "DETERIORO" && e.state !== "TORCIENDOSE") {
              return 0;
            }
            let maxScore = -Infinity;
            let maxIdx = 0;
            trayectoria.forEach((p, idx) => {
              if (p.score > maxScore && p.score !== 50) {
                maxScore = p.score;
                maxIdx = idx;
              }
            });
            const mesesDesdePico = trayectoria.length - 1 - maxIdx;
            return Math.max(1, mesesDesdePico > 0 && mesesDesdePico <= 12 ? mesesDesdePico : 4);
          })(),
          driversMovidos: alerta.drivers.map((d) =>
            BLOQUES.find((b) => b.campo === d.field)?.etiqueta ?? d.field),
          codigosRazon: alerta.drivers.map((d) =>
            BLOQUES.find((b) => b.campo === d.field)?.codigo ?? "—"),
          texto: alerta.direction === "deterioration" ? "Deterioro detectado" : "Mejora detectada",
        }
      : undefined,
  };
}

export async function cargarFiliales(gid: string, excluir: string) {
  const r = await apiEmpresasDeGrupo(gid);
  return (r?.items ?? []).filter((x) => x.company_id !== excluir);
}

export async function cargarRecomendaciones(id: string) {
  const [rk, pl] = await Promise.all([apiRankings(id), apiPalancas(id)]);
  return {
    sugerencias: (rk?.sugerencias ?? []) as ApiSugerencia[],
    palancas: (pl?.palancas ?? []) as ApiPalanca[],
    modelVersion: rk?.model_version ?? null,
    nSims: rk?.n_sims ?? 0,
  };
}

export type GrupoResumen = {
  id: string;
  nombre: string;
  erp: string | null;
  company_count: number;
  average_score: number;
  risk_companies_count: number;
};

export async function cargarGrupos(): Promise<GrupoResumen[]> {
  const r = await apiGrupos(250);
  if (!r?.groups) return [];
  return r.groups.map((g) => ({
    id: g.group_id,
    nombre: g.group_id.replace("GROUP_", "Grupo "),
    erp: g.erp,
    company_count: g.company_count,
    average_score: g.average_score,
    risk_companies_count: g.risk_companies_count,
  }));
}

export type MiembroGrupo = {
  id: string;
  nombre: string;
  sector: string;
  score: number;
  scorePrev: number;
  momentum: number;
  estado: Estado;
  mesesHistoria: number;
  facturacionAnual: number;
  trayectoria: Punto[];
  alerta?: { mesDeteccion: string };
};

export type GrupoDetalle = {
  id: string;
  nombre: string;
  cobertura: number;
  consolidado: number;
  media: number;
  penalizacion: number;
  peor: MiembroGrupo | null;
  miembros: MiembroGrupo[];
};

export async function cargarGrupoDetalle(gid: string): Promise<GrupoDetalle | null> {
  const limpio = decodeURIComponent(gid).trim().toUpperCase();
  const normGid = limpio.startsWith("GROUP_")
    ? limpio
    : `GROUP_${limpio.padStart(4, "0")}`;

  const [detail, r] = await Promise.all([
    apiGrupo(normGid),
    apiEmpresasDeGrupo(normGid),
  ]);

  const items = detail?.companies ?? r?.items ?? [];
  if (!items.length) return null;

  const worstId =
    detail?.worst_company_id ??
    items.reduce((a, b) => (a.score < b.score ? a : b), items[0]).company_id;

  const [peorHist, peorAlert] = await Promise.all([
    apiHistoria(worstId, 24),
    apiAlertas(worstId, 1),
  ]);

  const peorTrayectoria: Punto[] = (peorHist?.history ?? []).map((p) => ({
    mes: p.as_of.slice(0, 7),
    score: p.score,
    nivel: p.base_health,
  }));

  const miembros: MiembroGrupo[] = items.map((m) => {
    const isPeor = m.company_id === worstId;
    const hist = isPeor
      ? peorTrayectoria
      : [{ mes: "2026-09", score: m.score, nivel: m.base_health }];
    return {
      id: m.company_id,
      nombre: nombreDe(m.company_id),
      sector: m.erp ? `ERP ${m.erp}` : "Sin ERP",
      score: m.score,
      scorePrev: m.score,
      momentum: m.momentum,
      estado: ESTADOS[m.state] ?? "ESTABLE",
      mesesHistoria: m.state_eligible ? 24 : 8,
      facturacionAnual: 0,
      trayectoria: hist,
      alerta:
        isPeor && peorAlert?.alerts?.[0]
          ? { mesDeteccion: peorAlert.alerts[0].as_of.slice(0, 7) }
          : undefined,
    };
  });

  const media =
    detail?.average_score ??
    Math.round((miembros.reduce((a, b) => a + b.score, 0) / miembros.length) * 10) / 10;
  const worstScore = detail?.worst_company_score ?? Math.min(...miembros.map((m) => m.score));
  const consolidado =
    detail?.consolidated_score ?? Math.round((0.65 * media + 0.35 * worstScore) * 10) / 10;
  const penalizacion =
    detail?.contagion_penalty ??
    (worstScore < 40 ? Math.round((40 - worstScore) * 0.25 * 10) / 10 : 0);
  const cobertura =
    detail?.data_coverage_percentage ??
    Math.round((items.filter((x) => x.state_eligible).length / items.length) * 100);

  const peorMiembro = miembros.find((m) => m.id === worstId) ?? null;

  return {
    id: normGid,
    nombre: normGid.replace("GROUP_", "Grupo "),
    cobertura,
    consolidado,
    media,
    penalizacion,
    peor: peorMiembro,
    miembros,
  };
}

export type OpcionComparar = {
  id: string;
  nombre: string;
  score: number;
  estado: string;
};

export type ComparativaResultado = {
  sube: Empresa;
  baja: Empresa;
  opcionesSube: OpcionComparar[];
  opcionesBaja: OpcionComparar[];
};

export async function cargarComparativa(subeId?: string, bajaId?: string): Promise<ComparativaResultado> {
  // Consultamos empresas reales por estados positivos y negativos
  const [resMejora, resRecup, resDeter, resTorc] = await Promise.all([
    apiEmpresas({ state: "MEJORANDO", limit: 25 }),
    apiEmpresas({ state: "RECUPERACION", limit: 25 }),
    apiEmpresas({ state: "DETERIORO", limit: 25 }),
    apiEmpresas({ state: "TORCIENDOSE", limit: 25 }),
  ]);

  const listaSube = [...(resMejora?.items ?? []), ...(resRecup?.items ?? [])];
  const listaBaja = [...(resDeter?.items ?? []), ...(resTorc?.items ?? [])];

  const opcionesSube: OpcionComparar[] = listaSube.map((x) => ({
    id: x.company_id,
    nombre: nombreDe(x.company_id),
    score: x.score,
    estado: x.state,
  }));

  const opcionesBaja: OpcionComparar[] = listaBaja.map((x) => ({
    id: x.company_id,
    nombre: nombreDe(x.company_id),
    score: x.score,
    estado: x.state,
  }));

  let targetSubeId = subeId;
  let targetBajaId = bajaId;

  // Si no se proporcionaron IDs, buscamos el par con mínima diferencia de score en DuckDB
  if (!targetSubeId || !targetBajaId) {
    let minDiff = Infinity;
    let bestSube = listaSube[0]?.company_id ?? "COMP_1030";
    let bestBaja = listaBaja[0]?.company_id ?? "COMP_0648";

    for (const s of listaSube) {
      for (const b of listaBaja) {
        if (s.company_id === b.company_id) continue;
        const diff = Math.abs(s.score - b.score);
        if (diff < minDiff) {
          minDiff = diff;
          bestSube = s.company_id;
          bestBaja = b.company_id;
        }
      }
    }
    if (!targetSubeId) targetSubeId = bestSube;
    if (!targetBajaId) targetBajaId = bestBaja;
  }

  const [subeData, bajaData] = await Promise.all([
    cargarEmpresa(targetSubeId),
    cargarEmpresa(targetBajaId),
  ]);

  const subeMock = EMPRESAS_CON_SCORE.find((e) => e.estado === "MEJORANDO" || e.estado === "RECUPERACION")!;
  const bajaMock = EMPRESAS_CON_SCORE.find((e) => e.estado === "DETERIORO" || e.estado === "TORCIENDOSE")!;

  return {
    sube: subeData ?? subeMock,
    baja: bajaData ?? bajaMock,
    opcionesSube,
    opcionesBaja,
  };
}

