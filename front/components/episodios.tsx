"use client";
import { useState } from "react";
import type { Episodio, Punto } from "@/lib/data";
import { num } from "@/lib/format";
import { Trayectoria } from "./charts";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const mesAno = (iso: string) => {
  const [a, m] = iso.split("-");
  return `${MESES[+m - 1]} ${a}`;
};

const ESTADOS_MOTOR: Record<string, string> = {
  MEJORANDO: "mejorando", ESTABLE: "estable", TORCIENDOSE: "torciéndose",
  DETERIORO: "deterioro", BACHE: "bache", RECUPERACION: "recuperación",
  EVALUACION_PENDIENTE: "evaluación pendiente",
};

function fraseConfirmacion(ep: Episodio): string {
  const n = ep.meses_anticipacion;
  switch (ep.estado_confirmacion) {
    case "confirmado":
      if (n != null && n > 0) return `detectado ${n} ${n === 1 ? "mes" : "meses"} antes del cambio material`;
      if (n === 0) return "detectado el mismo mes del cambio material";
      return `el cambio material se había producido ${Math.abs(n ?? 0)} ${Math.abs(n ?? 0) === 1 ? "mes" : "meses"} antes: detección tardía`;
    case "pendiente":
      return "cambio material pendiente de confirmación";
    case "no_confirmado":
      return "no se confirmó cambio material";
  }
}

const COLOR = { deterioro: "var(--color-warm)", mejora: "var(--color-success)" } as const;

export function EpisodiosPanel({ episodios, destacado, trayectoria }: {
  episodios: Episodio[];
  destacado: number | null;
  trayectoria: Punto[];
}) {
  const [sel, setSel] = useState(destacado ?? episodios.length - 1);
  const [abierto, setAbierto] = useState(false);
  if (!episodios.length) return null;
  const ep = episodios[Math.min(sel, episodios.length - 1)];
  const color = COLOR[ep.direccion];

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[13.5px] font-medium" style={{ color }}>
            Detección en {mesAno(ep.deteccion)} · {fraseConfirmacion(ep)}
          </p>
          <p className="mt-1 text-[12px] leading-relaxed text-[var(--color-ink-3)]">
            Episodio de {ep.direccion} {ep.estado === "activo" ? "activo" : `cerrado en ${mesAno(ep.cierre ?? ep.deteccion)}`}
            {" · "}estado al detectar: {ESTADOS_MOTOR[ep.estado_deteccion] ?? ep.estado_deteccion}.
            {ep.senales.length > 0 && ` Señales: ${ep.senales.map((s) => s.senal).join(", ")}.`}
          </p>
        </div>
        {episodios.length > 1 && (
          <button
            onClick={() => setAbierto((v) => !v)}
            className="rounded-md border border-[var(--color-line-2)] px-3 py-1.5 text-[12px] text-[var(--color-ink-2)] hover:bg-[var(--color-surface-3)]"
          >
            {abierto ? "Ocultar histórico" : `Ver histórico (${episodios.length})`}
          </button>
        )}
      </div>

      <div className="mt-4">
        <Trayectoria
          datos={trayectoria}
          deteccion={{
            mes: ep.deteccion.slice(0, 7),
            direccion: ep.direccion,
            texto: ep.texto,
            senales: ep.senales,
          }}
          altura={210}
        />
      </div>

      {abierto && (
        <div className="mt-4 space-y-1 border-t border-[var(--color-line)] pt-3">
          {episodios.map((x, i) => (
            <button
              key={i}
              onClick={() => setSel(i)}
              className={`fila flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-[12px] ${
                i === sel ? "bg-[var(--color-surface-3)]" : ""
              }`}
            >
              <span style={{ color: COLOR[x.direccion] }} className="font-medium capitalize">
                {x.direccion}
              </span>
              <span className="text-[var(--color-ink-2)]">
                detectado {mesAno(x.deteccion)}
                {x.cierre ? ` · cerrado ${mesAno(x.cierre)}` : " · activo"}
              </span>
              <span className="tnum text-[var(--color-ink-4)]">
                score {num(x.score_deteccion)} · {x.estado_confirmacion.replace("_", " ")}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
