/**
 * La única puerta entre el front y el motor.
 *
 * Ninguna pantalla importa `demo-data` ni hace `fetch` por su cuenta. Todas pasan por
 * aquí. El día que Antonio enchufe `/score` real, cambia una variable de entorno y el
 * front no se toca (CA-B7).
 *
 *   NEXT_PUBLIC_API_MODE = mock (por defecto) | live
 *   NEXT_PUBLIC_API_URL  = https://…            (solo en modo live)
 *
 * En modo `live` con fallo de red, se cae a `mock` y se marca `degradado`. Durante el
 * pitch eso es la diferencia entre una pantalla en blanco y una demo que sigue (RF-B10.7).
 */

import type {
  Alerta,
  Mes,
  PeticionSimulacion,
  RespuestaGrupo,
  RespuestaScore,
  ResultadoSimulacion,
  ServicioAPI,
} from './contract'
import { ALERTAS, CARTERA, ECONOMICS, GRUPOS_DEMO, SCORES } from './demo-data'

const MODO = process.env.NEXT_PUBLIC_API_MODE ?? 'mock'
const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

export const modoApi = () => MODO

// ─────────────────────────────────────────── Mock

/**
 * Efectos de cada palanca sobre el score, en puntos por unidad. Son NÚMEROS INVENTADOS
 * y provisionales: el catálogo real y el contrafactual son de Pedro (RF-B8.2), que
 * recomputa B1→B2→B3 de verdad en vez de multiplicar.
 *
 * El calibrado sale de la frase del pitch (PRODUCTO.md §4):
 * "cobra 12 días antes → +6 pts → −35 bps → 14.000 €/año".
 */
const EFECTO: Record<string, { porUnidad: number; parametro: string; max: number }> = {
  reducir_dso: { porUnidad: 0.5, parametro: 'dias', max: 20 },
  ampliar_dpo: { porUnidad: 0.25, parametro: 'dias', max: 20 },
  bajar_utilizacion_linea: { porUnidad: 0.18, parametro: 'puntos_pct', max: 40 },
  reducir_concentracion: { porUnidad: 0.22, parametro: 'puntos_pct', max: 30 },
  recortar_opex: { porUnidad: 0.6, parametro: 'pct', max: 10 },
  descuento_pronto_pago: { porUnidad: 0.35, parametro: 'pct', max: 5 },
  refinanciar: { porUnidad: 3.5, parametro: 'n', max: 1 },
  sustituir_factoring_por_linea: { porUnidad: 2.4, parametro: 'n', max: 1 },
}

/** Puntos de score → puntos básicos de coste de financiación. Pata 2 de B9: ESTIMACIÓN. */
const BPS_POR_PUNTO = -5.83

const mock: ServicioAPI = {
  async getScore(entity_id, month) {
    const s = SCORES[entity_id]
    if (!s) throw new ApiError('ENTIDAD_DESCONOCIDA', `No existe ${entity_id}`)
    if (!month || month === s.mes) return s
    const punto = s.trayectoria.find((p) => p.mes === month)
    if (!punto) throw new ApiError('MES_FUERA_DE_RANGO', `Sin datos de ${entity_id} en ${month}`)
    return { ...s, mes: month, score: punto.score, nivel: punto.nivel, tendencia: punto.tendencia, estado: punto.estado }
  },

  async getGroup(group_id) {
    const g = GRUPOS_DEMO[group_id]
    if (!g) throw new ApiError('GRUPO_DESCONOCIDO', `No existe ${group_id}`)
    return g
  },

  async postSimulate({ entity_id, palancas }: PeticionSimulacion) {
    const s = SCORES[entity_id]
    if (!s) throw new ApiError('ENTIDAD_DESCONOCIDA', `No existe ${entity_id}`)
    const eco = ECONOMICS[entity_id] ?? { facturacion_anual: 0, deuda_viva: 0 }

    let delta = 0
    let diasDso = 0
    for (const p of palancas) {
      const e = EFECTO[p.id]
      if (!e) return rechazo(s.score, `Palanca desconocida: ${p.id}`)
      const magnitud = Number(p.parametros[e.parametro] ?? 0)
      if (magnitud <= 0) continue
      if (magnitud > e.max) return rechazo(s.score, `${p.id} fuera de rango plausible (máx ${e.max})`)
      delta += e.porUnidad * magnitud
      if (p.id === 'reducir_dso') diasDso += magnitud
    }

    // Rendimientos decrecientes: las palancas componen, no se suman (RF-B8.4).
    const deltaCompuesto = redondear(delta * (1 - Math.min(0.35, delta / 60)))
    const score_nuevo = Math.min(100, redondear(s.score + deltaCompuesto))
    const delta_bps = redondear(deltaCompuesto * BPS_POR_PUNTO)

    return {
      score_nuevo,
      delta_score: redondear(score_nuevo - s.score),
      caja_liberada_eur: Math.round((eco.facturacion_anual / 365) * diasDso),
      delta_bps,
      eur_anio: Math.round((eco.deuda_viva * Math.abs(delta_bps)) / 10_000),
    }
  },

  async getAlerts(desde?: Mes) {
    const a = desde ? ALERTAS.filter((x) => x.mes_deteccion >= desde) : ALERTAS
    const orden = { ALTA: 0, MEDIA: 1, BAJA: 2 }
    return [...a].sort(
      (x, y) => orden[x.severidad] - orden[y.severidad] || y.mes_deteccion.localeCompare(x.mes_deteccion),
    )
  },

  async getPortfolio() {
    return CARTERA
  },
}

const redondear = (v: number) => Math.round(v * 10) / 10

function rechazo(score: number, motivo: string): ResultadoSimulacion {
  return { score_nuevo: score, delta_score: 0, caja_liberada_eur: 0, delta_bps: 0, eur_anio: 0, motivo_rechazo: motivo }
}

export class ApiError extends Error {
  constructor(public codigo: string, mensaje: string) {
    super(mensaje)
  }
}

// ─────────────────────────────────────────── Live, con caída al mock

async function pedir<T>(ruta: string): Promise<T> {
  const res = await fetch(`${BASE}${ruta}`, { cache: 'no-store' })
  if (!res.ok) throw new ApiError(`HTTP_${res.status}`, `${ruta} respondió ${res.status}`)
  return res.json() as Promise<T>
}

let degradado = false
/** true → el front está sirviendo fixtures porque la API real no respondió. */
export const estaDegradado = () => degradado

function conFallback<A extends unknown[], R>(
  live: (...args: A) => Promise<R>,
  fallback: (...args: A) => Promise<R>,
): (...args: A) => Promise<R> {
  return async (...args: A) => {
    try {
      return await live(...args)
    } catch {
      degradado = true
      return fallback(...args)
    }
  }
}

const live: ServicioAPI = {
  getScore: (id, month) => pedir<RespuestaScore>(`/score/${id}${month ? `?month=${month}` : ''}`),
  getGroup: (id) => pedir<RespuestaGrupo>(`/group/${id}`),
  postSimulate: async (peticion) => {
    const res = await fetch(`${BASE}/simulate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(peticion),
      cache: 'no-store',
    })
    if (!res.ok) throw new ApiError(`HTTP_${res.status}`, `/simulate respondió ${res.status}`)
    return res.json() as Promise<ResultadoSimulacion>
  },
  getAlerts: (desde) => pedir<Alerta[]>(`/alerts${desde ? `?desde=${desde}` : ''}`),
  getPortfolio: () => pedir<RespuestaScore[]>(`/portfolio`),
}

export const api: ServicioAPI =
  MODO === 'live' && BASE
    ? {
        getScore: conFallback(live.getScore, mock.getScore),
        getGroup: conFallback(live.getGroup, mock.getGroup),
        postSimulate: conFallback(live.postSimulate, mock.postSimulate),
        getAlerts: conFallback(live.getAlerts, mock.getAlerts),
        getPortfolio: conFallback(live.getPortfolio, mock.getPortfolio),
      }
    : mock
