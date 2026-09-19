import { mesCerradoDeAsOf } from "./calendar";

export const eur = (n: number, compacto = false) =>
  new Intl.NumberFormat("es-ES", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
    notation: compacto ? "compact" : "standard",
  }).format(n);

export const num = (n: number, d = 1) =>
  new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d }).format(n);

export const mesCorto = (iso: string) => {
  const [a, m] = iso.split("-");
  return `${["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][+m - 1]} ${a.slice(2)}`;
};

/** Mes de actividad de un corte `as_of` (2026-09-01 → ago 26). */
export const mesCortoCerrado = (asOf: string) => mesCorto(mesCerradoDeAsOf(asOf));

/** Eje del score: rojo → morado → ámbar → verde. Tokens de Embat.
 *  El color nunca va solo: siempre lo acompaña la etiqueta o una flecha. */
export function banda(score: number) {
  if (score < 25) return { label: "Crítico",  color: "#e5775b", bg: "rgba(229,119,91,.18)" };
  if (score < 45) return { label: "Frágil",   color: "#e59f5e", bg: "rgba(229,159,94,.18)" };
  if (score < 60) return { label: "Atención", color: "#dfb631", bg: "rgba(223,182,49,.18)" };
  if (score < 80) return { label: "Estable",  color: "#9fe3b4", bg: "rgba(159,227,180,.18)" };
  return            { label: "Sólido",   color: "#80efa2", bg: "rgba(128,239,162,.20)" };
}

/* Alias que usa la página de previsión (front/app/prevision). */
export const fmtNum = num;
export const fmtMes = mesCorto;
