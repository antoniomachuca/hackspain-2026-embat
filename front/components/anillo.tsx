import { banda, num } from "@/lib/format";

/** Estados analíticos oficiales del motor y el bot de Telegram */
export const ESTADOS_TELEGRAM: Record<string, { label: string; color: string }> = {
  DETERIORO: { label: "Deterioro", color: "#e5775b" },       // Rojo (alerta crítica)
  TORCIENDOSE: { label: "Torciéndose", color: "#e59f5e" },   // Naranja (aviso preventivo)
  BACHE: { label: "Bache", color: "#dfb631" },               // Ámbar (bache transitorio de caja)
  ESTABLE: { label: "Estable", color: "#9fe3b4" },           // Verde suave (solvente/estable)
  MEJORANDO: { label: "Mejorando", color: "#80efa2" },       // Verde brillante (mejora operativa)
  RECUPERACION: { label: "Recuperación", color: "#80efa2" }, // Verde brillante (recuperación de caja)
  EVALUACION_PENDIENTE: { label: "En evaluación", color: "#afafbb" },
};

/** Paradas del eje del score, de peor a mejor. */
const EJE: Array<[number, string]> = [
  [0.0, "#e5775b"],   // rojo
  [0.34, "#e59f5e"],  // naranja
  [0.62, "#dfb631"],  // ámbar
  [1.0, "#80efa2"],   // verde
];

/** Color en una posición 0..1 del eje, interpolando entre paradas. */
function colorEn(t: number) {
  const p = Math.max(0, Math.min(1, t));
  let i = 0;
  while (i < EJE.length - 2 && p > EJE[i + 1][0]) i++;
  const [t0, c0] = EJE[i], [t1, c1] = EJE[i + 1];
  const k = (p - t0) / (t1 - t0 || 1);
  const a = hex(c0), b = hex(c1);
  const m = (j: number) => Math.round(a[j] + (b[j] - a[j]) * k);
  return `rgb(${m(0)},${m(1)},${m(2)})`;
}
const hex = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));

/**
 * Anillo de score. Arco de 270° con el hueco abajo.
 *
 * El degradado se pinta por segmentos a lo largo del arco, no con un
 * linearGradient sobre la caja: un degradado lineal sobre un elemento rotado
 * no sigue la curva, y el rojo acababa donde no tocaba.
 */
export function Anillo({
  score, tam = 162, grosor = 9, etiqueta = true, delta, estado,
}: { score: number; tam?: number; grosor?: number; etiqueta?: boolean; delta?: number; estado?: string }) {
  const b = banda(score);
  const st = estado ? ESTADOS_TELEGRAM[estado.toUpperCase().trim()] : null;
  const textoEtiqueta = st ? st.label : b.label;
  const colorEtiqueta = st ? st.color : b.color;
  const r = (tam - grosor) / 2;
  const cx = tam / 2;
  const INICIO = 135, BARRIDO = 270;          // empieza abajo-izquierda
  const frac = Math.max(0, Math.min(1, score / 100));

  const pos = (p: number) => {
    const a = ((INICIO + p * BARRIDO) * Math.PI) / 180;
    return [cx + r * Math.cos(a), cx + r * Math.sin(a)] as const;
  };
  const arco = (d: number, h: number) => {
    const [x1, y1] = pos(d), [x2, y2] = pos(h);
    const grande = (h - d) * BARRIDO > 180 ? 1 : 0;
    return `M${x1.toFixed(2)},${y1.toFixed(2)} A${r},${r} 0 ${grande} 1 ${x2.toFixed(2)},${y2.toFixed(2)}`;
  };

  // 48 segmentos: suficientes para que no se vean los cortes
  const N = 48;
  const hasta = Math.max(1, Math.round(N * frac));
  const [px, py] = pos(frac);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: tam, height: tam }}>
      <svg width={tam} height={tam}>
        {/* Pista */}
        <path d={arco(0, 1)} fill="none" stroke="rgba(255,255,255,.08)"
          strokeWidth={grosor} strokeLinecap="round" />
        {/* Arco, segmento a segmento: el color es el del valor en ese punto */}
        {Array.from({ length: hasta }, (_, i) => {
          const d = i / N, h = Math.min((i + 1.06) / N, frac);
          if (h <= d) return null;
          return (
            <path key={i} d={arco(d, h)} fill="none" stroke={colorEn((d + h) / 2)}
              strokeWidth={grosor} strokeLinecap={i === 0 || h >= frac ? "round" : "butt"} />
          );
        })}
      </svg>

      <span className="absolute h-2 w-2 rounded-full bg-white/85"
        style={{ left: px - 4, top: py - 4 }} />

      <div className="absolute flex flex-col items-center">
        <span className="tnum text-[38px] font-semibold leading-none" style={{ color: colorEtiqueta }}>
          {num(score)}
        </span>
        {etiqueta && (
          <span className="mt-1 text-[11px] font-medium tracking-wide" style={{ color: colorEtiqueta }}>
            {textoEtiqueta}
          </span>
        )}
        {delta !== undefined && (
          <span className="tnum mt-0.5 text-[11.5px] text-[var(--color-ink-3)]">
            {delta > 0 ? "↑ +" : delta < 0 ? "↓ −" : "→ "}{num(Math.abs(delta))} vs. mes ant.
          </span>
        )}
      </div>
    </div>
  );
}
