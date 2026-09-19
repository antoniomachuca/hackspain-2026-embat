"use client";
import { useState } from "react";
import type { Driver } from "@/lib/data";
import { num } from "@/lib/format";

/** Un tono por factor, del morado de marca hacia el ámbar de lo que resta. */
const TONOS = ["#c357ec", "#b083e8", "#8f6fd6", "#7b32c0", "#e59f5e", "#e5775b"];
const APAGADO = "rgba(255,255,255,.14)";

/**
 * El score partido en seis arcos sobre un mismo anillo.
 *
 * La descomposición es aditiva y exacta, así que la vuelta entera ES el score:
 * cada arco ocupa exactamente lo que aporta. Lo que resta se dibuja con trama,
 * porque un arco más no puede decir "menos" por sí solo.
 */
export function Anillo({ drivers, score }: { drivers: Driver[]; score: number }) {
  // Se elige al pasar por encima. El clic deja fijado uno, para poder leer la
  // explicación sin mantener el ratón quieto sobre el arco.
  const [fijo, setFijo] = useState(0);
  const [sobre, setSobre] = useState<number | null>(null);
  const sel = sobre ?? fijo;

  const positivos = drivers.filter((d) => d.contribucion > 0);
  const suma = positivos.reduce((a, d) => a + d.contribucion, 0) || 1;

  // Anillo cerrado: la descomposición es exacta, así que la vuelta entera es
  // el score. Se pinta en segmentos finos para que se lea como una curva
  // continua en vez de como piezas pegadas.
  const tam = 290, grosor = 30, RESALTE = 5;
  // El radio descuenta el grosor MÁS el resalte del segmento activo: si no, al
  // engordar se sale del lienzo y el SVG lo recorta justo en el canto.
  const r = (tam - grosor - RESALTE * 2) / 2, c = tam / 2;
  const INICIO = -90, BARRIDO = 360;   // arranca arriba y da la vuelta

  const pos = (p: number) => {
    const ang = ((INICIO + p * BARRIDO) * Math.PI) / 180;
    return [c + r * Math.cos(ang), c + r * Math.sin(ang)] as const;
  };
  const arco = (d: number, h: number) => {
    const [x1, y1] = pos(d), [x2, y2] = pos(h);
    const grande = (h - d) * BARRIDO > 180 ? 1 : 0;
    return `M${x1.toFixed(2)},${y1.toFixed(2)} A${r},${r} 0 ${grande} 1 ${x2.toFixed(2)},${y2.toFixed(2)}`;
  };

  // Cada factor ocupa del recorrido lo que aporta al score.
  const tramos = drivers.map((d, i) => {
    const antes = drivers.slice(0, i).reduce((acc, x) => acc + Math.max(0, x.contribucion), 0);
    return { d, i, desde: antes / suma, hasta: (antes + Math.max(0, d.contribucion)) / suma };
  });

  const N = 220;
  const activo = drivers[sel];
  const neg = activo?.contribucion < 0;

  return (
    <div className="grid items-center gap-7 lg:grid-cols-[290px_1fr]">
      <div className="relative mx-auto" style={{ width: tam, height: tam }}>
        <svg width={tam} height={tam}>
          {/* Pista: un círculo completo, no un arco. Con un arco de 360° los
              dos extremos caen en el mismo punto y el trazado se descuadra. */}
          <circle cx={c} cy={c} r={r} fill="none" stroke="rgba(255,255,255,.07)" strokeWidth={grosor} />

          {Array.from({ length: N }, (_, k) => {
            const d = k / N, h = (k + 1.12) / N;
            const medio = (d + h) / 2;
            const t = tramos.find((x) => medio >= x.desde && medio < x.hasta) ?? tramos[tramos.length - 1];
            const on = t.i === sel;
            return (
              <path key={k} d={arco(d, Math.min(h, 1))} fill="none"
                onMouseEnter={() => setSobre(t.i)}
                onMouseLeave={() => setSobre(null)}
                onClick={() => setFijo(t.i)}
                style={{ cursor: "pointer" }}
                stroke={TONOS[t.i % TONOS.length]}
                strokeOpacity={on ? 1 : 0.45}
                strokeWidth={on ? grosor + RESALTE : grosor}
                strokeLinecap="butt" />
            );
          })}
        </svg>

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="tnum text-[42px] font-semibold leading-none">{num(score)}</span>
          <span className="mt-1.5 text-[11.5px] text-[var(--color-ink-3)]">score</span>
        </div>
      </div>

      <div>
        {/* Leyenda: cada factor con su tono, su aporte y su barra de reparto */}
        <div className="flex flex-col">
          {drivers.map((d, i) => {
            const on = i === sel;
            const resta = d.contribucion < 0;
            const cero = Math.abs(d.contribucion) < 0.005;
            return (
              <button key={d.feature}
                onMouseEnter={() => setSobre(i)}
                onMouseLeave={() => setSobre(null)}
                onFocus={() => setSobre(i)}
                onBlur={() => setSobre(null)}
                onClick={() => setFijo(i)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors ${on ? "bg-[rgba(255,255,255,.07)]" : "hover:bg-[rgba(255,255,255,.035)]"}`}>
                <span className="h-2.5 w-2.5 flex-none rounded-[3px]"
                  style={{ background: cero ? APAGADO : resta ? "#e5775b" : TONOS[i % TONOS.length] }} />
                <span className={`flex-1 text-[13px] ${on ? "font-semibold" : ""}`}>{d.etiqueta}</span>
                <span className="tnum w-[92px] flex-none truncate text-right text-[11.5px] text-[var(--color-ink-3)]">
                  {cero ? "sin efecto" : d.valor}
                </span>
                <span className="tnum w-[54px] flex-none text-right text-[13px] font-semibold"
                  style={{ color: cero ? "var(--color-ink-4)" : resta ? "#e5775b" : "var(--color-ink)" }}>
                  {resta ? "−" : "+"}{num(Math.abs(d.contribucion), 1)}
                </span>
              </button>
            );
          })}
        </div>

        {activo && (
          <div className="mt-4 border-t border-[var(--color-line)] pt-4">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
              <h3 className="text-[14px] font-semibold tracking-tight">{activo.etiqueta}</h3>
              {activo.codigo && (
                <span className="rounded bg-[rgba(255,255,255,.08)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-ink-3)]">
                  {activo.codigo}
                </span>
              )}
              <span className="tnum flex items-center gap-2 text-[11.5px] text-[var(--color-ink-3)]">
                <span className="h-1.5 w-16 overflow-hidden rounded-full bg-[rgba(255,255,255,.1)]">
                  <span className="block h-full rounded-full"
                    style={{ width: `${activo.p_peer}%`, background: activo.p_peer >= 50 ? "#b083e8" : "#e59f5e" }} />
                </span>
                percentil {activo.p_peer}
              </span>
            </div>

            {activo.descripcion && (
              <p className="mt-2.5 text-[12.5px] leading-relaxed text-[var(--color-ink-2)]">{activo.descripcion}</p>
            )}
            {activo.diagnostico && (
              <p className="mt-2.5 rounded-lg px-3.5 py-2.5 text-[12.5px] leading-relaxed"
                style={{ background: `color-mix(in srgb, ${neg ? "#e5775b" : "#b083e8"} 13%, transparent)` }}>
                {activo.diagnostico}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
