/**
 * Adaptador: traduce lo que devuelve el motor a la forma que consume el front.
 * Si el motor no responde, `cargar()` devuelve null y la página cae al modo demo.
 */
import {
  apiEmpresa, apiHistoria, apiPeers, apiPalancas, apiRankings, apiWhatIf, apiAlertas, apiEmpresasDeGrupo, apiGrupos, apiGrupo, apiEmpresas, apiSimular,
  BLOQUES, type ApiEmpresa, type ApiSugerencia, type ApiPalanca, type ApiSimulateResponse, type ApiWhatIfResponse,
} from "./api";
import { eur, num } from "./format";
import { pendiente, repartir, inflexionDe, EMPRESAS_CON_SCORE, simular } from "./data";
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

export function driversDe(w: ApiEmpresa["waterfall"], e?: ApiEmpresa): Driver[] {
  return BLOQUES.map((b) => {
    const feat = b.campo.replace("_points", "");
    const pts = Math.round(w[b.campo] * 100) / 100;
    const sign = pts >= 0 ? "+" : "−";
    const absPts = Math.abs(pts);

    let rango = "0 a 50 pts";
    let desc = "";
    let diag = "";
    let valor = `${sign}${absPts.toFixed(1)} pts`;
    let p_peer = 50;

    if (b.campo === "liquidity_points") {
      rango = "0 a 50 pts";
      desc = "Colchón de tesorería y autonomía frente al gasto operativo diario (burn rate). Evalúa cuántos días de caja operativa mantiene la empresa sin deuda.";
      p_peer = Math.min(100, Math.max(0, Math.round((Math.max(0, pts) / 50) * 100)));
      const dias = e?.dias_caja ?? 0;
      if (dias > 0) {
        valor = `${num(dias, 1)} días de caja`;
        diag = dias >= 60
          ? "Excelente autonomía operativa (>60 días). Aporta máxima solidez al score."
          : dias >= 30
          ? "Autonomía operativa suficiente (30–60 días de caja sin tensiones)."
          : "Tensión de liquidez (<30 días de caja). Margen reducido ante imprevistos.";
      } else if (e?.total_balance != null && e.total_balance > 0) {
        valor = `${eur(e.total_balance, true)} de saldo`;
        diag = pts >= 25 ? "Saldo bancario suficiente para el ritmo de pagos actual." : "Colchón de caja ajustado frente a la operativa.";
      } else {
        diag = pts >= 25 ? "Cobertura de liquidez sólida." : "Tensión en colchón de tesorería.";
      }
    } else if (b.campo === "collections_points") {
      rango = "0 a 30 pts";
      desc = "Rotación de cobro de clientes (DSO) y disciplina en vencimientos. Penaliza facturas impagadas o en mora acumuladas.";
      p_peer = Math.min(100, Math.max(0, Math.round((Math.max(0, pts) / 30) * 100)));
      const dso = e?.dso ?? 0;
      const moraCount = e?.overdue_invoices_count ?? 0;
      const moraAmt = e?.overdue_invoices_amount ?? 0;
      if (dso > 0) {
        valor = `DSO ${num(dso, 0)}d${moraCount > 0 ? ` · ${moraCount} en mora` : " · 0 mora"}`;
        if (moraCount > 0) {
          diag = `${moraCount} facturas vencidas impagadas (${eur(moraAmt, true)}). Penaliza el flujo de caja.`;
        } else if (dso <= 45) {
          diag = "Cobro ágil dentro de plazo comercial estándar (DSO ≤ 45d) sin impagos.";
        } else {
          diag = `Plazo de cobro dilatado (${num(dso, 0)} días DSO). Retrasa la liquidez operativa.`;
        }
      } else {
        diag = pts >= 15 ? "Cobro fluido sin incidencias de morosidad." : "Retrasos en el circuito de cobros comerciales.";
      }
    } else if (b.campo === "debt_points") {
      rango = "0 a 20 pts";
      desc = "Capacidad de cobertura del servicio de deuda y margen de crédito disponible en pólizas o líneas de circulante.";
      p_peer = Math.min(100, Math.max(0, Math.round((Math.max(0, pts) / 20) * 100)));
      const util = e?.line_utilization ?? 0;
      if (util > 0) {
        valor = `${num(util, 0)}% línea dispuesta`;
        diag = util >= 75
          ? `Alto uso de líneas de crédito bancarias (${num(util, 0)}%). Margen de maniobra limitado.`
          : `Uso moderado de líneas de crédito (${num(util, 0)}%) y deuda estructurada.`;
      } else {
        valor = `${sign}${absPts.toFixed(1)} pts`;
        diag = pts >= 10 ? "Baja dependencia de crédito bancario a corto plazo." : "Capacidad de endeudamiento adicional reducida.";
      }
    } else if (b.campo === "momentum_points") {
      rango = "−15 a +15 pts";
      desc = "Inercia reciente y tendencia del flujo de tesorería a 3–6 meses. Bonifica aceleración positiva o penaliza deterioro continuado.";
      p_peer = Math.min(100, Math.max(0, Math.round(((pts + 15) / 30) * 100)));
      valor = `${sign}${absPts.toFixed(1)} pts inercia`;
      diag = pts >= 3
        ? "Tendencia de mejora continuada en el último trimestre que impulsa el score."
        : pts <= -3
        ? "Inercia negativa continuada en meses recientes. Alerta de deterioro."
        : "Evolución neutral sin grandes oscilaciones trimestrales.";
    } else if (b.campo === "growth_points") {
      rango = "−10 a +10 pts";
      desc = "Crecimiento comercial sostenible en facturación emitida sin provocar descalces en el fondo de maniobra.";
      p_peer = Math.min(100, Math.max(0, Math.round(((pts + 10) / 20) * 100)));
      const rev = e?.annual_revenue ?? 0;
      if (rev > 0) {
        valor = `${eur(rev, true)}/año`;
      } else {
        valor = `${sign}${absPts.toFixed(1)} pts`;
      }
      diag = pts >= 2
        ? "Expansión comercial favorable que aporta tracción al negocio."
        : pts <= -2
        ? "Contracción o enfriamiento en el volumen de actividad facturada."
        : "Facturación comercial consolidada a ritmo constante.";
    } else if (b.campo === "fragility_points") {
      rango = "−8 a 0 pts";
      desc = "Penalización por volatilidad intradía de saldos, concentración de clientes (HHI) y descalce temporal de pagos.";
      p_peer = Math.min(100, Math.max(0, Math.round(((pts + 8) / 8) * 100)));
      const hhi = e?.customer_hhi;
      if (hhi != null && hhi > 0) {
        valor = `HHI ${hhi.toFixed(2)}`;
      } else {
        valor = `${pts.toFixed(1)} pts estrés`;
      }
      diag = pts <= -3
        ? "Riesgo de concentración o volatilidad acusada en cuenta. Requiere diversificar."
        : pts < 0
        ? "Ligera penalización por picos puntuales de tesorería o concentración moderada."
        : "Estructura de cobros y saldos diversificada sin penalización por fragilidad.";
    }

    return {
      feature: feat,
      etiqueta: b.etiqueta,
      codigo: b.codigo,
      rango,
      descripcion: desc,
      diagnostico: diag,
      contribucion: pts,
      valor,
      p_peer,
    };
  }).sort((a, b) => b.contribucion - a.contribucion);
}

export async function cargarEmpresa(id: string): Promise<Empresa | null> {
  const [e, h, al, pr] = await Promise.all([
    apiEmpresa(id),
    apiHistoria(id, 24),
    apiAlertas(id, 5),
    apiPeers(id),
  ]);
  if (!e) return null;

  const trayectoria: Punto[] = (h?.history ?? []).map((p) => ({
    mes: p.as_of.slice(0, 7), score: p.score, nivel: p.base_health,
  }));
  const prev = trayectoria.length > 1 ? trayectoria[trayectoria.length - 2].score : e.score;
  const alerta = al?.alerts?.[0] ?? e.latest_alert ?? null;

  const serie = trayectoria.map((p) => p.score);
  const tends = serie.map((_, k) => pendiente(serie, k));
  const peerSerie = pr?.history?.map((p) => p.mediana) ?? [];
  const meses = trayectoria.map((p) => p.mes);
  const inflexion = (peerSerie.length === serie.length && serie.length > 0)
    ? inflexionDe(serie, tends, peerSerie, meses)
    : undefined;

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
    delta3m: e.delta_3m,
    elegible: e.state_eligible,
    clipping: e.waterfall.clipping_points,
    estado: ESTADOS[e.state] ?? "ESTABLE",
    confianza: e.data_confidence_index >= 80 ? "ALTA" : e.data_confidence_index >= 40 ? "MEDIA" : "BAJA",
    mesesHistoria: trayectoria.filter((p) => p.score !== 50).length || trayectoria.length,
    facturacionAnual: e.annual_revenue && e.annual_revenue > 0 ? e.annual_revenue : (e.total_pending_amount * 12),
    saldoBancario: e.total_balance ?? undefined,
    dso: e.dso ?? 0,
    dpo: e.dpo ?? 0,
    diasCaja: e.dias_caja ?? 0,
    utilizacionLinea: e.line_utilization ?? 0,
    hhiClientes: e.customer_hhi ?? 0,
    trayectoria,
    peer: pr ? { etiqueta: pr.label, n: pr.n_companies } : undefined,
    trayectoriaPeer: pr?.history ? pr.history.map((p) => ({ mes: p.mes, mediana: p.mediana })) : undefined,
    reparto: trayectoria.map((p, k) => repartir(serie, tends, k, p.mes)),
    inflexion,
    drivers: driversDe(e.waterfall, e),
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
  const [rk, pl, wf] = await Promise.all([
    apiRankings(id),
    apiPalancas(id),
    apiWhatIf(id),
  ]);
  return {
    sugerencias: (rk?.sugerencias ?? []) as ApiSugerencia[],
    opcionesCirculante: (rk?.opciones_circulante ?? []) as ApiSugerencia[],
    recomendado: (rk?.recomendado ?? null) as ApiSugerencia | null,
    palancas: (pl?.palancas ?? []) as ApiPalanca[],
    whatif: (wf ?? null) as ApiWhatIfResponse | null,
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

export type ResultadoSimulacion = {
  scoreNuevo: number;
  deltaScore: number;
  cajaLiberada: number;
  deltaBps: number;
  eurAnio: number;
  inaplicable: boolean;
  motivoRechazo?: string;
  advertencias?: string[];
  esReal: boolean;
};

export async function simularPalanca(
  cid: string,
  palancaId: string,
  valor: number,
  empresaBase: Empresa
): Promise<ResultadoSimulacion> {
  // Construir payload según la palanca para simulate_levers del backend
  let leverPayload: Record<string, unknown> = { id: palancaId };
  if (palancaId === "reducir_dso" || palancaId === "adelantar_cobros") {
    leverPayload = { id: "reducir_dso", days: valor, agreement_type: "presion_comercial" };
  } else if (palancaId === "pronto_pago" || palancaId === "descuento_pronto_pago") {
    leverPayload = { id: "descuento_pronto_pago", days: 15, haircut: valor / 100, agreement_type: "descuento_pronto_pago" };
  } else if (palancaId === "recortar_opex") {
    leverPayload = { id: "recortar_opex", pct: valor / 100 };
  } else if (palancaId === "refinanciar") {
    leverPayload = { id: "refinanciar", pct: valor / 100 };
  } else if (palancaId === "ampliar_dpo") {
    leverPayload = { id: "ampliar_dpo", pct: valor / 100, agreement_type: "acuerdo_negociado" };
  } else if (palancaId === "bajar_linea") {
    leverPayload = { id: "bajar_utilizacion_linea", pct: valor / 100 };
  } else if (palancaId === "reducir_concent") {
    leverPayload = { id: "reducir_concentracion", pct: valor / 100 };
  } else if (palancaId === "sustituir_fact") {
    leverPayload = { id: "sustituir_factoring", pct: valor / 100 };
  }

  const res = await apiSimular(cid, [leverPayload]);

  if (res?.detail && !res.projected) {
    const motivo = res.detail.motivo_rechazo ?? res.detail.error ?? "Inaplicable para el perfil actual";
    return {
      scoreNuevo: empresaBase.score,
      deltaScore: 0,
      cajaLiberada: 0,
      deltaBps: 0,
      eurAnio: 0,
      inaplicable: true,
      motivoRechazo: motivo,
      esReal: true,
    };
  }

  if (res && res.projected) {
    const rawDelta =
      res.delta_score ??
      res.efecto_score_informativo ??
      (res.projected.score - (res.baseline?.score ?? empresaBase.score));
    const deltaScore = Math.round(rawDelta * 10) / 10;
    const scoreNuevo = Math.round(res.projected.score * 10) / 10;
    const cajaLiberada = Math.round(res.caja_liberada_eur ?? 0);
    const eurAnio = Math.round(res.eur_año ?? (res.effects?.[0]?.eur_año ?? 0));
    const deltaBps = Math.round(res.delta_bps ?? (deltaScore * 7.5));

    return {
      scoreNuevo,
      deltaScore,
      cajaLiberada,
      deltaBps,
      eurAnio,
      inaplicable: false,
      advertencias: res.warnings,
      esReal: true,
    };
  }

  // Fallback con simular() local si el backend no responde
  const fallback = simular(empresaBase, palancaId, valor);
  return {
    ...fallback,
    inaplicable: false,
    esReal: false,
  };
}

