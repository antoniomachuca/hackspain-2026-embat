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

/** Eje de riesgo continuo cálido → frío. Tokens inversos oficiales de Embat. */
export function banda(score: number) {
  if (score < 25) return { label: "Crítico",  color: "var(--color-risk-1)", bg: "rgba(229,119,91,.16)" };
  if (score < 45) return { label: "Frágil",   color: "var(--color-risk-2)", bg: "rgba(229,159,94,.16)" };
  if (score < 60) return { label: "Atención", color: "var(--color-risk-3)", bg: "rgba(223,182,49,.16)" };
  if (score < 80) return { label: "Estable",  color: "var(--color-risk-4)", bg: "rgba(161,84,233,.20)" };
  return            { label: "Sólido",   color: "var(--color-risk-5)", bg: "rgba(195,87,236,.20)" };
}
