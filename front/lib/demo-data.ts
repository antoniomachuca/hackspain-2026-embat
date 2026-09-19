/**
 * Fixtures deterministas de la demo.
 *
 * POR QUÉ: RF-B7.4 (misma entrada, misma salida), RF-B7.7 (modo offline) y RF-B11.5
 * (cero red durante el pitch). El domingo por la mañana esto vale oro.
 *
 * TODO lo de aquí es INVENTADO y sirve para construir pantallas mientras el motor de
 * Carlos y Antonio no existe. Cuando `/score` real responda, se cambia el flag de
 * `lib/api.ts` y el front NO cambia ni una línea (CA-B7).
 *
 * Las dos trayectorias protagonistas están calcadas del enunciado §2:
 * Northbrook 45→65, Velasco 82→68, y a día de hoy 65 vs 68: tres puntos.
 */

import type {
  Alerta,
  BloqueFeature,
  CodigoRazon,
  Driver,
  Estado,
  Mes,
  PuntoTrayectoria,
  RespuestaGrupo,
  RespuestaScore,
} from './contract'
import { EMPRESAS_DEMO, GRUPO_DEMO, NORTHBROOK, VELASCO } from './identity'

/** 24 meses: 2024-10 … 2026-09. El último es el mes vivo de la demo. */
export const MESES: Mes[] = Array.from({ length: 24 }, (_, i) => {
  const m = 9 + i // 2024-10 es el mes 9 contando desde 2024-01
  return `${2024 + Math.floor(m / 12)}-${String((m % 12) + 1).padStart(2, '0')}`
})
export const MES_ACTUAL = MESES[MESES.length - 1]

/** Constante del motor: score = nivel + K · tendencia (B3). */
const K = 2

// ─────────────────────────────────────────── Generador determinista

/** PRNG con semilla. Sin esto los fixtures cambiarían en cada render. */
function rng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Interpola los puntos de control a 24 meses y añade ruido acotado. */
function serie(control: [number, number][], seed: number, ruido = 1.2): number[] {
  const r = rng(seed)
  return MESES.map((_, i) => {
    let j = 0
    while (j < control.length - 2 && control[j + 1][0] < i) j++
    const [x0, y0] = control[j]
    const [x1, y1] = control[j + 1]
    const t = x1 === x0 ? 0 : (i - x0) / (x1 - x0)
    const base = y0 + (y1 - y0) * Math.min(1, Math.max(0, t))
    return clamp(base + (r() - 0.5) * 2 * ruido, 0, 100)
  })
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
const r1 = (v: number) => Math.round(v * 10) / 10

/** Pendiente por mínimos cuadrados sobre los últimos `w` meses, en puntos/mes. */
function pendiente(serie: number[], i: number, w = 6): number {
  const desde = Math.max(0, i - w + 1)
  const ys = serie.slice(desde, i + 1)
  const n = ys.length
  if (n < 2) return 0
  const mx = (n - 1) / 2
  const my = ys.reduce((a, b) => a + b, 0) / n
  let num = 0
  let den = 0
  ys.forEach((y, k) => {
    num += (k - mx) * (y - my)
    den += (k - mx) ** 2
  })
  return den === 0 ? 0 : num / den
}

/** Reglas del brief §6.5, simplificadas. Bache ≠ deterioro: esa es la gracia. */
function estado(scores: number[], tends: number[], i: number): Estado {
  const t = tends[i]
  const n = scores[i]
  const caida6 = i >= 6 ? scores[i] - scores[i - 6] : 0
  const negativosSeguidos = [0, 1, 2].every((k) => (tends[i - k] ?? 0) < -0.4)
  const positivosSeguidos = [0, 1, 2].every((k) => (tends[i - k] ?? 0) > 0.4)

  if (caida6 < -6 && t > 0.5) return 'RECUPERACION'
  if (caida6 < -5 && !negativosSeguidos) return 'BACHE'
  if (negativosSeguidos && n >= 60) return 'TORCIENDOSE'
  if (negativosSeguidos) return 'DETERIORO'
  if (positivosSeguidos) return 'MEJORANDO'
  return 'ESTABLE'
}

// ─────────────────────────────────────────── Perfiles de la cartera

interface Perfil {
  id: string
  /** Puntos de control [índice de mes, score]. */
  control: [number, number][]
  seed: number
  /** Meses de historia. < 12 dispara "scoring pendiente" (RF-B11.9). */
  historia?: number
  confianza: number
  peer: { etiqueta: string; n: number; limitado?: boolean }
  facturacion_anual: number
  deuda_viva: number
  drivers: Driver[]
  codigos: CodigoRazon[]
  frase: string
}

const d = (
  feature: string,
  bloque: BloqueFeature,
  contribucion: number,
  valor: number,
  p_peer: number,
  unidad: string,
): Driver => ({ feature, bloque, contribucion, valor, p_peer, unidad })

const PERFILES: Perfil[] = [
  {
    id: NORTHBROOK,
    control: [[0, 45], [6, 47], [12, 54], [18, 61], [23, 65]],
    seed: 11,
    confianza: 0.86,
    peer: { etiqueta: 'Cuartil de tamaño 3', n: 321 },
    facturacion_anual: 18_400_000,
    deuda_viva: 2_100_000,
    drivers: [
      d('dso_medio', 'PAGO', 4.1, 38, 68, 'días'),
      d('runway_meses', 'LIQUIDEZ', 2.6, 4.2, 61, 'meses'),
      d('utilizacion_linea', 'DEUDA', 1.8, 0.41, 72, '%'),
      d('hhi_clientes', 'CONCENTRACION', -1.2, 0.31, 34, 'índice'),
    ],
    codigos: ['RC_04_CONCENTRACION_INGRESOS'],
    frase:
      'Sube 20 puntos en 24 meses. El motor lo atribuye sobre todo a los días de cobro: 51 → 38 días. Su punto flojo sigue siendo la concentración de clientes.',
  },
  {
    id: VELASCO,
    control: [[0, 82], [10, 81], [14, 78], [18, 74], [23, 68]],
    seed: 23,
    confianza: 0.91,
    peer: { etiqueta: 'Cuartil de tamaño 4', n: 318 },
    facturacion_anual: 29_800_000,
    deuda_viva: 4_000_000,
    drivers: [
      d('dso_medio', 'PAGO', -5.4, 63, 22, 'días'),
      d('pct_facturas_vencidas', 'PAGO', -3.1, 0.28, 18, '%'),
      d('utilizacion_linea', 'DEUDA', -2.9, 0.97, 9, '%'),
      d('dscr_proxy', 'DEUDA', -1.6, 1.08, 26, 'x'),
      d('runway_meses', 'LIQUIDEZ', 0.9, 5.1, 58, 'meses'),
    ],
    codigos: ['RC_02_DETERIORO_COBROS', 'RC_03_CARGA_FINANCIERA'],
    frase:
      'Con 68 sigue pareciendo sana. Pero lleva 9 meses cayendo: sus clientes le pagan 22 días más tarde que hace un año y la línea de crédito está al 97 %.',
  },
  {
    id: 'COMP_0841',
    control: [[0, 74], [12, 77], [23, 79]],
    seed: 31,
    confianza: 0.88,
    peer: { etiqueta: 'Cuartil de tamaño 3', n: 321 },
    facturacion_anual: 9_600_000,
    deuda_viva: 800_000,
    drivers: [
      d('runway_meses', 'LIQUIDEZ', 3.4, 7.8, 84, 'meses'),
      d('dso_medio', 'PAGO', 1.9, 34, 71, 'días'),
    ],
    codigos: [],
    frase: 'Estable en la parte alta. Sin señales de movimiento en ninguna dirección.',
  },
  {
    id: 'COMP_0886',
    control: [[0, 61], [8, 59], [12, 48], [16, 52], [23, 60]],
    seed: 47,
    confianza: 0.79,
    peer: { etiqueta: 'Cuartil de tamaño 2', n: 322 },
    facturacion_anual: 4_200_000,
    deuda_viva: 650_000,
    drivers: [
      d('runway_meses', 'LIQUIDEZ', -2.1, 2.9, 31, 'meses'),
      d('dso_medio', 'PAGO', 2.8, 41, 63, 'días'),
    ],
    codigos: [],
    frase:
      'Cayó 13 puntos en el invierno de 2025 y los ha recuperado. El motor lo clasifica como bache, no como deterioro: la caída no persistió tres meses.',
  },
  {
    id: 'COMP_0329',
    control: [[0, 56], [10, 52], [16, 43], [23, 34]],
    seed: 59,
    confianza: 0.72,
    peer: { etiqueta: 'Cuartil de tamaño 2', n: 322 },
    facturacion_anual: 3_100_000,
    deuda_viva: 1_450_000,
    drivers: [
      d('dscr_proxy', 'DEUDA', -6.2, 0.71, 6, 'x'),
      d('pct_facturas_vencidas', 'PAGO', -4.4, 0.41, 8, '%'),
      d('runway_meses', 'LIQUIDEZ', -3.8, 1.2, 11, 'meses'),
    ],
    codigos: ['RC_01_FLUJO_INSUFICIENTE', 'RC_03_CARGA_FINANCIERA'],
    frase:
      'Deterioro estructural sostenido. El servicio de deuda se come el flujo operativo desde hace siete meses.',
  },
  {
    id: 'COMP_0831',
    control: [[0, 38], [8, 44], [16, 55], [23, 67]],
    seed: 67,
    confianza: 0.83,
    peer: { etiqueta: 'Cuartil de tamaño 1', n: 325 },
    facturacion_anual: 1_900_000,
    deuda_viva: 240_000,
    drivers: [
      d('dso_medio', 'PAGO', 5.8, 29, 88, 'días'),
      d('runway_meses', 'LIQUIDEZ', 3.1, 6.4, 76, 'meses'),
    ],
    codigos: [],
    frase: 'La mejor trayectoria de la cartera: +29 puntos, sin un solo mes de retroceso.',
  },
  {
    id: 'COMP_0809',
    control: [[0, 70], [12, 69], [23, 71]],
    seed: 71,
    confianza: 0.81,
    peer: { etiqueta: 'Cuartil de tamaño 3', n: 321 },
    facturacion_anual: 7_300_000,
    deuda_viva: 1_100_000,
    drivers: [d('dso_medio', 'PAGO', 1.2, 44, 55, 'días')],
    codigos: [],
    frase: 'Plana. Es exactamente lo que parece.',
  },
  {
    id: 'COMP_0671',
    control: [[0, 64], [14, 63], [19, 57], [23, 49]],
    seed: 83,
    confianza: 0.77,
    peer: { etiqueta: 'Cuartil de tamaño 2', n: 322 },
    facturacion_anual: 5_400_000,
    deuda_viva: 1_800_000,
    drivers: [
      d('utilizacion_linea', 'DEUDA', -4.9, 1.0, 3, '%'),
      d('hhi_clientes', 'CONCENTRACION', -3.3, 0.58, 12, 'índice'),
    ],
    codigos: ['RC_03_CARGA_FINANCIERA', 'RC_04_CONCENTRACION_INGRESOS'],
    frase:
      'Línea de crédito agotada y un solo cliente concentra el 58 % de la facturación. Empezó a torcerse en marzo.',
  },
  {
    id: 'COMP_0308',
    control: [[0, 51], [12, 55], [23, 58]],
    seed: 97,
    confianza: 0.69,
    peer: { etiqueta: 'Peer limitado', n: 31, limitado: true },
    facturacion_anual: 2_400_000,
    deuda_viva: 390_000,
    drivers: [d('runway_meses', 'LIQUIDEZ', 1.7, 3.8, 52, 'meses')],
    codigos: ['RC_05_CONFIANZA_LIMITADA'],
    frase:
      'Mejora leve, pero el 44 % de sus movimientos llega sin categoría: la confianza del score es media.',
  },
  {
    id: 'COMP_0363',
    control: [[0, 47], [10, 46], [23, 44]],
    seed: 101,
    historia: 7,
    confianza: 0.31,
    peer: { etiqueta: 'Peer limitado', n: 31, limitado: true },
    facturacion_anual: 1_100_000,
    deuda_viva: 120_000,
    drivers: [],
    codigos: ['RC_05_CONFIANZA_LIMITADA'],
    frase:
      'Solo 7 meses de historia conectada. El motor no emite score: hacen falta 12 meses para medir trayectoria.',
  },
  // Filiales del grupo de demostración
  { id: 'COMP_0945', control: [[0, 68], [23, 74]], seed: 113, confianza: 0.84, peer: { etiqueta: 'Cuartil de tamaño 3', n: 321 }, facturacion_anual: 6_100_000, deuda_viva: 700_000, drivers: [d('dso_medio', 'PAGO', 2.2, 36, 69, 'días')], codigos: [], frase: 'La filial que tira del grupo hacia arriba.' },
  { id: 'COMP_0578', control: [[0, 59], [23, 63]], seed: 127, confianza: 0.80, peer: { etiqueta: 'Cuartil de tamaño 2', n: 322 }, facturacion_anual: 3_800_000, deuda_viva: 520_000, drivers: [d('runway_meses', 'LIQUIDEZ', 1.4, 4.0, 57, 'meses')], codigos: [], frase: 'Mejora contenida y sin sobresaltos.' },
  { id: 'COMP_0278', control: [[0, 55], [10, 49], [23, 38]], seed: 131, confianza: 0.74, peer: { etiqueta: 'Cuartil de tamaño 2', n: 322 }, facturacion_anual: 2_900_000, deuda_viva: 1_600_000, drivers: [d('dscr_proxy', 'DEUDA', -5.1, 0.64, 4, 'x'), d('pct_facturas_vencidas', 'PAGO', -3.7, 0.37, 9, '%')], codigos: ['RC_01_FLUJO_INSUFICIENTE'], frase: 'La filial francesa saca 38 y arrastra al consolidado del grupo.' },
  { id: 'COMP_0042', control: [[0, 66], [23, 69]], seed: 137, confianza: 0.78, peer: { etiqueta: 'Cuartil de tamaño 3', n: 321 }, facturacion_anual: 5_200_000, deuda_viva: 900_000, drivers: [d('dso_medio', 'PAGO', 1.6, 40, 60, 'días')], codigos: [], frase: 'Estable. Moneda USD, convertida a EUR para el consolidado.' },
]

// ─────────────────────────────────────────── Construcción de las respuestas

function construir(p: Perfil): RespuestaScore {
  const scores = serie(p.control, p.seed).map(r1)
  const tends = scores.map((_, i) => r1(pendiente(scores, i)))
  const niveles = scores.map((s, i) => r1(s - K * tends[i]))

  const historia = p.historia ?? 24
  const desde = 24 - historia

  const trayectoria: PuntoTrayectoria[] = MESES.slice(desde).map((mes, k) => {
    const i = desde + k
    return {
      mes,
      score: scores[i],
      nivel: niveles[i],
      tendencia: tends[i],
      estado: estado(scores, tends, i),
    }
  })

  const ultimo = trayectoria[trayectoria.length - 1]

  return {
    entity_id: p.id,
    mes: MES_ACTUAL,
    score: ultimo.score,
    nivel: ultimo.nivel,
    tendencia: ultimo.tendencia,
    estado: ultimo.estado,
    confianza: {
      valor: p.confianza,
      semaforo: p.confianza >= 0.75 ? 'ALTA' : p.confianza >= 0.5 ? 'MEDIA' : 'BAJA',
      peer_limitado: p.peer.limitado ?? false,
    },
    drivers: p.drivers,
    trayectoria,
    codigos_razon: p.codigos,
    peer: {
      peer_id: p.peer.etiqueta.toLowerCase().replace(/\s+/g, '_'),
      etiqueta: p.peer.etiqueta,
      n_empresas: p.peer.n,
      limitado: p.peer.limitado ?? false,
    },
    scoring_pendiente: historia < 12,
    meses_historia: historia,
    frase: p.frase,
  }
}

export const SCORES: Record<string, RespuestaScore> = Object.fromEntries(
  PERFILES.map((p) => [p.id, construir(p)]),
)

/** Datos económicos que usa el mock de /simulate. No son parte del contrato. */
export const ECONOMICS: Record<string, { facturacion_anual: number; deuda_viva: number }> =
  Object.fromEntries(
    PERFILES.map((p) => [
      p.id,
      { facturacion_anual: p.facturacion_anual, deuda_viva: p.deuda_viva },
    ]),
  )

export const CARTERA = EMPRESAS_DEMO.map((id) => SCORES[id]).filter(Boolean)

// ─────────────────────────────────────────── Alertas (B5)

export const ALERTAS: Alerta[] = [
  {
    entity_id: VELASCO,
    severidad: 'ALTA',
    mes_deteccion: '2026-04',
    meses_anticipacion: 4,
    estado_nuevo: 'TORCIENDOSE',
    drivers_movidos: SCORES[VELASCO].drivers.slice(0, 3),
    frase:
      'Lleva tres meses torciéndose. Lo vimos en abril, cuatro meses antes de que se notara en el nivel.',
  },
  {
    entity_id: 'COMP_0329',
    severidad: 'ALTA',
    mes_deteccion: '2026-01',
    meses_anticipacion: 5,
    estado_nuevo: 'DETERIORO',
    drivers_movidos: SCORES['COMP_0329'].drivers.slice(0, 2),
    frase: 'Deterioro estructural confirmado: siete meses consecutivos de caída.',
  },
  {
    entity_id: 'COMP_0671',
    severidad: 'MEDIA',
    mes_deteccion: '2026-03',
    meses_anticipacion: 3,
    estado_nuevo: 'TORCIENDOSE',
    drivers_movidos: SCORES['COMP_0671'].drivers,
    frase: 'Línea de crédito al 100 % y concentración de clientes al alza.',
  },
  {
    entity_id: 'COMP_0831',
    severidad: 'BAJA',
    mes_deteccion: '2025-11',
    meses_anticipacion: 4,
    estado_nuevo: 'MEJORANDO',
    drivers_movidos: SCORES['COMP_0831'].drivers,
    frase:
      'Señal en la otra dirección: mejora sostenida desde hace diez meses. Candidata a ampliar límite.',
  },
]

// ─────────────────────────────────────────── Grupo (B6)

export const GRUPOS_DEMO: Record<string, RespuestaGrupo> = {
  [GRUPO_DEMO]: (() => {
    const ids = ['COMP_0471', 'COMP_0945', 'COMP_0578', 'COMP_0278', 'COMP_0042']
    const pesos = [0.38, 0.22, 0.14, 0.11, 0.15]
    const filiales = ids.map((id, i) => ({
      entity_id: id,
      score: SCORES[id].score,
      tendencia: SCORES[id].tendencia,
      estado: SCORES[id].estado,
      peso: pesos[i],
    }))
    const media = filiales.reduce((a, f) => a + f.score * f.peso, 0)
    const peor = filiales.reduce((a, f) => (f.score < a.score ? f : a))
    const penalizacion = r1((media - peor.score) * 0.15)
    return {
      group_id: GRUPO_DEMO,
      mes: MES_ACTUAL,
      consolidado: r1(media - penalizacion),
      filiales,
      peor_filial: peor.entity_id,
      penalizacion_contagio: penalizacion,
    }
  })(),
}
