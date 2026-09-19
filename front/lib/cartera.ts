/**
 * Segmentación de la cartera para Embat. Es una regla, no un modelo, y es la
 * misma que aplica el backend en routes/stats.py (SEGMENT_SQL): si se toca una,
 * se toca la otra.
 */
export type Segmento = "APOSTAR" | "VIGILAR" | "ACOMPANAR";

export const SEGMENTOS: Record<Segmento, { label: string; accion: string; color: string; bg: string }> = {
  APOSTAR:   { label: "Apostar",   accion: "Sana y creciendo: candidata a línea de crédito.",
               color: "#80efa2", bg: "rgba(128,239,162,.14)" },
  VIGILAR:   { label: "Vigilar",   accion: "Empieza a torcerse: ofrecer ayuda antes de perderla.",
               color: "#e5775b", bg: "rgba(229,119,91,.14)" },
  ACOMPANAR: { label: "Acompañar", accion: "Bache puntual: seguir de cerca, sin actuar aún.",
               color: "#dfb631", bg: "rgba(223,182,49,.14)" },
};

export function segmentoDe(e: { score: number; estado: string; delta3m?: number; elegible?: boolean }): Segmento | null {
  const st = e.estado.toUpperCase();
  const elegible = e.elegible ?? true;
  if (elegible && e.score >= 60 && (st === "MEJORANDO" || st === "RECUPERACION" || (e.delta3m ?? 0) >= 10)) return "APOSTAR";
  if (st === "TORCIENDOSE" || st === "DETERIORO") return "VIGILAR";
  if (st === "BACHE") return "ACOMPANAR";
  return null;
}
