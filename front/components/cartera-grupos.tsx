"use client";
import { useState } from "react";
import Link from "next/link";
import type { GrupoCartera } from "@/lib/motor";
import { eur, num } from "@/lib/format";
import { ScoreBadge } from "@/components/ui";

/* Las bandas del score, de peor a mejor, con su color y su tramo. */
const BANDAS: { label: string; color: string; min: number; max: number }[] = [
  { label: "Crítico",  color: "#ff5a3c", min: 0,  max: 25 },
  { label: "Frágil",   color: "#ff9425", min: 25, max: 45 },
  { label: "Atención", color: "#ffcf1a", min: 45, max: 60 },
  { label: "Estable",  color: "#46dd86", min: 60, max: 80 },
  { label: "Sólido",   color: "#13ef73", min: 80, max: 101 },
];

/** La escala intensa: en un punto de 3 px la paleta suave desaparece. */
function tono(score: number) {
  return (BANDAS.find((b) => score >= b.min && score < b.max) ?? BANDAS[0]).color;
}

/**
 * Media del grupo contra su peor filial. La nube es el dato; todo lo que hay
 * que explicar vive fuera del dibujo, en HTML, porque dentro el texto se
 * quedaba en 8 px sobre un fondo oscuro y no se leía.
 */
export function Dispersion({ grupos, alto = 106 }: { grupos: GrupoCartera[]; alto?: number }) {
  const [sobre, setSobre] = useState<GrupoCartera | null>(null);
  const ancho = 330;
  const padL = 16, padR = 6, padT = 5, padB = 13;
  const w = ancho - padL - padR;
  const h = alto - padT - padB;

  const x = (v: number) => padL + (v / 100) * w;
  const y = (v: number) => padT + (1 - v / 100) * h;

  return (
    <div className="relative w-full">
      <svg viewBox={`0 0 ${ancho} ${alto}`} className="w-full" role="img"
        aria-label="Media del grupo frente a su peor filial: cuanto más abajo de la diagonal, más dispersión interna.">
        <rect x={x(60)} y={y(40)} width={x(100) - x(60)} height={y(0) - y(40)} rx={4} fill="rgba(255,90,60,.08)" />

        <line x1={x(0)} y1={y(0)} x2={x(100)} y2={y(100)} stroke="rgba(255,255,255,.32)" strokeDasharray="3 3" />
        <line x1={padL} y1={y(40)} x2={padL + w} y2={y(40)} stroke="#ff5a3c" strokeOpacity={0.5} strokeDasharray="2 2" />

        {[0, 50, 100].map((v) => (
          <g key={v}>
            <text x={padL - 4} y={y(v)} textAnchor="end" dominantBaseline="central"
              fontSize={6.5} fill="#7b7889" className="tnum">{v}</text>
            <text x={x(v)} y={alto - 4} textAnchor="middle" fontSize={6.5} fill="#7b7889" className="tnum">{v}</text>
          </g>
        ))}

        {grupos.map((g) => {
          const activo = sobre?.id === g.id;
          return (
            <circle key={g.id} cx={x(g.media)} cy={y(g.peor.score)}
              r={activo ? 3.6 : 1.5 + Math.min(1.7, g.filiales / 13)}
              fill={tono(g.consolidado)}
              fillOpacity={activo ? 1 : g.motivo === "SIN_SENAL" ? 0.28 : 0.88}
              stroke={activo ? "#fff" : "none"} strokeWidth={1}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setSobre(g)} onMouseLeave={() => setSobre(null)} />
          );
        })}
      </svg>

      {sobre && (
        <div className="glass pointer-events-none absolute left-1 top-1 rounded-xl px-3 py-2 text-[11.5px]">
          <p className="font-medium">{sobre.nombre}</p>
          <p className="tnum text-[var(--color-ink-3)]">
            media {num(sobre.media)} · peor filial {num(sobre.peor.score)}
          </p>
          <p className="tnum text-[var(--color-ink-4)]">
            la media le esconde {num(sobre.media - sobre.peor.score)} puntos
          </p>
        </div>
      )}
    </div>
  );
}

/** El recorrido interno del grupo, de su peor filial a la mejor. */
export function Tira({ g }: { g: GrupoCartera }) {
  const pos = (v: number) => `${Math.max(0, Math.min(100, v))}%`;
  return (
    <div className="relative h-[13px] w-full">
      <div className="absolute top-1/2 h-[3px] w-full -translate-y-1/2 rounded-full bg-[rgba(255,255,255,.07)]" />
      <div className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
        style={{
          left: pos(g.peor.score), width: `${Math.max(1, g.mejor.score - g.peor.score)}%`,
          background: `linear-gradient(90deg, ${tono(g.peor.score)}, ${tono(g.mejor.score)})`,
          opacity: 0.9,
        }} />
      <span className="absolute top-1/2 h-[10px] w-[2px] -translate-y-1/2 rounded-full bg-white"
        style={{ left: pos(g.consolidado) }} />
    </div>
  );
}

const CIFRA: Record<string, (g: GrupoCartera) => string> = {
  CONTAGIO:    (g) => `−${num(g.penalizacion)} pts`,
  DETERIORO:   (g) => `${g.enRiesgo} de ${g.filiales}`,
  DISPERSION:  (g) => `${num(g.mejor.score - g.peor.score, 0)} pts`,
  OPORTUNIDAD: (g) => `${num(g.cobertura, 0)} % cobertura`,
  SIN_SENAL:   (g) => `${g.filiales} ${g.filiales === 1 ? "sociedad" : "sociedades"}`,
};

/** Una sociedad, un punto: las que están en riesgo se ven sin contar nada. */
function Puntos({ g }: { g: GrupoCartera }) {
  const MAX = 14;
  const n = Math.min(g.filiales, MAX);
  const riesgo = Math.min(g.enRiesgo, n);
  return (
    <span className="flex flex-wrap items-center gap-[3px]" title={`${g.enRiesgo} de ${g.filiales} en riesgo`}>
      {Array.from({ length: n }, (_, i) => (
        <span key={i} className="h-[6px] w-[6px] rounded-full"
          style={{ background: i < riesgo ? "#ff5a3c" : "rgba(255,255,255,.22)" }} />
      ))}
      {g.filiales > MAX && <span className="tnum text-[9.5px] text-[var(--color-ink-4)]">+{g.filiales - MAX}</span>}
    </span>
  );
}

export function FilaGrupo({ g }: { g: GrupoCartera }) {
  return (
    <Link href={`/grupo/${g.id}`}
      className="fila grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1.5 px-3 py-1.5 lg:grid-cols-[168px_104px_1fr_88px_98px_44px]">
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium">{g.nombre}</p>
        <p className="truncate text-[10.5px] text-[var(--color-ink-4)]">
          {g.filiales} sociedades{g.erp ? ` · ${g.erp}` : ""}
        </p>
      </div>

      <div className="hidden lg:block"><Puntos g={g} /></div>

      <div className="col-span-2 flex min-w-0 items-center gap-2 lg:col-span-1">
        <span className="tnum w-5 flex-none text-right text-[10px]" style={{ color: tono(g.peor.score) }}>
          {num(g.peor.score, 0)}
        </span>
        <span className="min-w-0 flex-1"><Tira g={g} /></span>
        <span className="tnum w-5 flex-none text-[10px]" style={{ color: tono(g.mejor.score) }}>
          {num(g.mejor.score, 0)}
        </span>
      </div>

      <span className="tnum hidden text-right text-[11.5px] text-[var(--color-ink-3)] lg:block">
        {CIFRA[g.motivo](g)}
      </span>

      <span className="tnum hidden text-right text-[11px] text-[var(--color-ink-4)] lg:block">
        {g.flujoInterno > 0 ? `${eur(g.flujoInterno, true)} interno` : "sin flujo"}
      </span>

      <span className="text-right"><ScoreBadge score={g.consolidado} size="sm" /></span>
    </Link>
  );
}

/**
 * El reparto de la cartera por bandas, en anillo.
 *
 * El arco se pinta por segmentos cortos en vez de con `stroke-dasharray`: con
 * un solo trazo por banda, los extremos redondeados se montan unos sobre otros
 * y el hueco entre bandas deja de medir lo que dice.
 */
export function AnilloReparto({ grupos, tam = 140, grosor = 17 }: {
  grupos: GrupoCartera[]; tam?: number; grosor?: number;
}) {
  const [sobre, setSobre] = useState<number | null>(null);

  const tramos = BANDAS.map((b) => ({
    ...b,
    n: grupos.filter((g) => g.consolidado >= b.min && g.consolidado < b.max).length,
  }));
  const total = tramos.reduce((s, t) => s + t.n, 0) || 1;

  const r = (tam - grosor) / 2 - 3;
  const c = tam / 2;
  const HUECO = 2.2;                       // grados de aire entre bandas
  /**
   * Redondeado a tres decimales a propósito. `Math.cos` y `Math.sin` pueden
   * diferir en el último bit entre el Node que renderiza en el servidor y el
   * V8 del navegador, y React compara los atributos como texto: un
   * `88.94634171114498` contra un `88.94634171114497` rompe la hidratación.
   * A esta escala, la milésima de píxel no se ve.
   */
  const punto = (a: number) => {
    const rad = ((a - 90) * Math.PI) / 180;
    const red = (v: number) => Math.round(v * 1000) / 1000;
    return [red(c + r * Math.cos(rad)), red(c + r * Math.sin(rad))] as const;
  };

  const arcos = tramos.map((t, i) => {
    const inicio = tramos.slice(0, i).reduce((a, x) => a + (x.n / total) * 360, 0);
    const barrido = (t.n / total) * 360;
    return {
      ...t, i,
      desde: inicio + HUECO / 2,
      hasta: inicio + barrido - HUECO / 2,
      visible: barrido > HUECO,
    };
  });

  const sel = sobre === null ? null : arcos[sobre];

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
      <svg width={tam} height={tam} viewBox={`0 0 ${tam} ${tam}`} role="img"
        aria-label="Reparto de los grupos por banda del consolidado">
        <circle cx={c} cy={c} r={r} fill="none" stroke="rgba(255,255,255,.05)" strokeWidth={grosor} />

        {arcos.map((a) => {
          if (!a.visible) return null;
          const pasos = Math.max(2, Math.round((a.hasta - a.desde) / 1.5));
          const activo = sobre === a.i;
          return (
            <g key={a.label} onMouseEnter={() => setSobre(a.i)} onMouseLeave={() => setSobre(null)}
              style={{ cursor: "pointer" }}>
              {Array.from({ length: pasos }, (_, k) => {
                const p0 = punto(a.desde + ((a.hasta - a.desde) * k) / pasos);
                const p1 = punto(a.desde + ((a.hasta - a.desde) * (k + 1)) / pasos);
                return (
                  <line key={k} x1={p0[0]} y1={p0[1]} x2={p1[0]} y2={p1[1]}
                    stroke={a.color} strokeWidth={activo ? grosor + 5 : grosor}
                    strokeOpacity={sobre === null || activo ? 1 : 0.34} strokeLinecap="butt" />
                );
              })}
            </g>
          );
        })}

        <text x={c} y={c - 7} textAnchor="middle" dominantBaseline="central"
          className="tnum" fontSize={23} fontWeight={600}
          fill={sel ? sel.color : "rgba(233,231,240,.92)"}>
          {sel ? sel.n : total}
        </text>
        <text x={c} y={c + 16} textAnchor="middle" dominantBaseline="central"
          fontSize={11} fill="#8b8798">
          {sel ? sel.label.toLowerCase() : "grupos"}
        </text>
      </svg>

      <div className="flex min-w-[178px] flex-col gap-1">
        {arcos.map((a) => (
          <button key={a.label} type="button"
            onMouseEnter={() => setSobre(a.i)} onMouseLeave={() => setSobre(null)}
            className="flex items-center gap-2.5 rounded-lg px-2 py-1 text-left transition-colors hover:bg-[rgba(255,255,255,.05)]">
            <span className="h-3 w-3 flex-none rounded-full" style={{ background: a.color }} />
            <span className="flex-1 text-[13.5px]" style={{ color: sobre === a.i ? "var(--color-ink)" : "var(--color-ink-2)" }}>
              {a.label}
            </span>
            <span className="tnum text-[13.5px] font-medium">{a.n}</span>
            <span className="tnum w-10 text-right text-[11.5px] text-[var(--color-ink-4)]">
              {num((a.n / total) * 100, 0)} %
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * El mismo grupo, en formato columna: cabe el triple por fila sin perder lo
 * que importa —el recorrido interno, la cifra del motivo y el consolidado—.
 */
export function TarjetaGrupo({ g }: { g: GrupoCartera }) {
  return (
    <Link href={`/grupo/${g.id}`} className="fila flex h-full min-h-0 flex-col justify-center gap-0.5 px-3.5 py-1 [@media(max-height:860px)]:py-0.5">
      <div className="flex items-baseline justify-between gap-2 leading-tight">
        <span className="truncate text-[13px] font-medium leading-tight">{g.nombre}</span>
        <span className="tnum flex-none text-[15px] font-semibold" style={{ color: tono(g.consolidado) }}>
          {num(g.consolidado, 0)}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="tnum w-4 flex-none text-right text-[9.5px]" style={{ color: tono(g.peor.score) }}>
          {num(g.peor.score, 0)}
        </span>
        <span className="min-w-0 flex-1"><Tira g={g} /></span>
        <span className="tnum w-4 flex-none text-[9.5px]" style={{ color: tono(g.mejor.score) }}>
          {num(g.mejor.score, 0)}
        </span>
      </div>

      <div className="flex items-center justify-between gap-2 [@media(max-height:860px)]:hidden">
        <Puntos g={g} />
        <span className="tnum flex-none text-[10px] text-[var(--color-ink-3)]">{CIFRA[g.motivo](g)}</span>
      </div>
    </Link>
  );
}
