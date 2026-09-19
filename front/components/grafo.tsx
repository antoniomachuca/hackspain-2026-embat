"use client";
/**
 * Mapa de flujos entre las sociedades de un grupo.
 * Nodo = sociedad (color por banda de score, tamaño por euros movidos).
 * Arista = flujo inferido A → B (grosor por euros, opacidad por nº de coincidencias).
 * Se dibuja en SVG con d3-force; el layout se calcula una vez, sin animación.
 */
import { useEffect, useMemo, useState } from "react";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY, type SimulationNodeDatum } from "d3-force";
import type { ApiGrafoNodo, ApiGrafoArista } from "@/lib/api";
import { banda, eur, num, mesCorto } from "@/lib/format";

type Vista = "embat" | "empresa" | "auto";
type Nodo = ApiGrafoNodo & SimulationNodeDatum & { r: number };
type Arista = { source: Nodo; target: Nodo; matches: number; eur: number; last_date: string };

const W = 900, H = 520;

export function Grafo({ nodos, aristas, vista = "auto", destacar, alto = 520 }: {
  nodos: ApiGrafoNodo[]; aristas: ApiGrafoArista[]; vista?: Vista; destacar?: string; alto?: number;
}) {
  const [layout, setLayout] = useState<{ nodos: Nodo[]; aristas: Arista[] } | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; texto: React.ReactNode } | null>(null);
  const [modo, setModo] = useState<"embat" | "empresa">("empresa");

  // Los dos effects fijan estado a propósito: sessionStorage y el layout solo existen
  // en el navegador, y calcularlos en el servidor daría una hidratación distinta.
  /* eslint-disable react-hooks/set-state-in-effect */
  // La vista "auto" respeta desde dónde llegó el usuario (lo guarda el Shell).
  useEffect(() => {
    if (vista !== "auto") { setModo(vista); return; }
    try { const v = sessionStorage.getItem("xray:modo"); if (v === "embat" || v === "empresa") setModo(v); } catch {}
  }, [vista]);

  useEffect(() => {
    const maxEur = Math.max(1, ...nodos.map((n) => n.eur_in + n.eur_out));
    const ns: Nodo[] = nodos.map((n) => ({
      ...n,
      r: 17 + 13 * Math.sqrt((n.eur_in + n.eur_out) / maxEur),
    }));
    const porId = new Map(ns.map((n) => [n.company_id, n]));
    const as: Arista[] = aristas
      .filter((a) => porId.has(a.source) && porId.has(a.target))
      .map((a) => ({ source: porId.get(a.source)!, target: porId.get(a.target)!, matches: a.matches, eur: a.eur, last_date: a.last_date }));

    // Grupos pequeños: más separación para que no queden encogidos en el centro.
    // Los nodos sin flujos se atraen al centro con más fuerza, o la repulsión los manda a las esquinas.
    const n = ns.length;
    const conectados = new Set(as.flatMap((a) => [a.source.company_id, a.target.company_id]));
    const suelto = (d: Nodo) => !conectados.has(d.company_id);
    const sim = forceSimulation(ns)
      .force("link", forceLink<Nodo, Arista>(as).distance(n <= 12 ? 170 : n <= 20 ? 130 : 105).strength(0.5))
      .force("carga", forceManyBody().strength(-Math.max(380, 11000 / n)))
      .force("centro", forceCenter(W / 2, H / 2))
      .force("x", forceX<Nodo>(W / 2).strength((d) => (suelto(d) ? 0.22 : 0.035)))
      .force("y", forceY<Nodo>(H / 2).strength((d) => (suelto(d) ? 0.28 : 0.05)))
      .force("choque", forceCollide<Nodo>((d) => d.r + 12))
      .stop();
    for (let i = 0; i < 300; i++) sim.tick();
    // Encajar en el lienzo por si el grupo es grande.
    for (const n of ns) {
      n.x = Math.max(n.r + 4, Math.min(W - n.r - 4, n.x ?? W / 2));
      n.y = Math.max(n.r + 4, Math.min(H - n.r - 4, n.y ?? H / 2));
    }
    setLayout({ nodos: ns, aristas: as });
  }, [nodos, aristas]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const maxEurArista = useMemo(() => Math.max(1, ...aristas.map((a) => a.eur)), [aristas]);
  const rutaDe = (id: string) => (modo === "embat" ? `/embat/${id}` : `/${id}`);

  if (!layout) {
    return <div style={{ height: alto }} className="flex items-center justify-center text-[12px] text-[var(--color-ink-4)]">Calculando el mapa…</div>;
  }

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: alto }} role="img" aria-label="Mapa de flujos entre sociedades del grupo">
        <defs>
          <marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#b083e8" />
          </marker>
        </defs>

        {layout.aristas.map((a, i) => {
          const dx = a.target.x! - a.source.x!, dy = a.target.y! - a.source.y!;
          const d = Math.hypot(dx, dy) || 1;
          // Curva hacia un lado para que A→B y B→A no se pisen; se acorta para que la flecha toque el borde.
          const nx = -dy / d, ny = dx / d;
          const mx = (a.source.x! + a.target.x!) / 2 + nx * d * 0.16;
          const my = (a.source.y! + a.target.y!) / 2 + ny * d * 0.16;
          const tx = a.target.x! - (dx / d) * (a.target.r + 4) + nx * 6;
          const ty = a.target.y! - (dy / d) * (a.target.r + 4) + ny * 6;
          const sx = a.source.x! + (dx / d) * (a.source.r + 2) + nx * 6;
          const sy = a.source.y! + (dy / d) * (a.source.r + 2) + ny * 6;
          const grosor = 1 + 6 * Math.sqrt(a.eur / maxEurArista);
          const denso = layout.aristas.length > 60 ? 0.55 : 1;
          const opacidad = (0.3 + 0.6 * Math.min(1, a.matches / 12)) * denso;
          const toca = destacar && (a.source.company_id === destacar || a.target.company_id === destacar);
          return (
            <path key={i} d={`M${sx},${sy} Q${mx},${my} ${tx},${ty}`} fill="none"
              stroke={toca ? "#e2ccff" : "#b083e8"} strokeWidth={grosor} strokeOpacity={opacidad} strokeLinecap="round"
              markerEnd="url(#flecha)" style={{ cursor: "help" }}
              onMouseMove={(ev) => setHover({ x: ev.clientX, y: ev.clientY, texto: (
                <>
                  <p className="font-medium">{corto(a.source.company_id)} → {corto(a.target.company_id)}</p>
                  <p className="tnum text-[var(--color-ink-3)]">{eur(a.eur)} · {a.matches} coincidencias · último {mesCorto(a.last_date.slice(0, 7))}</p>
                </>
              ) })}
              onMouseLeave={() => setHover(null)} />
          );
        })}

        {layout.nodos.map((n) => {
          const b = banda(n.score);
          const activo = n.state_eligible;
          const esDestacado = destacar === n.company_id;
          const suelto = n.eur_in + n.eur_out === 0;
          return (
            <a key={n.company_id} href={rutaDe(n.company_id)} style={{ cursor: "pointer" }}
              onMouseMove={(ev) => setHover({ x: ev.clientX, y: ev.clientY, texto: (
                <>
                  <p className="font-medium">Sociedad {corto(n.company_id)} · <span className="tnum" style={{ color: b.color }}>{num(n.score)}</span></p>
                  <p className="tnum text-[var(--color-ink-3)]">
                    {activo ? b.label : "sin historia suficiente"} · entra {eur(n.eur_in, true)} · sale {eur(n.eur_out, true)}
                  </p>
                </>
              ) })}
              onMouseLeave={() => setHover(null)}>
              {esDestacado && <circle cx={n.x} cy={n.y} r={n.r + 6} fill="none" stroke="#ffffff" strokeOpacity={0.6} strokeWidth={1.5} strokeDasharray="3 3" />}
              <circle cx={n.x} cy={n.y} r={n.r}
                fill={activo ? b.color : "#1d1630"} fillOpacity={suelto ? 0.55 : 1}
                stroke={activo ? "rgba(255,255,255,.35)" : "#373c56"} strokeWidth={1.2} />
              <text x={n.x} y={n.y} textAnchor="middle" dominantBaseline="central"
                fontSize={n.r >= 24 ? 12.5 : 11} fontWeight={600} className="tnum"
                fill={activo ? "#0d0416" : "#afafbb"} style={{ pointerEvents: "none" }}>
                {corto(n.company_id)}
              </text>
            </a>
          );
        })}
      </svg>

      {hover && (
        <div className="glass pointer-events-none fixed z-50 rounded-xl px-3 py-2 text-[12px]" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          {hover.texto}
        </div>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[var(--color-ink-4)]">
        {[85, 70, 52, 35, 15].map((s) => { const b = banda(s); return (
          <span key={s} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: b.color }} />{b.label}</span>
        ); })}
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full border border-[#373c56] bg-[#1d1630]" />sin historia</span>
        <span>· tamaño = euros movidos · grosor = euros del flujo · opacidad = coincidencias</span>
      </div>
    </div>
  );
}

const corto = (id: string) => id.replace("COMP_", "");
