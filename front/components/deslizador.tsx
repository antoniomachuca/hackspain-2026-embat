"use client";

/**
 * Deslizador con el tramo recorrido en morado.
 *
 * WebKit no tiene un selector para la parte rellena (Firefox sí, con
 * `::-moz-range-progress`), así que el porcentaje se pasa como variable CSS y
 * la pista se pinta con un degradado de dos tramos. Sin esto, o toda la barra
 * va del color de acento o ninguna.
 */
export function Deslizador({ min, max, paso = 1, valor, onCambio, id, etiqueta }:
  { min: number; max: number; paso?: number; valor: number; onCambio: (v: number) => void; id?: string; etiqueta?: string }) {
  const pct = ((valor - min) / Math.max(1e-9, max - min)) * 100;
  return (
    <input
      id={id} type="range" min={min} max={max} step={paso} value={valor}
      aria-label={etiqueta}
      onChange={(e) => onCambio(+e.target.value)}
      style={{ "--pct": `${pct}%` } as React.CSSProperties}
    />
  );
}
