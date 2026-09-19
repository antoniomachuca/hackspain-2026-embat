/**
 * Capa de identidad · company_id → razón social.
 *
 * POR QUÉ EXISTE: el dataset NO trae nombre de empresa. `companies.csv` es
 * `company_id, group_id, country, currency, erp, created_at` y nada más. Una cartera
 * llena de `COMP_0218` se lee como un notebook, no como un producto, y "artesanía" es
 * un criterio de evaluación explícito (enunciado §7).
 *
 * HONESTIDAD: los nombres son ETIQUETAS DE DEMO sobre IDs anónimos. Se dice en pantalla
 * (ver `NOTA_IDENTIDAD`) y en el pitch. Northbrook Foods y Velasco Industrial son los
 * nombres del propio enunciado §2, aplicados a dos empresas reales del dataset elegidas
 * porque su trayectoria encaja (45→65 y 82→68).
 *
 * LO QUE NO HACEMOS: inventar sector. No existe en el dataset, y el peer group es por
 * CUARTIL DE TAMAÑO (informe_exploracion §8). La UI nunca dice "benchmark sectorial".
 *
 * PENDIENTE: los `company_id` de abajo se eligieron por `created_at` temprano como proxy
 * de historia larga. Cuando Carlos cierre B0, sustituirlos por dos de las 373 empresas con
 * 24 meses completos cuya trayectoria real encaje (RF-B11.5).
 */

export const NOTA_IDENTIDAD =
  'Nombres de demostración sobre empresas anónimas del dataset sintético de Embat.'

export interface Identidad {
  company_id: string
  nombre: string
  /** El país sí está en el dataset, aunque el 82 % sea nulo. Solo se muestra si existe. */
  pais?: string
  moneda: string
  group_id: string
}

const REGISTRO: Identidad[] = [
  // ── Los dos casos del enunciado §2
  { company_id: 'COMP_0471', nombre: 'Northbrook Foods',        pais: 'ES', moneda: 'EUR', group_id: 'GROUP_0162' },
  { company_id: 'COMP_0840', nombre: 'Velasco Industrial',      pais: 'ES', moneda: 'EUR', group_id: 'GROUP_0248' },

  // ── Cartera de apoyo: que todos los estados de la UI tengan contenido
  { company_id: 'COMP_0841', nombre: 'Suministros Hidráulicos del Ebro', pais: 'ES', moneda: 'EUR', group_id: 'GROUP_0005' },
  { company_id: 'COMP_0886', nombre: 'Cerámicas Altamira',      pais: 'ES', moneda: 'EUR', group_id: 'GROUP_0161' },
  { company_id: 'COMP_0329', nombre: 'Envases Lumar',                        moneda: 'EUR', group_id: 'GROUP_0161' },
  { company_id: 'COMP_0831', nombre: 'Talleres Ordoñez',                     moneda: 'EUR', group_id: 'GROUP_0250' },
  { company_id: 'COMP_0809', nombre: 'Frigoríficos del Segura',              moneda: 'EUR', group_id: 'GROUP_0250' },
  { company_id: 'COMP_0671', nombre: 'Montajes Eléctricos Bilbao',           moneda: 'EUR', group_id: 'GROUP_0250' },
  { company_id: 'COMP_0308', nombre: 'Aceites Peñalba',                      moneda: 'EUR', group_id: 'GROUP_0250' },
  { company_id: 'COMP_0363', nombre: 'Logística Ronda',                      moneda: 'EUR', group_id: 'GROUP_0250' },

  // ── El grupo multi-entidad (GROUP_0162 es real y multi-país: ES, FR, US, VND)
  { company_id: 'COMP_0945', nombre: 'Northbrook Ibérica',      pais: 'ES', moneda: 'EUR', group_id: 'GROUP_0162' },
  { company_id: 'COMP_0578', nombre: 'Northbrook Levante',      pais: 'ES', moneda: 'EUR', group_id: 'GROUP_0162' },
  { company_id: 'COMP_0278', nombre: 'Northbrook France',       pais: 'FR', moneda: 'EUR', group_id: 'GROUP_0162' },
  { company_id: 'COMP_0042', nombre: 'Northbrook US',           pais: 'US', moneda: 'USD', group_id: 'GROUP_0162' },
]

const POR_ID = new Map(REGISTRO.map((i) => [i.company_id, i]))

export const GRUPOS: Record<string, string> = {
  GROUP_0162: 'Grupo Northbrook',
  GROUP_0248: 'Velasco',
  GROUP_0250: 'Grupo Ordoñez',
  GROUP_0161: 'Grupo Altamira',
  GROUP_0005: 'Hidráulicos del Ebro',
}

export function identidad(company_id: string): Identidad {
  return (
    POR_ID.get(company_id) ?? {
      company_id,
      nombre: company_id,
      moneda: 'EUR',
      group_id: 'GROUP_DESCONOCIDO',
    }
  )
}

export function nombre(company_id: string): string {
  return identidad(company_id).nombre
}

export function nombreGrupo(group_id: string): string {
  return GRUPOS[group_id] ?? group_id
}

/** Iniciales para el avatar de la lista. Dos letras, sin artículos. */
export function iniciales(company_id: string): string {
  return nombre(company_id)
    .split(/\s+/)
    .filter((p) => !['de', 'del', 'la', 'el', 'y'].includes(p.toLowerCase()))
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}

export const EMPRESAS_DEMO = REGISTRO.map((i) => i.company_id)

/** Los dos protagonistas del pitch (enunciado §2). */
export const NORTHBROOK = 'COMP_0471'
export const VELASCO = 'COMP_0840'
export const GRUPO_DEMO = 'GROUP_0162'
