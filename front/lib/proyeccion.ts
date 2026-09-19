/**
 * Proyección de una trayectoria de score.
 *
 * Puente browniano entre hoy y el destino: `forma` curva el camino y el ruido
 * se escala con la volatilidad observada, anulándose en los extremos para
 * aterrizar exactamente en el objetivo. Determinista: misma semilla, mismo
 * dibujo, en cualquier máquina y en cualquier recarga.
 */
export function senda(desde: number, hasta: number, n: number, forma: number, vol: number, semilla: number) {
  let s = semilla >>> 0;
  const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296 - 0.5);
  const paso: number[] = []; let acc = 0;
  for (let i = 0; i <= n; i++) { acc += r() * vol * 1.1; paso.push(acc); }
  const deriva = paso[n];
  const out: number[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const base = desde + (hasta - desde) * Math.pow(t, forma);
    const ruido = (paso[i] - deriva * t) * Math.sin(Math.PI * t);
    out.push(acota(base + ruido));
  }
  out[0] = desde; out[n] = hasta;
  return out;
}

export const acota = (v: number) => Math.max(1, Math.min(99, Math.round(v * 10) / 10));

/** Volatilidad mensual observada, acotada para que el ruido no coma la señal. */
export function volatilidad(serie: number[]) {
  const saltos = serie.slice(1).map((v, i) => v - serie[i]);
  if (!saltos.length) return 1;
  const m = saltos.reduce((a, b) => a + b, 0) / saltos.length;
  return Math.min(4.5, Math.sqrt(saltos.reduce((a, b) => a + (b - m) ** 2, 0) / saltos.length));
}
