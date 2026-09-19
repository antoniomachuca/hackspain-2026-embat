"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import type { GrupoCartera, MotivoGrupo } from "@/lib/motor";
import { apiGrafo, type ApiGrafo } from "@/lib/api";
import { eur, num } from "@/lib/format";
import { TarjetaGrupo } from "@/components/cartera-grupos";
import { Grafo } from "@/components/grafo";
import { Modal } from "@/components/modal";

export type Motivo = { clave: MotivoGrupo; label: string; accion: string; color: string; bg: string };

const VISIBLES = 12;   // cuatro filas de tres, estiradas al alto que sobre

/** Los datos del grupo y su mapa de flujos, dentro de la vista ampliada. */
function Detalle({ g }: { g: GrupoCartera }) {
  const [cache, setCache] = useState<{ id: string; grafo: ApiGrafo | null } | null>(null);

  useEffect(() => {
    let vivo = true;
    apiGrafo(g.id, 1).then((r) => { if (vivo) setCache({ id: g.id, grafo: r }); });
    return () => { vivo = false; };
  }, [g.id]);

  const cargando = cache?.id !== g.id;
  const grafo = cargando ? null : cache!.grafo;

  const datos: [string, string][] = [
    ["Consolidado", num(g.consolidado)],
    ["Media", num(g.media)],
    ["Peor filial", `${num(g.peor.score)} · ${g.peor.id.replace("COMP_", "")}`],
    ["Mejor filial", `${num(g.mejor.score)} · ${g.mejor.id.replace("COMP_", "")}`],
    ["Sociedades", `${g.filiales}`],
    ["En riesgo", `${g.enRiesgo}`],
    ["Cobertura", `${num(g.cobertura, 0)} %`],
    ["Flujo interno", g.flujoInterno > 0 ? eur(g.flujoInterno, true) : "—"],
  ];

  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="text-[15px] font-semibold tracking-tight">{g.nombre}</h3>
        <Link href={`/grupo/${g.id}`} className="text-[11.5px] text-[var(--color-purple)] hover:underline">
          Abrir la ficha del grupo →
        </Link>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        {datos.map(([k, v]) => (
          <div key={k}>
            <p className="text-[10px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
            <p className="tnum mt-1 text-[13.5px] font-medium">{v}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 border-t border-[var(--color-line)] pt-3">
        <p className="text-[11.5px] text-[var(--color-ink-4)]">
          Flujos entre sus sociedades · la peor va marcada
        </p>
        <div className="mt-2">
          {cargando ? (
            <div className="flex h-[280px] items-center justify-center text-[12px] text-[var(--color-ink-4)]">
              Calculando el mapa…
            </div>
          ) : grafo && grafo.edges.length > 0 ? (
            <Grafo nodos={grafo.nodes} aristas={grafo.edges} destacar={g.peor.id} alto={280} />
          ) : (
            <div className="flex h-[120px] items-center justify-center text-[12px] text-[var(--color-ink-4)]">
              Sin flujos detectados entre sus sociedades
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Qué hacer con la cartera de grupos.
 *
 * Los motivos son pestañas y fuera solo se ven tres casos: los tres primeros
 * de una lista ordenada por gravedad ya dicen si hay que preocuparse. El resto
 * vive en la vista ampliada, donde cada grupo enseña sus números y el mapa de
 * flujos entre sus sociedades.
 */
export function Bandeja({ motivos, grupos }: { motivos: Motivo[]; grupos: GrupoCartera[] }) {
  const conCasos = motivos.filter((m) => grupos.some((g) => g.motivo === m.clave));
  const [sel, setSel] = useState(conCasos[0]?.clave ?? motivos[0].clave);
  const [abierto, setAbierto] = useState(false);
  const [elegido, setElegido] = useState<string | null>(null);
  if (!conCasos.length) return null;

  const activo = conCasos.find((m) => m.clave === sel) ?? conCasos[0];
  const lista = grupos
    .filter((g) => g.motivo === activo.clave)
    .sort((a, b) => b.gravedad - a.gravedad);
  const detalle = lista.find((g) => g.id === elegido) ?? lista[0];

  const abrir = (id?: string) => { setElegido(id ?? lista[0].id); setAbierto(true); };

  return (
    <div className="panel flex min-h-0 flex-1 flex-col px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight">Dónde actuar</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">{activo.accion}</p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {conCasos.map((m) => {
            const n = grupos.filter((g) => g.motivo === m.clave).length;
            const on = m.clave === activo.clave;
            return (
              <button key={m.clave} onClick={() => { setSel(m.clave); setElegido(null); }}
                className={`pildora ${on ? "on" : ""} flex items-center gap-2`}
                style={{ padding: "6px 13px", fontSize: 12 }}>
                <span className="h-2 w-2 rounded-full" style={{ background: m.color, opacity: on ? 1 : 0.55 }} />
                {m.label}
                <span className="tnum" style={{ color: on ? m.color : "var(--color-ink-4)" }}>{n}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-3 grid min-h-0 flex-1 auto-rows-fr gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {lista.slice(0, VISIBLES).map((g) => <TarjetaGrupo key={g.id} g={g} />)}
      </div>

      <button onClick={() => abrir()}
        className="mt-1.5 w-full rounded-lg py-0.5 text-[11.5px] text-[var(--color-ink-3)] transition-colors hover:bg-[rgba(255,255,255,.05)] hover:text-[var(--color-ink)]">
        Ver los {num(lista.length, 0)} de {activo.label.toLowerCase()} en detalle
      </button>

      <Modal abierto={abierto} onCerrar={() => setAbierto(false)}
        titulo={`Dónde actuar · ${activo.label.toLowerCase()}`} sub={activo.accion}>
        <div className="grid h-full min-h-0 grid-cols-1 gap-6 px-7 py-5 lg:grid-cols-[292px_1fr]">
          <div className="columna-scroll flex min-h-0 flex-col gap-1.5">
            {lista.map((g) => (
              <button key={g.id} onClick={() => setElegido(g.id)}
                className={`fila grid grid-cols-[1fr_auto] items-center gap-3 px-3 py-2 text-left ${
                  g.id === detalle.id ? "bg-[rgba(255,255,255,.09)]" : ""}`}>
                <span className="truncate text-[12.5px] font-medium">{g.nombre}</span>
                <span className="tnum text-[12.5px]" style={{ color: activo.color }}>{num(g.consolidado)}</span>
              </button>
            ))}
          </div>

          <div className="min-h-0 overflow-y-auto">
            <Detalle g={detalle} />
          </div>
        </div>
      </Modal>
    </div>
  );
}
