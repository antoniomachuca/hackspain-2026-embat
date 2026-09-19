/**
 * Contrato B7 · La única frontera entre el front y el motor.
 *
 * Fuente: REQUISITOS.md §B7 y PRODUCTO.md §5. Nombres sin acentos, como el contrato.
 * Dueños del otro lado: Antonio (/score, /group), Pedro (/simulate, /alerts).
 *
 * REGLA: este fichero no se toca sin avisar a los cuatro consumidores (RF-B7.1).
 *
 * Tres extensiones que el front necesita y que NO estaban en el contrato escrito.
 * Están marcadas con [EXT] y hay que confirmarlas con Antonio y Pedro:
 *   [EXT-1] `trayectoria` son objetos, no números. Para cumplir RF-B11.4 ("el gráfico
 *           distingue visualmente nivel y tendencia") hacen falta las tres series, no una.
 *   [EXT-2] `scoring_pendiente` + `meses_historia`. El 32 % de las empresas tiene < 12
 *           meses de historia y RF-B11.9 pide una pantalla real para ese caso.
 *   [EXT-3] `peer` descriptivo. El benchmark es por CUARTIL DE TAMAÑO, no por sector
 *           ni por país (informe_exploracion §1: país 82 % nulo, sector no existe).
 */

// ─────────────────────────────────────────── Enumeraciones del motor (B3, B4, B5)

export type Estado =
  | 'MEJORANDO'
  | 'ESTABLE'
  | 'TORCIENDOSE'
  | 'DETERIORO'
  | 'BACHE'
  | 'RECUPERACION'

export type Semaforo = 'ALTA' | 'MEDIA' | 'BAJA'

export type BloqueFeature = 'LIQUIDEZ' | 'PAGO' | 'DEUDA' | 'CONCENTRACION'

export type CodigoRazon =
  | 'RC_01_FLUJO_INSUFICIENTE'
  | 'RC_02_DETERIORO_COBROS'
  | 'RC_03_CARGA_FINANCIERA'
  | 'RC_04_CONCENTRACION_INGRESOS'
  | 'RC_05_CONFIANZA_LIMITADA'

export type Severidad = 'ALTA' | 'MEDIA' | 'BAJA'

/** Mes canónico en formato `YYYY-MM`. El calendario va de 2024-09 a 2026-09. */
export type Mes = string

// ─────────────────────────────────────────── GET /score/{entity_id}?month=

export interface Driver {
  feature: string
  bloque: BloqueFeature
  /** Puntos de score que aporta este driver. La suma cuadra con el delta (RF-B4). */
  contribucion: number
  /** Valor crudo de la feature, en su unidad de negocio. */
  valor: number
  /** Percentil dentro de su peer group, 0–100. */
  p_peer: number
  unidad: string
}

export interface Confianza {
  /** 0–1. */
  valor: number
  semaforo: Semaforo
  peer_limitado: boolean
}

/** [EXT-1] Un punto de los 24 meses, con las tres series separadas. */
export interface PuntoTrayectoria {
  mes: Mes
  score: number
  nivel: number
  tendencia: number
  estado: Estado
}

/** [EXT-3] El peer group contra el que se compara, descrito para pantalla. */
export interface Peer {
  peer_id: string
  /** "Cuartil de tamaño 3" — nunca "sector": el dataset no trae sector. */
  etiqueta: string
  n_empresas: number
  limitado: boolean
}

export interface RespuestaScore {
  entity_id: string
  mes: Mes
  score: number
  nivel: number
  tendencia: number
  estado: Estado
  confianza: Confianza
  drivers: Driver[]
  trayectoria: PuntoTrayectoria[]
  codigos_razon: CodigoRazon[]
  peer: Peer
  /** [EXT-2] true → la UI enseña "datos insuficientes, scoring pendiente" (RF-B11.9). */
  scoring_pendiente: boolean
  meses_historia: number
  /** Frase legible generada por B4. Nunca sustituye a los números, los acompaña. */
  frase?: string
}

// ─────────────────────────────────────────── GET /group/{group_id}

export interface FilialResumen {
  entity_id: string
  score: number
  tendencia: number
  estado: Estado
  /** Peso en el consolidado (por cobros anualizados). */
  peso: number
}

export interface RespuestaGrupo {
  group_id: string
  mes: Mes
  consolidado: number
  filiales: FilialResumen[]
  peor_filial: string
  penalizacion_contagio: number
}

// ─────────────────────────────────────────── POST /simulate

export type TipoPalanca =
  | 'reducir_dso'
  | 'ampliar_dpo'
  | 'refinanciar'
  | 'bajar_utilizacion_linea'
  | 'reducir_concentracion'
  | 'sustituir_factoring_por_linea'
  | 'recortar_opex'
  | 'descuento_pronto_pago'

export interface Palanca {
  id: TipoPalanca
  parametros: Record<string, number | string | string[]>
}

export interface PeticionSimulacion {
  entity_id: string
  palancas: Palanca[]
}

export interface ResultadoSimulacion {
  score_nuevo: number
  delta_score: number
  /** Pata 1 del puente a euros: aritmética pura, ΔDSO × facturación diaria (RF-B9.1). */
  caja_liberada_eur: number
  /** Pata 2: estimación estadística sobre el tipo implícito. Se etiqueta como tal (RF-B9.5). */
  delta_bps: number
  eur_anio: number
  /** Si la palanca no aplica, viene el motivo y el resto va a cero (RF-B8.5). */
  motivo_rechazo?: string
}

// ─────────────────────────────────────────── GET /alerts?desde=

export interface Alerta {
  entity_id: string
  severidad: Severidad
  mes_deteccion: Mes
  /** Meses de adelanto sobre el cambio de régimen detectado en la serie cruda (B5). */
  meses_anticipacion: number
  estado_nuevo: Estado
  drivers_movidos: Driver[]
  frase: string
}

// ─────────────────────────────────────────── El servicio

export interface ServicioAPI {
  getScore(entity_id: string, month?: Mes): Promise<RespuestaScore>
  getGroup(group_id: string, month?: Mes): Promise<RespuestaGrupo>
  postSimulate(peticion: PeticionSimulacion): Promise<ResultadoSimulacion>
  getAlerts(desde?: Mes): Promise<Alerta[]>
  /** Solo front: la cartera del monitor. Se sirve de fixtures o de un /portfolio futuro. */
  getPortfolio(month?: Mes): Promise<RespuestaScore[]>
}
