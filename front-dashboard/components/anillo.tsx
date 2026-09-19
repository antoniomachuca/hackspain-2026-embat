import { banda, num } from "@/lib/format";

/**
 * Anillo de score. Arco de 270° sobre pista tenue, con el degradado del eje de
 * riesgo (cálido → morado) y un punto en la posición exacta. Sin resplandores:
 * el dato se lee por la forma y el color, no por el efecto.
 * Se usa junto a la trayectoria, nunca en su lugar: el anillo dice dónde está,
 * la línea dice hacia dónde va.
 */
export function Anillo({
  score, tam = 162, grosor = 9, etiqueta = true, delta,
}: { score: number; tam?: number; grosor?: number; etiqueta?: boolean; delta?: number }) {
  const b = banda(score);
  const r = (tam - grosor) / 2;
  const cx = tam / 2;
  const barrido = 270;                       // hueco de 90° abajo
  const circ = 2 * Math.PI * r;
  const largoPista = (circ * barrido) / 360;
  const largoArco = largoPista * (score / 100);
  const id = `anillo-${Math.round(score * 10)}`;

  // Ángulo de la aguja: empieza en 135° (abajo-izquierda) y avanza 270°
  const ang = (135 + (score / 100) * barrido) * (Math.PI / 180);
  const px = cx + r * Math.cos(ang);
  const py = cx + r * Math.sin(ang);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: tam, height: tam }}>
      <svg width={tam} height={tam} className="-rotate-[0deg]" style={{ transform: "rotate(135deg)" }}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#e5775b" />
            <stop offset="26%"  stopColor="#e59f5e" />
            <stop offset="48%"  stopColor="#dfb631" />
            <stop offset="74%"  stopColor="#a154e9" />
            <stop offset="100%" stopColor="#c357ec" />
          </linearGradient>
        </defs>
        {/* Pista */}
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="rgba(255,255,255,.08)"
          strokeWidth={grosor} strokeLinecap="round"
          strokeDasharray={`${largoPista} ${circ}`} />
        {/* Arco */}
        <circle cx={cx} cy={cx} r={r} fill="none" stroke={`url(#${id})`}
          strokeWidth={grosor} strokeLinecap="round"
          strokeDasharray={`${largoArco} ${circ}`} />
      </svg>

      {/* Aguja en la punta del arco */}
      <span className="absolute h-2 w-2 rounded-full bg-white/85"
        style={{ left: px - 4, top: py - 4 }} />

      <div className="absolute flex flex-col items-center">
        <span className="tnum text-[38px] font-semibold leading-none" style={{ color: b.color }}>
          {num(score)}
        </span>
        {etiqueta && (
          <span className="mt-1 text-[11px] font-medium tracking-wide" style={{ color: b.color }}>
            {b.label}
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
