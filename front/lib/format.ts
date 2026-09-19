/**
 * Formato y vocabulario de pantalla.
 *
 * Reglas de RF-B11.8 y del research de producto (§5):
 *  · Cifras con tabular figures, para que alineen en tabla.
 *  · El estado SIEMPRE lleva texto, nunca solo color (8 % de daltonismo rojo-verde).
 *  · Eje continuo ámbar → aguamarina. Ni semáforos ni tres círculos.
 */

import type { BloqueFeature, CodigoRazon, Estado, Semaforo, Severidad } from './contract'

const eur = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const num = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 })

export const fmtEur = (v: number) => eur.format(v)
export const fmtNum = (v: number) => num.format(v)
export const fmtPuntos = (v: number) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${num.format(Math.abs(v))}`
export const fmtBps = (v: number) => `${v > 0 ? '+' : '−'}${num.format(Math.abs(v))} bps`

const MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

/** `2026-04` → `abr 26`. */
export function fmtMes(mes: string): string {
  const [a, m] = mes.split('-')
  return `${MESES_ES[Number(m) - 1]} ${a.slice(2)}`
}

/** `2026-04` → `abril de 2026`, para prosa. */
export function fmtMesLargo(mes: string): string {
  const largos = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
  const [a, m] = mes.split('-')
  return `${largos[Number(m) - 1]} de ${a}`
}

// ─────────────────────────────────────────── Vocabulario

export const ESTADO_TEXTO: Record<Estado, string> = {
  MEJORANDO: 'Mejorando',
  ESTABLE: 'Estable',
  TORCIENDOSE: 'Empieza a torcerse',
  DETERIORO: 'Deterioro',
  BACHE: 'Bache puntual',
  RECUPERACION: 'Recuperación',
}

/** Dirección del estado. Decide el color, pero el color nunca va solo. */
export const ESTADO_SIGNO: Record<Estado, 'positivo' | 'neutro' | 'negativo'> = {
  MEJORANDO: 'positivo',
  RECUPERACION: 'positivo',
  ESTABLE: 'neutro',
  BACHE: 'neutro',
  TORCIENDOSE: 'negativo',
  DETERIORO: 'negativo',
}

export const SEMAFORO_TEXTO: Record<Semaforo, string> = {
  ALTA: 'Confianza alta',
  MEDIA: 'Confianza media',
  BAJA: 'Confianza baja',
}

export const SEVERIDAD_TEXTO: Record<Severidad, string> = {
  ALTA: 'Alta',
  MEDIA: 'Media',
  BAJA: 'Informativa',
}

export const BLOQUE_TEXTO: Record<BloqueFeature, string> = {
  LIQUIDEZ: 'Liquidez',
  PAGO: 'Comportamiento de pago',
  DEUDA: 'Carga financiera',
  CONCENTRACION: 'Concentración',
}

export const CODIGO_TEXTO: Record<CodigoRazon, string> = {
  RC_01_FLUJO_INSUFICIENTE: 'Flujo operativo insuficiente para el servicio de deuda',
  RC_02_DETERIORO_COBROS: 'Deterioro en el comportamiento de cobro',
  RC_03_CARGA_FINANCIERA: 'Carga financiera por encima de su peer group',
  RC_04_CONCENTRACION_INGRESOS: 'Ingresos concentrados en pocos clientes',
  RC_05_CONFIANZA_LIMITADA: 'Historia o cobertura de datos limitada',
}

/** Nombres de feature en lenguaje de tesorero, no de pipeline. */
export const FEATURE_TEXTO: Record<string, string> = {
  dso_medio: 'Días de cobro (DSO)',
  dpo_medio: 'Días de pago (DPO)',
  pct_facturas_vencidas: 'Facturas vencidas sobre el total',
  utilizacion_linea: 'Utilización de la línea de crédito',
  dscr_proxy: 'Cobertura del servicio de deuda',
  runway_meses: 'Meses de caja (runway)',
  hhi_clientes: 'Concentración de clientes',
}

export const featureTexto = (f: string) => FEATURE_TEXTO[f] ?? f

/** Banda del score. Cuatro tramos, con nombre: el número solo no dice nada. */
export function banda(score: number): { etiqueta: string; desde: number; hasta: number } {
  if (score >= 75) return { etiqueta: 'Sólida', desde: 75, hasta: 100 }
  if (score >= 55) return { etiqueta: 'Aceptable', desde: 55, hasta: 75 }
  if (score >= 35) return { etiqueta: 'Vigilancia', desde: 35, hasta: 55 }
  return { etiqueta: 'Riesgo', desde: 0, hasta: 35 }
}

/**
 * Color del score sobre el eje continuo ámbar → aguamarina.
 * Devuelve una variable CSS, no un hex: el tema manda.
 */
export function colorScore(score: number): string {
  if (score >= 75) return 'var(--score-alto)'
  if (score >= 55) return 'var(--score-medio)'
  if (score >= 35) return 'var(--score-bajo)'
  return 'var(--score-critico)'
}
