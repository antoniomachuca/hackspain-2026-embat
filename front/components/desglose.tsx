"use client";
import { useState } from "react";
import type { Driver } from "@/lib/data";
import { num } from "@/lib/format";

const POS = "#b083e8";
const NEG = "#e59f5e";

/**
 * De dónde sale el score, factor a factor.
 *
 * Sustituye al gráfico de barras: con seis valores, una de ellos a cero, el
 * lienzo quedaba medio vacío y además no enseñaba lo que el motor ya calcula
 * —el valor en unidades de negocio y el diagnóstico de cada factor—, que es
 * justo lo que hace entendible el número a quien decide.
 */
export function Desglose({ drivers, score }: { drivers: Driver[]; score: number }) {
  const [abierto, setAbierto] = useState<string | null>(null);
  const max = Math.max(...drivers.map((d) => Math.abs(d.contribucion)), 1);

  return (
    <div>
      <div className="flex flex-col">
        {drivers.map((d) => {
          const neg = d.contribucion < 0;
          const cero = Math.abs(d.contribucion) < 0.005;
          const ancho = (Math.abs(d.contribucion) / max) * 100;
          const detalle = d.diagnostico || d.descripcion;
          const on = abierto === d.feature;

          return (
            <div key={d.feature} className="border-b border-[var(--color-line)] last:border-0">
              <button
                onClick={() => setAbierto(on ? null : d.feature)}
                className="group flex w-full items-center gap-4 py-3 text-left"
                aria-expanded={on}
              >
                <span className="w-[104px] flex-none text-[12.5px] font-medium">{d.etiqueta}</span>

                <span className="tnum w-[128px] flex-none truncate text-[11.5px] text-[var(--color-ink-3)]">
                  {cero ? "sin efecto" : d.valor}
                </span>

                <span className="tnum w-[52px] flex-none text-right text-[13px] font-semibold"
                  style={{ color: cero ? "var(--color-ink-4)" : neg ? NEG : "var(--color-ink)" }}>
                  {neg ? "−" : ""}{num(Math.abs(d.contribucion), 2)}
                </span>

                {detalle && (
                  <span className="w-3 flex-none text-[10px] text-[var(--color-ink-4)] transition-transform group-hover:text-[var(--color-ink-3)]">
                    {on ? "▴" : "▾"}
                  </span>
                )}

                {/* La barra va al final y sin pista: cada una termina donde le
                    toca, así la longitud se compara de un vistazo en lugar de
                    quedar todas alineadas contra el mismo borde. */}
                <span className="min-w-0 flex-1">
                  <span className="block h-[18px] rounded-[5px] transition-[width] duration-300"
                    style={{
                      width: `${Math.max(cero ? 0 : 3, ancho)}%`,
                      background: cero
                        ? "rgba(255,255,255,.1)"
                        : neg
                        ? `linear-gradient(90deg, ${NEG}88, ${NEG})`
                        : `linear-gradient(90deg, ${POS}77, ${POS})`,
                    }} />
                </span>
              </button>

              {on && detalle && (
                <p className="pb-3 pl-[104px] pr-4 text-[11.5px] leading-relaxed text-[var(--color-ink-2)]">
                  {detalle}
                  {d.rango && <span className="text-[var(--color-ink-4)]"> · rango {d.rango}</span>}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-3 flex items-center gap-4 border-t border-[var(--color-line-2)] pt-3">
        <span className="w-[104px] flex-none text-[12.5px] font-semibold">Score</span>
        <span className="w-[128px] flex-none text-[11px] text-[var(--color-ink-4)]">suma exacta</span>
        <span className="tnum w-[52px] flex-none text-right text-[15px] font-semibold"
          style={{ color: "var(--color-purple)" }}>
          {num(score)}
        </span>
        <span className="w-3 flex-none" />
        <span className="min-w-0 flex-1 text-[11px] text-[var(--color-ink-4)]">
          Sin SHAP ni aproximaciones
        </span>
      </div>
    </div>
  );
}
