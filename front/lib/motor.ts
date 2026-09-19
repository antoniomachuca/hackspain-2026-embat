/**
 * Adaptador: traduce lo que devuelve el motor a la forma que consume el front.
 * Si el motor no responde, `cargar()` devuelve null y la página cae al modo demo.
 */
import {
  apiEmpresa, apiHistoria, apiPalancas, apiRankings, apiAlertas, apiEmpresasDeGrupo,
  BLOQUES, type ApiEmpresa, type ApiSugerencia, type ApiPalanca,
} from "./api";
import { pendiente, repartir } from "./data";
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
          // FALTA: el motor no calcula los meses de anticipación (REQ-B5.1)
          mesesAnticipacion: 0,
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
