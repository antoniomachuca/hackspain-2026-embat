// Datos mockeados con la forma del contrato de /score, /group, /palancas y /simulate.
// Determinista: misma semilla → mismos datos en cada render y en cada máquina.
// Sustituir por llamadas reales cambiando solo lib/api.ts.

import { num } from "./format";

export type Estado =
  | "MEJORANDO" | "ESTABLE" | "TORCIENDOSE" | "DETERIORO" | "BACHE" | "RECUPERACION";

export type Driver = {
  feature: string;
  etiqueta: string;
  contribucion: number;   // puntos, con signo. Las seis suman el score.
  valor: string;          // el valor en unidades de negocio
  p_peer: number;         // percentil dentro de su grupo de pares
  codigo?: string;
  rango?: string;
  descripcion?: string;
  diagnostico?: string;
};

export type Severidad = "ALTA" | "MEDIA" | "BAJA";

export type Alerta = {
  severidad: Severidad;
  mesDeteccion: string;
  mesesAnticipacion: number;
  driversMovidos: string[];   // los dos causales que la dispararon
  codigosRazon: string[];     // códigos normalizados
  texto: string;
};

/** Trazabilidad: va en cada respuesta del motor. */
export const MODEL_VERSION = "xray-1.0.0+d41f2ac";
/** Medida a una tasa fijada de 1 falsa alarma por empresa-año en las sanas. */
export const ANTICIPACION_MEDIANA = 8;

export type Punto = { mes: string; score: number; nivel: number };

/** La mediana del cuartil de pares, mes a mes. El benchmark del motor es por
 *  CUARTIL DE TAMAÑO, no por sector: el dataset no trae sector fiable. */
export type PuntoPeer = { mes: string; mediana: number };

/** Bache o tendencia: el movimiento del mes, partido en la parte que persiste
 *  y la que revierte. `pctTendencia + pctBache = 100` salvo en los meses planos. */
/**
 * El reparto mes a mes entre lo que se queda (tendencia) y lo que revierte
 * (bache). Lo calcula el motor congelando los flujos del mes anterior y
 * descongelando campo a campo; el front solo lo pinta. Al usuario nunca se le
 * dicen las palabras internas: `estructural` es «tendencia» y `coyuntural`,
 * «bache».
 */
export type KindMes = "estructural" | "coyuntural";
export type FamilyMes = "salud" | "circulante" | "dato" | "formula";

export type DriverMes = {
  field: string;
  etiqueta: string;     // ya traducida por el motor
  points: number;       // puntos de score, con signo; suman ≈ delta
  kind: KindMes;
  family: FamilyMes;
  reason: string;       // clave estable
  razon: string;        // frase corta ya traducida: se pinta tal cual
};

export type Reparto = {
  mes: string;
  delta: number;
  pctTendencia: number;
  pctBache: number;
  structPts: number;
  circPts: number;
  drivers: DriverMes[];
};

/** El mes en que la serie cambió de régimen, con el juicio de si fue la empresa
 *  o fue su cuartil. Ese juicio es el producto. */
export type Inflexion = {
  mes: string;
  direccion: "mejora" | "deterioro";
  mesesRegimen: number;
  deltaEmpresa: number;
  deltaPeer: number;
  /** 0–1 · qué fracción del movimiento explica el cuartil. */
  partePeer: number;
  frase: string;
};

export type Empresa = {
  id: string;
  nombre: string;
  grupo: string;
  grupoNombre: string;
  sector: string;
  moneda: string;
  score: number;
  scorePrev: number;
  nivelBase: number;      // B_t · el nivel, sin inercia
  momentum: number;       // M_t ∈ [-1, 1] · la tendencia
  delta3m?: number;       // variación del score en tres meses
  elegible?: boolean;     // historia suficiente para tener estado
  clipping: number;       // residuo de recorte a [0,100]
  estado: Estado;
  confianza: "ALTA" | "MEDIA" | "BAJA";
  mesesHistoria: number;
  facturacionAnual: number;
  saldoBancario?: number;
  dso: number;
  dpo: number;
  diasCaja: number;
  utilizacionLinea: number;
  hhiClientes: number;
  trayectoria: Punto[];
  // Opcionales: los datos de demostración los calculan, pero el motor todavía
  // no los sirve (peer group, reparto tendencia/bache, inflexión). El gráfico
  // los trata como capas que aparecen si existen.
  peer?: { etiqueta: string; n: number };
  trayectoriaPeer?: PuntoPeer[];
  reparto?: Reparto[];
  inflexion?: Inflexion;
  drivers: Driver[];
  alerta?: Alerta;
};

// ── Generador determinista ────────────────────────────────────────────
function rng(seed: number) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

const MESES = (() => {
  const out: string[] = [];
  for (let i = 0; i < 24; i++) {
    const d = new Date(Date.UTC(2024, 9 + i, 1));
    out.push(d.toISOString().slice(0, 7));
  }
  return out;
})();

export const MES_ACTUAL = MESES[23];

/** Casos verificados contra el motor (respuestas_a_pedro.md). Los cinco
 *  primeros llevan score y estado reales; el resto son relleno de cartera. */
export const CASOS_DEMO = ["COMP_0001", "COMP_0002", "COMP_0003", "COMP_0004", "COMP_0005"];

const NOMBRES: [string, string][] = [
  ["Suministros Hidráulicos del Ebro", "Distribución industrial"],
  ["Northbrook Foods Ibérica", "Alimentación"],
  ["Velasco Industrial", "Metalurgia"],
  ["Cerámicas Altamira", "Materiales de construcción"],
  ["Logística Peninsular Duero", "Transporte"],
  ["Textiles Mancha Real", "Textil"],
  ["Envases Torrelavega", "Packaging"],
  ["Clínicas Dental Sur", "Salud"],
  ["Ferretería Marín Hermanos", "Retail industrial"],
  ["Bodegas Camino Viejo", "Bebidas"],
  ["Instalaciones Térmicas Náquera", "Instalaciones"],
  ["Papelera del Cantábrico", "Papel"],
  ["Rótulos y Señalética Levante", "Publicidad"],
  ["Congelados Atlántico Norte", "Alimentación"],
  ["Mecanizados Precisión Álava", "Automoción"],
  ["Jardinería Urbana Sevilla", "Servicios"],
  ["Componentes Eléctricos Tajo", "Electrónica"],
  ["Distribuciones Farmacéuticas Genil", "Farma"],
  ["Plásticos Reciclados Aragón", "Reciclaje"],
  ["Servicios Informáticos Meridiano", "IT"],
  ["Aislamientos Térmicos Norte", "Construcción"],
  ["Frutas y Verduras La Vega", "Alimentación"],
  ["Transportes Refrigerados Segura", "Transporte"],
  ["Calderería Industrial Besós", "Metalurgia"],
];

const GRUPOS: [string, string][] = [
  ["GROUP_0147", "Grupo Ebro Industrial"],
  ["GROUP_0022", "Northbrook Holding"],
  ["GROUP_0091", "Velasco Participaciones"],
  ["GROUP_0308", "Altamira Materiales"],
  ["GROUP_0455", "Duero Logística"],
];

// Perfiles de trayectoria: cada uno cuenta una historia distinta
type Perfil = "recupera" | "cae" | "estable" | "bache" | "solido" | "fragil";

function serie(perfil: Perfil, r: () => number): number[] {
  const out: number[] = [];
  let base: number;
  switch (perfil) {
    case "recupera": base = 45; break;
    case "cae":      base = 82; break;
    case "estable":  base = 62; break;
    case "bache":    base = 68; break;
    case "solido":   base = 79; break;
    default:         base = 34;
  }
  for (let i = 0; i < 24; i++) {
    const t = i / 23;
    let v = base;
    if (perfil === "recupera") v = 45 + 20 * t + (r() - 0.5) * 3;
    if (perfil === "cae")      v = 82 - 14 * Math.pow(t, 1.4) + (r() - 0.5) * 2.5;
    if (perfil === "estable")  v = 62 + Math.sin(i / 3) * 2.5 + (r() - 0.5) * 2;
    if (perfil === "bache")    v = 68 - (i >= 12 && i <= 16 ? 14 : 0) + (r() - 0.5) * 2;
    if (perfil === "solido")   v = 79 + 5 * t + (r() - 0.5) * 2;
    if (perfil === "fragil")   v = 34 - 6 * t + (r() - 0.5) * 3;
    out.push(Math.max(3, Math.min(97, Math.round(v * 10) / 10)));
  }
  return out;
}

function estadoDe(s: number[]): Estado {
  const d3 = s[23] - s[20];
  const d6 = s[23] - s[17];
  const min = Math.min(...s.slice(12));
  if (s[23] - min > 9 && d3 > 1) return "RECUPERACION";
  if (d6 > 5) return "MEJORANDO";
  if (d6 < -9) return "DETERIORO";
  if (d6 < -3) return "TORCIENDOSE";
  if (Math.abs(d6) <= 3 && min < s[23] - 8) return "BACHE";
  return "ESTABLE";
}

export const DESCRIPCIONES_FACTORES: Record<string, { codigo: string; rango: string; desc: string }> = {
  liquidity: {
    codigo: "LIQ-02",
    rango: "0 a 50 pts",
    desc: "Colchón de tesorería y autonomía frente al gasto operativo diario (burn rate). Mide los días de caja disponibles sin recurrir a deuda externa.",
  },
  collections: {
    codigo: "COB-01",
    rango: "0 a 30 pts",
    desc: "Velocidad de rotación y cobro a clientes (DSO) y disciplina en vencimientos sin facturas en mora impagadas.",
  },
  debt: {
    codigo: "DEU-03",
    rango: "0 a 20 pts",
    desc: "Capacidad de servicio de deuda y margen de crédito disponible en pólizas o líneas de circulante.",
  },
  momentum: {
    codigo: "MOM-01",
    rango: "−15 a +15 pts",
    desc: "Inercia reciente y tendencia del flujo de tesorería a 3–6 meses. Bonifica aceleración o penaliza deterioro continuado.",
  },
  growth: {
    codigo: "CRE-02",
    rango: "−10 a +10 pts",
    desc: "Crecimiento sostenible de ventas y facturación comercial emitida sin provocar descalces en el fondo de maniobra.",
  },
  fragility: {
    codigo: "FRA-01",
    rango: "−8 a 0 pts",
    desc: "Penalización por volatilidad intradía de saldos, concentración excesiva de clientes (HHI) y descalce de pagos.",
  },
};

const CODIGOS: Record<string, string> = {
  liquidity: "LIQ-02", collections: "COB-01", debt: "DEU-03",
  momentum: "MOM-01", growth: "CRE-02", fragility: "FRA-01",
};

function driversDe(
  score: number, dso: number, util: number, hhi: number, dias: number,
  momentum: number, r: () => number,
): Driver[] {
  // Los seis bloques que emite el motor (columnas *_points de scores_monthly).
  // La descomposición es aditiva exacta: no hay SHAP ni aproximación local.
  const brutos = [
    { feature: "liquidity",   etiqueta: "Liquidez",     peso: 0.30, valor: `${dias} días de caja`,   p: Math.min(98, Math.round(dias * 1.4)) },
    { feature: "collections", etiqueta: "Cobros",       peso: 0.24, valor: `DSO ${dso} días`,         p: Math.max(3, 100 - dso) },
    { feature: "debt",        etiqueta: "Deuda",        peso: 0.20, valor: `línea al ${util}%`,       p: Math.max(3, 100 - util) },
    { feature: "momentum",    etiqueta: "Momentum",     peso: 0.12, valor: momentum.toFixed(2),       p: Math.round((momentum + 1) * 50) },
    { feature: "growth",      etiqueta: "Crecimiento",  peso: 0.09, valor: r() > 0.5 ? "sostenido" : "plano", p: Math.round(r() * 100) },
    { feature: "fragility",   etiqueta: "Fragilidad",   peso: 0.05, valor: `HHI ${hhi.toFixed(2)}`,   p: Math.round((1 - hhi) * 100) },
  ];
  const suma = brutos.reduce((a, b) => a + b.peso * b.p, 0);
  const k = score / (suma / 100);
  const ds: Driver[] = brutos.map((b) => {
    const meta = DESCRIPCIONES_FACTORES[b.feature];
    const diag =
      b.p >= 70 ? `Rendimiento favorable en ${b.etiqueta.toLowerCase()}` :
      b.p >= 40 ? `Nivel moderado de ${b.etiqueta.toLowerCase()}` :
      `Tensión detectada en ${b.etiqueta.toLowerCase()}`;
    return {
      feature: b.feature,
      etiqueta: b.etiqueta,
      codigo: meta?.codigo ?? CODIGOS[b.feature] ?? "—",
      rango: meta?.rango ?? "—",
      descripcion: meta?.desc ?? "",
      diagnostico: diag,
      contribucion: Math.round(b.peso * b.p * k) / 100,
      valor: b.valor,
      p_peer: b.p,
    };
  });
  const total = ds.reduce((a, b) => a + b.contribucion, 0);
  ds[0].contribucion = Math.round((ds[0].contribucion + (score - total)) * 100) / 100;
  return ds.sort((a, b) => b.contribucion - a.contribucion);
}

const PERFILES: Perfil[] = [
  "recupera", "cae", "estable", "bache", "solido", "fragil",
  "estable", "cae", "recupera", "solido", "bache", "estable",
  "fragil", "solido", "cae", "estable", "recupera", "bache",
  "estable", "solido", "cae", "fragil", "estable", "recupera",
];

/** Anclas verificadas contra el motor: score, estado y delta a 3 meses. */
const ANCLAS: Record<number, { score: number; estado: Estado; d3: number; caso: string }> = {
  0: { score: 83.4, estado: "ESTABLE",      d3:  15.3, caso: "Empresa excelente de control" },
  1: { score: 57.4, estado: "TORCIENDOSE",  d3: -18.7, caso: "Alerta temprana preventiva" },
  2: { score:  5.1, estado: "DETERIORO",    d3: -77.7, caso: "Colapso de solvencia" },
  3: { score: 45.6, estado: "BACHE",        d3: -26.7, caso: "Bache, no insolvencia" },
  4: { score: 67.5, estado: "RECUPERACION", d3:  44.9, caso: "Trayectoria de éxito" },
};

// ── El cuartil de pares ───────────────────────────────────────────────
// Sin esta serie el gráfico enseña una línea que baja. Con ella se puede decir
// si baja sola o si baja todo su cuartil con ella, que es otra conversación.

const CUARTILES: { techo: number; control: [number, number][]; n: number }[] = [
  { techo:  3_000_000, control: [[0, 52], [12, 54], [23, 56]], n: 319 },
  // El invierno de 2025 fue malo para todo el cuartil 2, no solo para quien lo sufrió.
  { techo:  7_000_000, control: [[0, 58], [8, 58], [12, 52], [16, 55], [23, 58]], n: 322 },
  { techo: 12_000_000, control: [[0, 60], [12, 61], [23, 62]], n: 321 },
  // El 4 sigue plano mientras alguno de los suyos cae: ahí sí hay que preocuparse.
  { techo: Infinity,   control: [[0, 66], [12, 67], [23, 68]], n: 318 },
];

function cuartil(facturacion: number) {
  const k = CUARTILES.findIndex((c) => facturacion < c.techo);
  return { idx: k + 1, etiqueta: `Cuartil de tamaño ${k + 1}`, ...CUARTILES[k] };
}

/** Cacheada por cuartil: la comparten muchas empresas y tiene que salir idéntica. */
const SERIE_PEER = new Map<number, number[]>();
function medianaPeer(idx: number, control: [number, number][]): number[] {
  const hecha = SERIE_PEER.get(idx);
  if (hecha) return hecha;
  const r = rng(7000 + idx * 131);
  const s = MESES.map((_, i) => {
    let j = 0;
    while (j < control.length - 2 && control[j + 1][0] < i) j++;
    const [x0, y0] = control[j], [x1, y1] = control[j + 1];
    const t = x1 === x0 ? 0 : (i - x0) / (x1 - x0);
    return Math.round((y0 + (y1 - y0) * Math.min(1, Math.max(0, t)) + (r() - 0.5)) * 10) / 10;
  });
  SERIE_PEER.set(idx, s);
  return s;
}

/** Pendiente por mínimos cuadrados sobre los últimos `w` meses, en puntos/mes.
 *  Es la parte estructural del movimiento: no hace falta un modelo aparte. */
export function pendiente(s: number[], i: number, w = 6): number {
  const ys = s.slice(Math.max(0, i - w + 1), i + 1);
  const n = ys.length;
  if (n < 2) return 0;
  const mx = (n - 1) / 2, my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, den = 0;
  ys.forEach((y, k) => { num += (k - mx) * (y - my); den += (k - mx) ** 2; });
  return den === 0 ? 0 : num / den;
}

export function repartir(s: number[], tends: number[], i: number, mes: string): Reparto {
  const delta = i === 0 ? 0 : Math.round((s[i] - s[i - 1]) * 10) / 10;
  // Un mes plano no se reparte: no hay movimiento que atribuir.
  if (Math.abs(delta) < 0.15) return { mes, delta, pctTendencia: 0, pctBache: 0, structPts: 0, circPts: 0, drivers: [] };
  // La tendencia vigente no puede explicar más movimiento del que hubo.
  const explicado = Math.sign(delta) === Math.sign(tends[i])
    ? Math.min(Math.abs(tends[i]), Math.abs(delta)) : 0;
  const pctTendencia = Math.round((explicado / Math.abs(delta)) * 100);
  return { mes, delta, pctTendencia, pctBache: 100 - pctTendencia, structPts: 0, circPts: 0, drivers: [] };
}

/** La última inflexión, que es la que importa hoy. */
export function inflexionDe(s: number[], tends: number[], peer: number[], meses: string[] = MESES): Inflexion | undefined {
  const regimen = (i: number) =>
    [0, 1, 2].every((k) => (tends[i - k] ?? 0) < -0.4) ? "deterioro" as const
    : [0, 1, 2].every((k) => (tends[i - k] ?? 0) > 0.4) ? "mejora" as const
    : null;

  let ultima: Inflexion | undefined;
  for (let i = 3; i < s.length; i++) {
    const r = regimen(i);
    // Solo el ARRANQUE del régimen, y solo si aguanta tres meses: lo de menos
    // duración es ruido, y de eso ya habla la tira de abajo.
    if (!r || regimen(i - 1) === r) continue;
    if (![0, 1, 2].every((k) => regimen(i + k) === r)) continue;

    // El régimen no lo cierra un mes plano, solo el contrario. Si no, un deterioro
    // que pasa por un respiro se mide en 3 meses en vez de en los 9 que duró.
    let fin = i;
    while (fin + 1 < s.length) {
      const sig = regimen(fin + 1);
      if (sig !== null && sig !== r) break;
      fin++;
    }
    // Se detecta con retraso: cuando tres pendientes seguidas van en contra, la
    // caída ya lleva un par de meses rodando. Se mira atrás para ver dónde empezó.
    const ini = Math.max(0, i - 3);
    const swing = (xs: number[]) => {
      const antes = xs.slice(ini, i + 1), despues = xs.slice(i, fin + 1);
      return r === "deterioro"
        ? Math.min(...despues) - Math.max(...antes)
        : Math.max(...despues) - Math.min(...antes);
    };
    const dEmpresa = Math.round(swing(s) * 10) / 10;
    const dPeer = Math.round(swing(peer) * 10) / 10;
    // Un booleano aquí miente: entre "es la marea" y "es el barco" está el caso
    // real, que es un poco de cada. Se enseña la fracción y juzga quien mira.
    const misma = dPeer !== 0 && Math.sign(dPeer) === Math.sign(dEmpresa);
    const partePeer = !misma || dEmpresa === 0 ? 0
      : Math.min(1, Math.round((Math.abs(dPeer) / Math.abs(dEmpresa)) * 100) / 100);

    ultima = {
      mes: MESES[i], direccion: r, mesesRegimen: fin - i + 1,
      deltaEmpresa: dEmpresa, deltaPeer: dPeer, partePeer,
      frase: fraseInflexion(r, MESES[i], fin - i + 1, dEmpresa, dPeer, partePeer),
    };
  }
  return ultima;
}

const MESES_TXT = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const mesLargo = (m: string) => `${MESES_TXT[+m.split("-")[1] - 1]} de ${m.split("-")[0]}`;
const pts = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v))} pts`;

/** Tres lecturas según cuánto explique el cuartil, porque llevan a tres
 *  decisiones distintas: no hacer nada, mirar de cerca, o llamar. */
function fraseInflexion(
  r: "mejora" | "deterioro", mes: string, meses: number,
  dE: number, dP: number, parte: number,
): string {
  const verbo = r === "mejora" ? "Se anima" : "Empieza a torcerse";
  const ventana = `${pts(dE)} en ${meses} ${meses === 1 ? "mes" : "meses"}`;
  if (parte >= 0.5) {
    return `${verbo} en ${mesLargo(mes)}, pero su cuartil hizo lo mismo: ${ventana} la empresa, ${pts(dP)} el cuartil. Es la marea, no el barco.`;
  }
  if (parte >= 0.2) {
    return `${verbo} en ${mesLargo(mes)}: ${ventana}. Su cuartil se movió ${pts(dP)}, así que el entorno explica algo menos de la mitad. El resto es de la empresa.`;
  }
  const quieto = Math.abs(dP) < 0.5;
  return `${verbo} en ${mesLargo(mes)}: ${ventana} mientras su cuartil ${quieto ? "no se movía" : `hacía ${pts(dP)}`}. Esto no es el entorno, es la empresa.`;
}

export const EMPRESAS: Empresa[] = NOMBRES.map(([nombre, sector], i) => {
  const r = rng(1000 + i * 37);
  const ancla = ANCLAS[i];
  const perfil = PERFILES[i];
  let s = serie(perfil, r);
  // Las ancladas se reescalan para terminar en su score verificado
  if (ancla) {
    const fin = s[23], ini = Math.max(3, Math.min(97, ancla.score - ancla.d3));
    s = s.map((_, k) => {
      const t = k / 23;
      const v = ini + (ancla.score - ini) * Math.pow(t, perfil === "bache" ? 1 : 1.25)
        + (perfil === "bache" && k >= 12 && k <= 16 ? -11 : 0) + (r() - 0.5) * 2.2;
      return Math.max(1, Math.min(99, Math.round(v * 10) / 10));
    });
    s[23] = ancla.score;
  }
  const [gid, gnombre] = GRUPOS[i % GRUPOS.length];
  const mesesHistoria = !ancla && i % 7 === 3 ? 8 : !ancla && i % 11 === 5 ? 11 : 24;
  const dso = Math.round(32 + r() * 55);
  const dpo = Math.round(28 + r() * 45);
  const dias = Math.round(12 + r() * 70);
  const util = Math.round(18 + r() * 65);
  const hhi = Math.round((0.08 + r() * 0.5) * 100) / 100;
  const facturacion = Math.round((900 + r() * 14000)) * 1000;
  const score = s[23];
  const estado = ancla ? ancla.estado : estadoDe(s);

  // M_t ∈ [-1,1]: la inercia de los últimos 6 meses, acotada
  const momentum = Math.max(-1, Math.min(1, Math.round(((s[23] - s[17]) / 20) * 100) / 100));
  const nivelBase = Math.round(Math.max(0, Math.min(100, score - momentum * 6)) * 10) / 10;
  const clipping = Math.round((score >= 99 || score <= 1 ? Math.abs(momentum) * 2 : 0) * 100) / 100;

  const q = cuartil(facturacion);
  const peerS = medianaPeer(q.idx, q.control);
  const tends = s.map((_, k) => pendiente(s, k));

  const drivers = driversDe(score, dso, util, hhi, dias, momentum, r);
  const negativo = estado === "DETERIORO" || estado === "TORCIENDOSE";
  const mesesAnt = negativo ? (estado === "DETERIORO" ? 8 : 5) : 0;
  const causales = [...drivers].reverse().slice(0, 2);

  return {
    id: `COMP_${String(i + 1).padStart(4, "0")}`,
    nombre, grupo: gid, grupoNombre: gnombre, sector, moneda: "EUR",
    score, scorePrev: s[22], nivelBase, momentum, clipping, estado,
    confianza: mesesHistoria < 12 ? "BAJA" : r() > 0.35 ? "ALTA" : "MEDIA",
    mesesHistoria, facturacionAnual: facturacion,
    dso, dpo, diasCaja: dias, utilizacionLinea: util, hhiClientes: hhi,
    trayectoria: MESES.map((mes, k) => ({ mes, score: s[k], nivel: s[k] })),
    peer: { etiqueta: q.etiqueta, n: q.n },
    trayectoriaPeer: MESES.map((mes, k) => ({ mes, mediana: peerS[k] })),
    reparto: MESES.map((mes, k) => repartir(s, tends, k, mes)),
    inflexion: inflexionDe(s, tends, peerS),
    drivers,
    alerta: mesesAnt
      ? {
          severidad: (score < 25 ? "ALTA" : score < 60 ? "MEDIA" : "BAJA") as Severidad,
          mesDeteccion: MESES[23 - mesesAnt],
          mesesAnticipacion: mesesAnt,
          driversMovidos: causales.map((c) => c.etiqueta),
          codigosRazon: causales.map((c) => CODIGOS[c.feature]),
          texto: ancla?.caso ?? `${causales[0].etiqueta} se deterioró antes de que el score lo reflejara`,
        }
      : undefined,
  };
});

// Las empresas con menos de 12 meses no tienen score publicable
export const EMPRESAS_CON_SCORE = EMPRESAS.filter((e) => e.mesesHistoria >= 12);
export const EMPRESAS_SIN_DATOS  = EMPRESAS.filter((e) => e.mesesHistoria < 12);

/** La empresa que ha iniciado sesión. El producto es para ella, no para
 *  quien la mira desde fuera: nunca se enseñan otras empresas con nombre. */
export const MI_EMPRESA = "COMP_0773";
/**
 * Elegida del dataset por volumen e historia: 16 meses con estado real —el
 * máximo, porque el motor gasta 8 en arrancar—, confianza 100, ERP conectado,
 * 3.862 facturas y 12.773 movimientos. Y una trayectoria que se puede contar:
 * 71,5 → 22,0 en dos meses, recuperación a 73,1 y descenso hasta 56,4, con una
 * alerta ALTA de −38,9 puntos en octubre de 2025. Su grupo tiene 12 sociedades.
 */

export function empresa(id: string) {
  return EMPRESAS.find((e) => e.id === id);
}

export function grupo(gid: string) {
  const miembros = EMPRESAS.filter((e) => e.grupo === gid);
  const conScore = miembros.filter((m) => m.mesesHistoria >= 12);
  const media = conScore.reduce((a, b) => a + b.score, 0) / (conScore.length || 1);
  const peor = conScore.reduce((a, b) => (b.score < a.score ? b : a), conScore[0]);
  // 65% media + 35% peor filial material (hipótesis declarada en PRODUCTO.md)
  const consolidado = Math.round((0.65 * media + 0.35 * (peor?.score ?? media)) * 10) / 10;
  const penalizacion = Math.round((media - consolidado) * 10) / 10;
  return {
    id: gid,
    nombre: miembros[0]?.grupoNombre ?? gid,
    consolidado,
    penalizacion,
    media: Math.round(media * 10) / 10,
    peor,
    miembros,
    cobertura: Math.round((conScore.length / miembros.length) * 100),
  };
}

export const GRUPOS_LISTA = [...new Set(EMPRESAS.map((e) => e.grupo))].map(grupo);

// ── Palancas ──────────────────────────────────────────────────────────
export type Palanca = {
  id: string;
  nombre: string;
  descripcion: string;
  unidad: string;
  min: number; max: number; defecto: number;
  driver: string;
};

export const PALANCAS: Palanca[] = [
  { id: "reducir_dso",     nombre: "Reducir DSO",                descripcion: "Cobrar antes a los clientes que más tardan", unidad: "días antes", min: 1, max: 30, defecto: 12, driver: "cobros" },
  { id: "ampliar_dpo",     nombre: "Ampliar DPO",                descripcion: "Negociar más plazo con proveedores",         unidad: "días más",   min: 1, max: 30, defecto: 10, driver: "liquidez" },
  { id: "refinanciar",     nombre: "Refinanciar deuda",          descripcion: "Sustituir deuda cara por deuda a plazo",     unidad: "% del saldo",min: 5, max: 80, defecto: 30, driver: "deuda" },
  { id: "bajar_linea",     nombre: "Bajar utilización de línea", descripcion: "Reducir el dispuesto de la póliza",          unidad: "puntos",     min: 5, max: 50, defecto: 20, driver: "deuda" },
  { id: "reducir_concent", nombre: "Reducir concentración",      descripcion: "Repartir facturación entre más clientes",    unidad: "% del mayor",min: 5, max: 40, defecto: 15, driver: "concentracion" },
  { id: "sustituir_fact",  nombre: "Sustituir factoring",        descripcion: "Cambiar factoring por línea de crédito",     unidad: "% cedido",   min: 10,max: 100,defecto: 50, driver: "deuda" },
  { id: "recortar_opex",   nombre: "Recortar opex",              descripcion: "Reducir gasto operativo recurrente",         unidad: "%",          min: 1, max: 20, defecto: 6,  driver: "liquidez" },
  { id: "pronto_pago",     nombre: "Descuento pronto pago",      descripcion: "Ofrecer descuento por cobro anticipado",     unidad: "% descuento",min: 1, max: 5,  defecto: 2,  driver: "cobros" },
];

// Simulación contrafactual: recomputa, no extrapola.
export function simular(e: Empresa, palancaId: string, valor: number) {
  const p = PALANCAS.find((x) => x.id === palancaId)!;
  const facturacionDiaria = e.facturacionAnual / 365;
  let deltaScore = 0;
  let cajaLiberada = 0;

  switch (palancaId) {
    case "reducir_dso":
      cajaLiberada = valor * facturacionDiaria;
      deltaScore = valor * 0.42;
      break;
    case "ampliar_dpo":
      cajaLiberada = valor * facturacionDiaria * 0.55;
      deltaScore = valor * 0.21;
      break;
    case "refinanciar":
      cajaLiberada = (valor / 100) * e.facturacionAnual * 0.04;
      deltaScore = valor * 0.18;
      break;
    case "bajar_linea":
      cajaLiberada = 0;
      deltaScore = valor * 0.34;
      break;
    case "reducir_concent":
      cajaLiberada = 0;
      deltaScore = valor * 0.26;
      break;
    case "sustituir_fact":
      cajaLiberada = (valor / 100) * e.facturacionAnual * 0.02;
      deltaScore = valor * 0.09;
      break;
    case "recortar_opex":
      cajaLiberada = (valor / 100) * e.facturacionAnual * 0.18;
      deltaScore = valor * 0.55;
      break;
    default:
      cajaLiberada = facturacionDiaria * valor * 3;
      deltaScore = valor * 1.1;
  }

  const techo = 97 - e.score;
  deltaScore = Math.round(Math.min(deltaScore, techo) * 10) / 10;
  const scoreNuevo = Math.round((e.score + deltaScore) * 10) / 10;
  // Curva score → tipo implícito, calibrada sobre lo que pagan las empresas del dataset
  const bps = Math.round(-deltaScore * 5.8);
  const deudaViva = e.facturacionAnual * 0.22;
  const eurAnio = Math.round((-bps / 10000) * deudaViva);

  return {
    palanca: p,
    valor,
    scoreNuevo,
    deltaScore,
    cajaLiberada: Math.round(cajaLiberada),
    deltaBps: bps,
    eurAnio,
  };
}

// Recomendaciones: se simulan TODAS las palancas aplicables y se ordenan.
// Determinista y exhaustivo. Ningún modelo de lenguaje elige aquí.
export function recomendar(e: Empresa, n = 3) {
  const esfuerzo: Record<string, number> = {
    reducir_dso: 2, ampliar_dpo: 2, refinanciar: 4, bajar_linea: 3,
    reducir_concent: 5, sustituir_fact: 4, recortar_opex: 3, pronto_pago: 1,
  };
  const driverDebil = e.drivers[e.drivers.length - 1].feature;
  return PALANCAS
    .map((p) => {
      const sim = simular(e, p.id, p.defecto);
      const anclada = p.driver === driverDebil ? 1.35 : 1;
      return { ...sim, ratio: (sim.deltaScore / esfuerzo[p.id]) * anclada, anclada: p.driver === driverDebil };
    })
    .sort((a, b) => b.ratio - a.ratio)
    .slice(0, n);
}

export const ESTADO_LABEL: Record<Estado, string> = {
  MEJORANDO: "Mejorando",
  ESTABLE: "Estable",
  TORCIENDOSE: "Torciéndose",
  DETERIORO: "Deterioro",
  BACHE: "Bache",
  RECUPERACION: "Recuperación",
};
