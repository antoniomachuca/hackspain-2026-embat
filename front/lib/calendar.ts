/**
 * Tres relojes del dataset. El score llega con `as_of` = primer día *después*
 * del mes de transacciones. El último ciclo completo es agosto de 2026.
 * Septiembre es un día suelto: no se pinta como mes cerrado ni entra en medias.
 */
export const DATA_CUTOFF = "2026-09-01";
export const LAST_CLOSED_MONTH = "2026-08-01";
export const PARTIAL_MONTH = "2026-09-01";
export const PARTIAL_MONTH_LABEL = "Foto de apertura 1-sep (1 día)";

/** YYYY-MM del mes de actividad que cierra un corte `as_of`. */
export function mesCerradoDeAsOf(asOf: string | null | undefined): string {
  if (!asOf) return LAST_CLOSED_MONTH.slice(0, 7);
  const [year, month] = asOf.slice(0, 7).split("-").map(Number);
  if (!year || !month) return LAST_CLOSED_MONTH.slice(0, 7);
  const closed = new Date(Date.UTC(year, month - 2, 1));
  return closed.toISOString().slice(0, 7);
}

/** Etiqueta de eje: prefiere `closed_month` del API; si no, deriva del as_of. */
export function mesDePunto(punto: {
  closed_month?: string | null;
  as_of?: string | null;
  mes?: string | null;
}): string {
  if (punto.closed_month) return punto.closed_month.slice(0, 7);
  if (punto.as_of) return mesCerradoDeAsOf(punto.as_of);
  if (punto.mes) return mesCerradoDeAsOf(punto.mes);
  return LAST_CLOSED_MONTH.slice(0, 7);
}
