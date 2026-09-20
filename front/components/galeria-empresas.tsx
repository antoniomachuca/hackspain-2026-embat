"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiEmpresas, apiHistoria, type ApiEmpresa } from "@/lib/api";
import { nombreDe } from "@/lib/motor";
import { ESTADO_LABEL, type Estado } from "@/lib/data";
import { num } from "@/lib/format";
import { segmentoDe, SEGMENTOS } from "@/lib/cartera";
import { ScoreBadge, EstadoChip, Delta } from "@/components/ui";
import { Trayectoria } from "@/components/charts";
import { Modal } from "@/components/modal";

const POR_LOTE = 500;   // el tope que admite /api/companies

const etiqueta = (st: string) => ESTADO_LABEL[st as Estado] ?? (st === "EVALUACION_PENDIENTE" ? "Pendiente" : st);

/** Los números y la trayectoria del cliente elegido. */
function Detalle({ c }: { c: ApiEmpresa }) {
  const [cache, setCache] = useState<{ id: string; puntos: { mes: string; score: number; nivel: number }[] } | null>(null);

  useEffect(() => {
    let vivo = true;
    apiHistoria(c.company_id, 24).then((h) => {
      if (!vivo) return;
      setCache({
        id: c.company_id,
        puntos: (h?.history ?? []).map((p) => ({ mes: p.as_of.slice(0, 7), score: p.score, nivel: p.base_health })),
      });
    });
    return () => { vivo = false; };
  }, [c.company_id]);

  const listo = cache?.id === c.company_id;
  const seg = segmentoDe({ score: c.score, estado: c.state, delta3m: c.delta_3m, elegible: c.state_eligible });
  const s = seg ? SEGMENTOS[seg] : null;

  const datos: [string, React.ReactNode][] = [
    ["Score", c.state_eligible ? <ScoreBadge key="s" score={c.score} size="sm" /> : <span key="s" className="tnum text-[13px] text-[var(--color-ink-4)]">sin score</span>],
    ["Δ 3 meses", <Delta key="d" v={c.delta_3m} sufijo=" pts" />],
    ["Momentum", <Delta key="m" v={c.momentum} />],
    ["Estado", <EstadoChip key="e" estado={c.state} />],
  ];

  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-[15px] font-semibold tracking-tight">{nombreDe(c.company_id)}</h3>
          {s && (
            <span className="rounded-md px-2 py-0.5 text-[11px] font-medium" style={{ background: s.bg, color: s.color }}>
              {s.label}
            </span>
          )}
        </div>
        <Link href={`/embat/${c.company_id}`} className="text-[11.5px] text-[var(--color-purple)] hover:underline">
          Abrir la ficha →
        </Link>
      </div>
      <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
        {c.company_id} · {c.group_id.replace("GROUP_", "Grupo ")}{c.erp ? ` · ERP ${c.erp}` : ""}
      </p>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        {datos.map(([k, v]) => (
          <div key={k}>
            <p className="text-[10px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
            <p className="mt-1">{v}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 border-t border-[var(--color-line)] pt-3">
        <p className="text-[11.5px] text-[var(--color-ink-4)]">Trayectoria de 24 meses</p>
        <div className="mt-2 min-h-[150px]">
          {listo && cache.puntos.length > 1
            ? <Trayectoria datos={cache.puntos} altura={150} />
            : <div className="flex h-[150px] items-center justify-center text-[12px] text-[var(--color-ink-4)]">
                {listo ? "Sin historia suficiente" : "Cargando…"}
              </div>}
        </div>
      </div>

      {s && <p className="mt-3 text-[12px] leading-relaxed text-[var(--color-ink-2)]">{s.accion}</p>}
    </div>
  );
}

/**
 * La cartera entera, en un diálogo.
 *
 * Fuera solo se ven cuatro clientes porque una tabla de 1.286 filas paginada
 * de 25 en 25 no es una vista: es un archivo. Quien quiera buscar, entra aquí,
 * y quien solo quiera saber cómo va la cartera, no baja 52 páginas.
 */
export function GaleriaEmpresas({ etiqueta: texto, total }: { etiqueta: string; total: number }) {
  const [abierto, setAbierto] = useState(false);
  const [items, setItems] = useState<ApiEmpresa[] | null>(null);
  const [q, setQ] = useState("");
  const [elegido, setElegido] = useState<string | null>(null);

  useEffect(() => {
    if (!abierto || items) return;
    let vivo = true;
    (async () => {
      const lotes: ApiEmpresa[] = [];
      for (let offset = 0; offset < total; offset += POR_LOTE) {
        const r = await apiEmpresas({ limit: POR_LOTE, offset, order_by: "score", order_dir: "desc" });
        if (!vivo) return;
        lotes.push(...(r?.items ?? []));
        if (!r?.items?.length) break;
      }
      if (vivo) setItems(lotes);
    })();
    return () => { vivo = false; };
  }, [abierto, items, total]);

  const lista = useMemo(() => {
    const t = q.trim().toUpperCase();
    if (!items) return [];
    if (!t) return items;
    return items.filter((c) =>
      c.company_id.toUpperCase().includes(t) ||
      c.group_id.toUpperCase().includes(t) ||
      nombreDe(c.company_id).toUpperCase().includes(t) ||
      etiqueta(c.state).toUpperCase().includes(t));
  }, [items, q]);

  const detalle = lista.find((c) => c.company_id === elegido) ?? lista[0];

  return (
    <>
      <button onClick={() => setAbierto(true)}
        className="mt-2 w-full rounded-lg py-2 text-[12px] text-[var(--color-ink-3)] transition-colors hover:bg-[rgba(255,255,255,.05)] hover:text-[var(--color-ink)]">
        {texto}
      </button>

      <Modal abierto={abierto} onCerrar={() => setAbierto(false)}
        titulo="Toda la cartera" sub={`${num(total, 0)} clientes · busca por nombre, identificador, grupo o estado`}>
        <div className="grid h-full min-h-0 grid-cols-1 gap-6 px-7 py-5 lg:grid-cols-[320px_1fr]">
          <div className="flex min-h-0 flex-col">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar" maxLength={24}
              className="h-9 flex-none rounded-full border border-[rgba(255,255,255,.1)] bg-[rgba(255,255,255,.06)] px-3.5 text-[12.5px] outline-none placeholder:text-[var(--color-ink-4)] focus:border-[var(--color-purple)]" />
            <p className="mt-2 flex-none text-[11px] text-[var(--color-ink-4)]">
              {items ? `${num(lista.length, 0)} de ${num(items.length, 0)}` : "Cargando la cartera…"}
            </p>

            <div className="columna-scroll mt-2 flex min-h-0 flex-1 flex-col gap-1">
              {lista.map((c) => (
                <button key={c.company_id} onClick={() => setElegido(c.company_id)}
                  className={`fila grid grid-cols-[1fr_auto] items-center gap-3 px-3 py-2 text-left ${
                    detalle && c.company_id === detalle.company_id ? "bg-[rgba(255,255,255,.09)]" : ""}`}>
                  <span className="min-w-0">
                    <span className="block truncate text-[12.5px] font-medium">{nombreDe(c.company_id)}</span>
                    <span className="block truncate text-[10.5px] text-[var(--color-ink-4)]">
                      {c.group_id.replace("GROUP_", "Grupo ")} · {etiqueta(c.state)}
                    </span>
                  </span>
                  {c.state_eligible
                    ? <ScoreBadge score={c.score} size="sm" />
                    : <span className="tnum text-[12px] text-[var(--color-ink-4)]">—</span>}
                </button>
              ))}
              {items && lista.length === 0 && (
                <p className="py-8 text-center text-[12px] text-[var(--color-ink-4)]">Ningún cliente coincide.</p>
              )}
            </div>
          </div>

          <div className="min-h-0 overflow-y-auto">
            {detalle
              ? <Detalle c={detalle} />
              : <p className="text-[12px] text-[var(--color-ink-4)]">Cargando la cartera…</p>}
          </div>
        </div>
      </Modal>
    </>
  );
}
