"use client";
/**
 * Mapa de flujos entre las sociedades de un grupo.
 * Nodo = sociedad (color por banda de score, tamaño por euros movidos).
 * Arista = flujo inferido A → B (grosor por euros, opacidad por nº de coincidencias).
 * Layout con d3-force (una vez); el lienzo se mueve, hace zoom y deja arrastrar nodos.
 */
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY, type SimulationNodeDatum } from "d3-force";
import type { ApiGrafoNodo, ApiGrafoArista } from "@/lib/api";
import { banda, eur, num, mesCorto } from "@/lib/format";

type Nodo = ApiGrafoNodo & SimulationNodeDatum & { r: number };
type Arista = { source: Nodo; target: Nodo; matches: number; eur: number; last_date: string };
type Camara = { x: number; y: number; k: number };
type Gesto =
  | { tipo: "pan"; lastX: number; lastY: number; moved: boolean }
  | { tipo: "nodo"; id: string; moved: boolean; ox: number; oy: number; sx: number; sy: number }
  | { tipo: "pinch"; dist: number }
  | null;

const W = 900, H = 520;
const K_MIN = 0.28, K_MAX = 6;
const UMBRAL_ARRASTRE = 4;

const FONDO_LIENZO = [16, 12, 24];   // el rgba(0,0,0,.22) del lienzo sobre el panel

/** Acerca un color al fondo: 0 lo deja igual, 1 lo apaga del todo. */
function apagar(hex: string, cantidad: number) {
  const n = parseInt(hex.slice(1), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  const m = c.map((v, i) => Math.round(v + (FONDO_LIENZO[i] - v) * cantidad));
  return `rgb(${m[0]},${m[1]},${m[2]})`;
}

const ORIGEN: Camara = { x: 0, y: 0, k: 1 };

export function Grafo({ nodos, aristas, destacar, alto = 520 }: {
  nodos: ApiGrafoNodo[]; aristas: ApiGrafoArista[]; destacar?: string; alto?: number;
}) {
  const [layout, setLayout] = useState<{ nodos: Nodo[]; aristas: Arista[] } | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; texto: React.ReactNode } | null>(null);
  const [gestoUi, setGestoUi] = useState<"pan" | "nodo" | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const zoomTxtRef = useRef<HTMLSpanElement>(null);
  const camara = useRef<Camara>({ ...ORIGEN });
  const gesto = useRef<Gesto>(null);
  const punteros = useRef(new Map<number, { x: number; y: number }>());
  const router = useRouter();

  const uid = useId().replace(/:/g, "");
  const marcador = `grafo-${uid}`;   // prefijo de los degradados de cada arista

  const aplicarCamara = () => {
    const { x, y, k } = camara.current;
    gRef.current?.setAttribute("transform", `translate(${x} ${y}) scale(${k})`);
    if (zoomTxtRef.current) zoomTxtRef.current.textContent = `${Math.round(k * 100)}%`;
  };

  const zoomEn = (clientX: number, clientY: number, factor: number) => {
    const svg = svgRef.current;
    if (!svg) return;
    const pt = pantallaAViewBox(svg, clientX, clientY);
    const v = camara.current;
    const nk = clamp(v.k * factor, K_MIN, K_MAX);
    v.x = pt.x - ((pt.x - v.x) / v.k) * nk;
    v.y = pt.y - ((pt.y - v.y) / v.k) * nk;
    v.k = nk;
    aplicarCamara();
  };

  const zoomCentro = (factor: number) => {
    const svg = svgRef.current;
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    zoomEn(r.left + r.width / 2, r.top + r.height / 2, factor);
  };

  const animacion = useRef<number | null>(null);
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pararAnimacion = () => {
    if (animacion.current !== null) cancelAnimationFrame(animacion.current);
    animacion.current = null;
  };

  /** Vuelve al encuadre inicial con una curva suave, no de un salto. */
  const volverAlOrigen = (ms = 620) => {
    pararAnimacion();
    const desde = { ...camara.current };
    if (desde.x === ORIGEN.x && desde.y === ORIGEN.y && desde.k === ORIGEN.k) return;
    const t0 = performance.now();
    const paso = (ahora: number) => {
      const t = Math.min(1, (ahora - t0) / ms);
      const e = 1 - Math.pow(1 - t, 3);          // ease-out cúbica
      camara.current = {
        x: desde.x + (ORIGEN.x - desde.x) * e,
        y: desde.y + (ORIGEN.y - desde.y) * e,
        k: desde.k + (ORIGEN.k - desde.k) * e,
      };
      aplicarCamara();
      animacion.current = t < 1 ? requestAnimationFrame(paso) : null;
    };
    animacion.current = requestAnimationFrame(paso);
  };

  const resetCamara = () => volverAlOrigen();

  // Al salir del lienzo se recentra solo; si vuelves antes, se cancela.
  const programarRecentrado = () => {
    if (temporizador.current) clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => volverAlOrigen(), 900);
  };
  const cancelarRecentrado = () => {
    if (temporizador.current) clearTimeout(temporizador.current);
    temporizador.current = null;
    pararAnimacion();
  };

  useEffect(() => () => { pararAnimacion(); if (temporizador.current) clearTimeout(temporizador.current); }, []);

  // Los dos effects fijan estado a propósito: sessionStorage y el layout solo existen
  // en el navegador, y calcularlos en el servidor daría una hidratación distinta.
  /* eslint-disable react-hooks/set-state-in-effect */
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
    for (const nodo of ns) {
      nodo.x = Math.max(nodo.r + 4, Math.min(W - nodo.r - 4, nodo.x ?? W / 2));
      nodo.y = Math.max(nodo.r + 4, Math.min(H - nodo.r - 4, nodo.y ?? H / 2));
    }
    camara.current = { ...ORIGEN };
    setLayout({ nodos: ns, aristas: as });
  }, [nodos, aristas]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    aplicarCamara();
  }, [layout]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (ev: WheelEvent) => {
      ev.preventDefault();
      const sensibilidad = ev.ctrlKey ? 0.012 : 0.0016;
      zoomEn(ev.clientX, ev.clientY, Math.exp(-ev.deltaY * sensibilidad));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [layout]);

  const maxEurArista = useMemo(() => Math.max(1, ...aristas.map((a) => a.eur)), [aristas]);
  // Un clic en una sociedad abre siempre su ficha principal, venga el grafo de
  // donde venga: es lo que espera quien pincha en el nodo.
  const rutaDe = (id: string) => `/${id}`;

  const moverNodo = (id: string, clientX: number, clientY: number, ox: number, oy: number) => {
    const svg = svgRef.current;
    if (!svg) return;
    const mundo = pantallaAMundo(svg, camara.current, clientX, clientY);
    setLayout((prev) => {
      if (!prev) return prev;
      const nodos = prev.nodos.map((n) =>
        n.company_id === id ? { ...n, x: mundo.x - ox, y: mundo.y - oy } : n,
      );
      const porId = new Map(nodos.map((n) => [n.company_id, n]));
      return {
        nodos,
        aristas: prev.aristas.map((a) => ({
          ...a,
          source: porId.get(a.source.company_id)!,
          target: porId.get(a.target.company_id)!,
        })),
      };
    });
  };

  const onPointerDown = (ev: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    svg.focus({ preventScroll: true });
    punteros.current.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });

    if (punteros.current.size === 2) {
      const pts = [...punteros.current.values()];
      gesto.current = { tipo: "pinch", dist: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) || 1 };
      setGestoUi("pan");
      setHover(null);
      svg.setPointerCapture(ev.pointerId);
      return;
    }

    const idNodo = (ev.target as Element | null)?.closest?.("[data-nodo]")?.getAttribute("data-nodo");
    if (idNodo && layout) {
      const nodo = layout.nodos.find((n) => n.company_id === idNodo);
      const mundo = pantallaAMundo(svg, camara.current, ev.clientX, ev.clientY);
      gesto.current = {
        tipo: "nodo",
        id: idNodo,
        moved: false,
        ox: mundo.x - (nodo?.x ?? 0),
        oy: mundo.y - (nodo?.y ?? 0),
        sx: ev.clientX,
        sy: ev.clientY,
      };
    } else {
      gesto.current = { tipo: "pan", lastX: ev.clientX, lastY: ev.clientY, moved: false };
      setGestoUi("pan");
      setHover(null);
    }
    svg.setPointerCapture(ev.pointerId);
  };

  const onPointerMove = (ev: React.PointerEvent<SVGSVGElement>) => {
    if (punteros.current.has(ev.pointerId)) {
      punteros.current.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
    }

    const g = gesto.current;
    if (!g) {
      return;
    }

    if (g.tipo === "pinch" && punteros.current.size >= 2) {
      const pts = [...punteros.current.values()];
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) || 1;
      const cx = (pts[0].x + pts[1].x) / 2;
      const cy = (pts[0].y + pts[1].y) / 2;
      zoomEn(cx, cy, dist / g.dist);
      g.dist = dist;
      return;
    }

    if (g.tipo === "pan") {
      const svg = svgRef.current;
      if (!svg) return;
      const dx = ev.clientX - g.lastX;
      const dy = ev.clientY - g.lastY;
      if (!g.moved && Math.hypot(dx, dy) < UMBRAL_ARRASTRE) return;
      g.moved = true;
      const r = svg.getBoundingClientRect();
      camara.current.x += dx * (W / r.width);
      camara.current.y += dy * (H / r.height);
      g.lastX = ev.clientX;
      g.lastY = ev.clientY;
      aplicarCamara();
      return;
    }

    if (g.tipo === "nodo") {
      const svg = svgRef.current;
      if (!svg) return;
      const dist = Math.hypot(ev.clientX - g.sx, ev.clientY - g.sy);
      if (!g.moved && dist < UMBRAL_ARRASTRE) return;
      if (!g.moved) {
        g.moved = true;
        setGestoUi("nodo");
        setHover(null);
      }
      moverNodo(g.id, ev.clientX, ev.clientY, g.ox, g.oy);
    }
  };

  const soltarPuntero = (ev: React.PointerEvent<SVGSVGElement>) => {
    const g = gesto.current;
    if (g?.tipo === "nodo" && !g.moved && ev.type === "pointerup" && !ev.ctrlKey && !ev.metaKey && ev.button === 0) {
      router.push(rutaDe(g.id));
    }
    punteros.current.delete(ev.pointerId);
    if (punteros.current.size < 2 && gesto.current?.tipo === "pinch") {
      gesto.current = null;
      setGestoUi(null);
    }
    if (punteros.current.size === 0) {
      gesto.current = null;
      setGestoUi(null);
    }
  };

  const onKeyDown = (ev: React.KeyboardEvent<SVGSVGElement>) => {
    const paso = ev.shiftKey ? 80 : 36;
    if (ev.key === "+" || ev.key === "=") { ev.preventDefault(); zoomCentro(1.18); }
    else if (ev.key === "-" || ev.key === "_") { ev.preventDefault(); zoomCentro(1 / 1.18); }
    else if (ev.key === "0") { ev.preventDefault(); resetCamara(); }
    else if (ev.key === "ArrowLeft") { ev.preventDefault(); camara.current.x += paso; aplicarCamara(); }
    else if (ev.key === "ArrowRight") { ev.preventDefault(); camara.current.x -= paso; aplicarCamara(); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); camara.current.y += paso; aplicarCamara(); }
    else if (ev.key === "ArrowDown") { ev.preventDefault(); camara.current.y -= paso; aplicarCamara(); }
  };

  if (!layout) {
    return <div style={{ height: alto }} className="flex items-center justify-center text-[12px] text-[var(--color-ink-4)]">Calculando el mapa…</div>;
  }

  const cursor = gestoUi === "pan" || gestoUi === "nodo" ? "grabbing" : "grab";

  return (
    <div className="relative">
      <div
        className="relative overflow-hidden rounded-[18px]"
        style={{ height: alto, background: "rgba(0,0,0,.22)", boxShadow: "inset 0 0 0 1px rgba(255,255,255,.05)" }}
        onPointerEnter={cancelarRecentrado}
        onPointerLeave={programarRecentrado}
      >
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          tabIndex={0}
          role="application"
          aria-label="Mapa de flujos entre sociedades del grupo. Rueda para zoom, arrastra el fondo, arrastra una sociedad. Clic abre la ficha."
          className="block h-full w-full touch-none outline-none"
          style={{ width: "100%", height: alto, cursor, userSelect: "none" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={soltarPuntero}
          onPointerCancel={soltarPuntero}
          onDoubleClick={(ev) => {
            if ((ev.target as Element | null)?.closest?.("[data-nodo]")) return;
            zoomEn(ev.clientX, ev.clientY, 1.45);
          }}
          onKeyDown={onKeyDown}
        >
          <defs>
            <marker id={marcador} viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
              <path d="M0.5,0.8 L9.5,5 L0.5,9.2 Z" fill="#a9a3c6" />
            </marker>
          </defs>

          <g ref={gRef}>
            {layout.aristas.map((a, i) => {
              const dx = a.target.x! - a.source.x!, dy = a.target.y! - a.source.y!;
              const d = Math.hypot(dx, dy) || 1;
              const nx = -dy / d, ny = dx / d;
              const mx = (a.source.x! + a.target.x!) / 2 + nx * d * 0.16;
              const my = (a.source.y! + a.target.y!) / 2 + ny * d * 0.16;
              const tx = a.target.x! - (dx / d) * (a.target.r + 6) + nx * 6;
              const ty = a.target.y! - (dy / d) * (a.target.r + 6) + ny * 6;
              const sx = a.source.x! + (dx / d) * (a.source.r + 2) + nx * 6;
              const sy = a.source.y! + (dy / d) * (a.source.r + 2) + ny * 6;
              const grosor = 0.9 + 4.4 * Math.sqrt(a.eur / maxEurArista);
              const denso = layout.aristas.length > 60 ? 0.55 : 1;
              const opacidad = (0.26 + 0.44 * Math.min(1, a.matches / 12)) * denso;
              const toca = destacar && (a.source.company_id === destacar || a.target.company_id === destacar);
              return (
                <g key={i}>
                <linearGradient id={`${marcador}-g${i}`} gradientUnits="userSpaceOnUse"
                  x1={sx} y1={sy} x2={tx} y2={ty}>
                  <stop offset="0%" stopColor="#6d6a86" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#8d88ab" stopOpacity={0.62} />
                </linearGradient>
                <path d={`M${sx},${sy} Q${mx},${my} ${tx},${ty}`} fill="none"
                  stroke={toca ? "#b9b2d6" : `url(#${marcador}-g${i})`} strokeWidth={grosor}
                  strokeOpacity={opacidad} strokeLinecap="round"
                  markerEnd={`url(#${marcador})`}
                  style={{ cursor: "help", pointerEvents: gestoUi ? "none" : "stroke" }}
                  onMouseMove={(e) => {
                    if (gesto.current) return;
                    setHover({ x: e.clientX, y: e.clientY, texto: (
                      <>
                        <p className="font-medium">{corto(a.source.company_id)} → {corto(a.target.company_id)}</p>
                        <p className="tnum text-[var(--color-ink-3)]">{eur(a.eur)} · {a.matches} coincidencias · último {mesCorto(a.last_date.slice(0, 7))}</p>
                      </>
                    ) });
                  }}
                  onMouseLeave={() => setHover(null)} />
                </g>
              );
            })}

            {layout.nodos.map((n) => {
              const b = banda(n.score);
              const activo = n.state_eligible;
              const esDestacado = destacar === n.company_id;
              const suelto = n.eur_in + n.eur_out === 0;
              return (
                <a key={n.company_id} href={rutaDe(n.company_id)} data-nodo={n.company_id}
                  style={{ cursor: gestoUi === "nodo" ? "grabbing" : "grab" }}
                  onClick={(e) => { if (!e.ctrlKey && !e.metaKey) e.preventDefault(); }}
                  onDragStart={(e) => e.preventDefault()}
                  onMouseMove={(e) => {
                    if (gesto.current) return;
                    setHover({ x: e.clientX, y: e.clientY, texto: (
                      <>
                        <p className="font-medium">Sociedad {corto(n.company_id)} · <span className="tnum" style={{ color: b.color }}>{num(n.score)}</span></p>
                        <p className="tnum text-[var(--color-ink-3)]">
                          {activo ? b.label : "sin historia suficiente"} · entra {eur(n.eur_in, true)} · sale {eur(n.eur_out, true)}
                        </p>
                        <p className="mt-0.5 text-[10.5px] text-[var(--color-ink-4)]">Arrastra para mover · clic para abrir</p>
                      </>
                    ) });
                  }}
                  onMouseLeave={() => setHover(null)}>
                  {esDestacado && <circle cx={n.x} cy={n.y} r={n.r + 7} fill="none" stroke="rgba(255,255,255,.22)" strokeWidth={1} />}
                  <circle cx={n.x} cy={n.y} r={n.r} fill="#14101f" fillOpacity={suelto ? 0.7 : 0.9} />
                  <circle cx={n.x} cy={n.y} r={n.r - 1.5} fill="none"
                    stroke={activo ? apagar(b.color, 0.42) : "#33374d"} strokeOpacity={activo ? 0.9 : 0.65}
                    strokeWidth={esDestacado ? 2.6 : 1.8} />
                  <text x={n.x} y={n.y! - (n.r >= 20 ? 4.5 : 0)} textAnchor="middle" dominantBaseline="central"
                    fontSize={n.r >= 20 ? 13 : 10.5} fontWeight={600} className="tnum"
                    fill={activo ? "rgba(233,231,240,.88)" : "#6f7390"} style={{ pointerEvents: "none" }}>
                    {activo ? num(n.score) : "—"}
                  </text>
                  {/* El código siempre se ve: dentro del nodo si cabe, y si no,
                      colgado justo debajo del círculo. */}
                  {n.r >= 20 ? (
                    <text x={n.x} y={n.y! + 9} textAnchor="middle" dominantBaseline="central"
                      fontSize={8.5} fontWeight={500} letterSpacing={0.4}
                      fill="rgba(255,255,255,.34)" style={{ pointerEvents: "none" }}>
                      {corto(n.company_id)}
                    </text>
                  ) : (
                    <text x={n.x} y={n.y! + n.r + 8} textAnchor="middle" dominantBaseline="central"
                      fontSize={8.5} fontWeight={500} letterSpacing={0.4}
                      fill="rgba(255,255,255,.42)" style={{ pointerEvents: "none",
                        paintOrder: "stroke", stroke: "#14101f", strokeWidth: 2.6, strokeLinejoin: "round" }}>
                      {corto(n.company_id)}
                    </text>
                  )}
                </a>
              );
            })}
          </g>
        </svg>

        <div className="absolute right-2.5 top-2.5 z-10 flex items-center gap-0.5 rounded-full border border-[rgba(255,255,255,.1)] bg-[rgba(8,6,14,.78)] p-1 backdrop-blur-md">
          <BotonVista aria="Alejar" onClick={() => zoomCentro(1 / 1.22)}>−</BotonVista>
          <button
            type="button"
            onClick={resetCamara}
            className="min-w-[3.1rem] px-1.5 text-center text-[11px] tabular-nums text-[var(--color-ink-3)] transition-[color,background-color,scale] duration-150 hover:text-[var(--color-ink)] active:scale-[0.96]"
            style={{ transitionTimingFunction: "cubic-bezier(0.2, 0, 0, 1)" }}
            aria-label="Restablecer zoom"
            title="Restablecer (0)"
          >
            <span ref={zoomTxtRef}>100%</span>
          </button>
          <BotonVista aria="Acercar" onClick={() => zoomCentro(1.22)}>+</BotonVista>
        </div>
      </div>

      {/* El tooltip se cuelga del body: la Card que envuelve el grafo lleva
          backdrop-filter, y eso la convierte en el bloque contenedor de sus
          hijos `fixed`. Dentro de ella, las coordenadas del ratón se
          desplazaban y el globo caía fuera de la vista. */}
      {hover && !gestoUi && createPortal(
        <div className="glass pointer-events-none fixed z-50 rounded-xl px-3 py-2 text-[12px]"
          style={{ left: hover.x + 12, top: hover.y + 12 }}>
          {hover.texto}
        </div>,
        document.body,
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[var(--color-ink-4)]">
        {[85, 70, 52, 35, 15].map((s) => { const b = banda(s); return (
          <span key={s} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full border-2" style={{ borderColor: apagar(b.color, 0.42) }} />{b.label}</span>
        ); })}
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full border-2 border-[#373c56]" />sin historia</span>
        <span>rueda = zoom · arrastra el mapa · mueve una sociedad · doble clic acerca</span>
      </div>
    </div>
  );
}

function BotonVista({ children, onClick, aria }: { children: React.ReactNode; onClick: () => void; aria: string }) {
  return (
    <button
      type="button"
      aria-label={aria}
      onClick={onClick}
      className="grid h-8 w-8 place-items-center rounded-full text-[16px] leading-none text-[var(--color-ink-2)] transition-[background-color,color,scale] duration-150 hover:bg-[rgba(255,255,255,.12)] hover:text-[var(--color-ink)] active:scale-[0.96]"
      style={{ transitionTimingFunction: "cubic-bezier(0.2, 0, 0, 1)" }}
    >
      {children}
    </button>
  );
}

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

function pantallaAViewBox(svg: SVGSVGElement, clientX: number, clientY: number) {
  const r = svg.getBoundingClientRect();
  return {
    x: ((clientX - r.left) / r.width) * W,
    y: ((clientY - r.top) / r.height) * H,
  };
}

function pantallaAMundo(svg: SVGSVGElement, cam: Camara, clientX: number, clientY: number) {
  const pt = pantallaAViewBox(svg, clientX, clientY);
  return { x: (pt.x - cam.x) / cam.k, y: (pt.y - cam.y) / cam.k };
}

const corto = (id: string) => id.replace("COMP_", "");
