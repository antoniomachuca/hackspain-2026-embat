import { PALANCAS, simular, type Empresa, type Palanca } from "./data";

export type Ajuste = { id: string; valor: number };

/**
 * Esfuerzo relativo de una palanca, de 0 a 1.
 *
 * No todas cuestan lo mismo de aplicar: apretar el cobro a unos clientes es
 * una llamada, refinanciar es un comité. Y dentro de una palanca el esfuerzo
 * crece más deprisa que el parámetro — pedir 30 días de adelanto no es el
 * doble de difícil que pedir 15, es mucho más.
 */
const COSTE_BASE: Record<string, number> = {
  reducir_dso: 2, ampliar_dpo: 2.4, pronto_pago: 1.4, recortar_opex: 3.4,
  refinanciar: 4.2, bajar_linea: 3, reducir_concent: 5.2, sustituir_fact: 4,
};

export function esfuerzo(p: Palanca, valor: number) {
  const t = (valor - p.min) / Math.max(1e-9, p.max - p.min);
  return Math.pow(Math.max(0, Math.min(1, t)), 1.6) * (COSTE_BASE[p.id] ?? 3);
}

/**
 * Combina varios ajustes en un solo resultado.
 *
 * Los deltas NO se suman: todas las palancas tiran del mismo margen de mejora,
 * así que la segunda rinde menos que la primera. Se compone de forma
 * multiplicativa sobre el techo disponible — es la forma honesta de decir que
 * hacer cinco cosas a la vez no da cinco veces el resultado.
 *
 * La caja liberada y el ahorro sí se suman: son euros distintos.
 */
export function combinar(e: Empresa, ajustes: Ajuste[]) {
  const partes = ajustes
    .map((a) => {
      const p = PALANCAS.find((x) => x.id === a.id);
      if (!p) return null;
      // `simular` ya devuelve palanca y valor; se sobreescriben a propósito
      // con los del ajuste para que el desglose hable del que se está viendo.
      const s = simular(e, a.id, a.valor);
      return { ...s, palanca: p, valor: a.valor, esfuerzo: esfuerzo(p, a.valor) };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null);

  const techo = Math.max(1, 97 - e.score);
  const restante = partes.reduce((acc, p) => acc * (1 - Math.min(0.95, p.deltaScore / techo)), 1);
  const deltaTotal = Math.round(techo * (1 - restante) * 10) / 10;

  // Cada palanca se lleva su parte proporcional del total ya saturado, para
  // que el desglose de la pantalla sume exactamente lo que dice el titular.
  const bruto = partes.reduce((a, p) => a + p.deltaScore, 0) || 1;
  const conReparto = partes.map((p) => ({
    ...p,
    aporte: Math.round((p.deltaScore / bruto) * deltaTotal * 10) / 10,
  }));

  return {
    partes: conReparto,
    deltaTotal,
    perdidaPorSolape: Math.round((bruto - deltaTotal) * 10) / 10,
    scoreNuevo: Math.round(Math.min(97, e.score + deltaTotal) * 10) / 10,
    caja: conReparto.reduce((a, p) => a + p.cajaLiberada, 0),
    eurAnio: conReparto.reduce((a, p) => a + p.eurAnio, 0),
    esfuerzoTotal: Math.round(conReparto.reduce((a, p) => a + p.esfuerzo, 0) * 10) / 10,
  };
}

/** Palancas que no pueden aplicarse a la vez. Viene del catálogo del motor. */
export const EXCLUSIONES: Record<string, string[]> = {
  reducir_dso: ["pronto_pago"],
  pronto_pago: ["reducir_dso"],
  bajar_linea: ["sustituir_fact"],
  sustituir_fact: ["bajar_linea"],
};

export function choca(id: string, activas: string[]) {
  return (EXCLUSIONES[id] ?? []).find((x) => activas.includes(x));
}
