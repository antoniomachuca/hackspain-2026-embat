"use client";
import {
  Line, XAxis, YAxis, ResponsiveContainer, Tooltip,
  ReferenceLine, ReferenceDot, BarChart, Bar, Cell, CartesianGrid, Area, AreaChart,
} from "recharts";
import { useId } from "react";
import { mesCorto, num, banda } from "@/lib/format";
import type { Punto, Driver, EpisodioSenal } from "@/lib/data";

const EJE = { fontSize: 11, fill: "#afafbb" };

type CajaProps = {
  active?: boolean;
  payload?: { name: string; value: number; color?: string }[];
  label?: string;
};

function Caja({ active, payload, label }: CajaProps) {
  if (!active || !payload?.length) return null;
  const texto = typeof label === "string" && label.includes("-") ? mesCorto(label) : label;
  return (
    <div className="glass rounded-xl px-3 py-2">
      {texto && <p className="text-[11px] text-[var(--color-ink-3)]">{texto}</p>}
      {payload.map((p) => (
        <p key={p.name} className="tnum text-[13px] font-medium" style={{ color: p.color }}>
          {p.name}: {Number.isInteger(p.value) ? num(p.value, 0) : num(p.value)}
        </p>
      ))}
    </div>
  );
}

type WaterfallDato = {
  etiqueta: string; v: number; p: number;
  codigo?: string; rango?: string; valor?: string;
  descripcion?: string; diagnostico?: string;
};

function CajaWaterfall({ active, payload }: {
  active?: boolean;
  payload?: { payload?: WaterfallDato }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  const isPos = d.v >= 0;
  const signo = isPos ? "+" : "−";
  const puntosFmt = `${signo}${Math.abs(d.v).toFixed(2)} pts`;
  const color = d.p >= 50 ? "#b083e8" : "#e59f5e";

  return (
    <div className="glass rounded-xl p-3.5 shadow-2xl border border-[rgba(255,255,255,.12)] max-w-[310px] backdrop-blur-md pointer-events-none">
      <div className="flex items-center justify-between gap-2 pb-2 border-b border-[rgba(255,255,255,.08)]">
        <div className="flex items-center gap-1.5">
          <span className="text-[13px] font-semibold text-white tracking-tight">{d.etiqueta}</span>
          {d.codigo && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[rgba(255,255,255,.08)] text-[var(--color-ink-3)]">
              {d.codigo}
            </span>
          )}
        </div>
        <span className="tnum text-[13px] font-bold" style={{ color }}>
          {puntosFmt}
        </span>
      </div>

      <div className="mt-2 space-y-1.5 text-[11.5px]">
        {d.rango && (
          <div className="flex items-center justify-between text-[var(--color-ink-3)]">
            <span>Rango teórico:</span>
            <span className="font-mono text-[var(--color-ink-2)]">{d.rango}</span>
          </div>
        )}
        {d.valor && (
          <div className="flex items-center justify-between text-[var(--color-ink-3)]">
            <span>Métrica observada:</span>
            <span className="font-medium text-white">{d.valor}</span>
          </div>
        )}
        {d.descripcion && (
          <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--color-ink-2)] pt-1.5 border-t border-[rgba(255,255,255,.06)]">
            {d.descripcion}
          </p>
        )}
        {d.diagnostico && (
          <p className="mt-1 text-[11px] leading-relaxed font-medium text-[#c4b5fd] bg-[rgba(176,131,232,.10)] rounded-md px-2 py-1 border border-[rgba(176,131,232,.15)]">
            {d.diagnostico}
          </p>
        )}
      </div>
    </div>
  );
}

export type DeteccionMarca = {
  mes: string;                       // "YYYY-MM" dentro de la serie
  direccion: "deterioro" | "mejora";
  texto?: string;
  senales?: EpisodioSenal[];
};

const COLOR_DETECCION = { deterioro: "var(--color-warm)", mejora: "var(--color-success)" } as const;

export type CaminoMarca = {
  mes: string;                       // "YYYY-MM" dentro de la serie (origen)
  scoreProyectado: number;
  familia?: "salud" | "circulante" | string;
};

const COLOR_CAMINO = { salud: "var(--color-warm)", circulante: "#dfb631" } as const;

function CajaDeteccion({ deteccion, camino, active, payload, label }: {
  deteccion?: DeteccionMarca;
  camino?: CaminoMarca;
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  const base = <Caja active={active} payload={payload} label={label} />;
  if (camino && label === camino.mes) {
    return (
      <div className="space-y-1">
        {base}
        <div className="glass rounded-xl px-3 py-2 max-w-[280px]">
          <p className="text-[11px] font-semibold text-[var(--color-warm)]">Si no hacías nada</p>
          <p className="mt-0.5 tnum text-[11px] text-[var(--color-ink-2)]">
            proyectado a 6 m, no es un hecho: {num(camino.scoreProyectado)}
          </p>
        </div>
      </div>
    );
  }
  if (!deteccion || label !== deteccion.mes) return base;
  const color = COLOR_DETECCION[deteccion.direccion as keyof typeof COLOR_DETECCION] ?? "#e59f5e";
  return (
    <div className="space-y-1">
      {base}
      <div className="glass rounded-xl px-3 py-2 max-w-[280px]">
        <p className="text-[11px] font-semibold" style={{ color }}>
          Detección de {deteccion.direccion}
        </p>
        {deteccion.senales?.map((s: EpisodioSenal) => (
          <p key={s.senal} className="tnum text-[11px] text-[var(--color-ink-3)]">
            {s.senal}: {num(s.antes)} → {num(s.en_deteccion)}
          </p>
        ))}
      </div>
    </div>
  );
}

/** Trayectoria de 24 meses. El patrón de Moody's EDF-X: la historia, no el gauge. */
export function Trayectoria({ datos, deteccion, camino, comparador, altura = 220 }: {
  datos: Punto[];
  deteccion?: DeteccionMarca;
  camino?: CaminoMarca;
  comparador?: { nombre: string; datos: Punto[] };
  altura?: number;
}) {
  const gradientId = `grad-${useId().replace(/:/g, "")}`;
  const merged = datos.map((d, i) => ({
    mes: d.mes, score: d.score,
    ...(comparador ? { otro: comparador.datos[i]?.score } : {}),
  }));
  const detPunto = deteccion ? datos.find((d) => d.mes === deteccion.mes) : undefined;
  const camPunto = camino ? datos.find((d) => d.mes === camino.mes) : undefined;
  const colorCam = COLOR_CAMINO[(camino?.familia === "circulante" ? "circulante" : "salud")];

  // El corte del degradado, en % del ancho, es el mes de la detección.
  const trazoId = `trazo-${gradientId}`;
  const areaId = `area-${gradientId}`;
  const iDet = deteccion ? datos.findIndex((d) => d.mes === deteccion.mes) : -1;
  const hayCorte = iDet > 0 && datos.length > 1;
  const corte = hayCorte ? Math.round((iDet / (datos.length - 1)) * 100) : 100;
  const colorAntes = "#b083e8";
  const colorDespues = hayCorte
    ? (deteccion!.direccion === "deterioro" ? "#e59f5e" : "#80efa2")
    : colorAntes;
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <AreaChart data={merged} margin={{ top: 20, right: 12, bottom: 0, left: -18 }}>
        <defs>
          {/* El color va a lo largo del tiempo, no de la altura: la serie es
              morada hasta el mes en que saltó la detección y toma el color del
              episodio a partir de ahí. El corte cae exactamente en ese mes. */}
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={colorAntes} stopOpacity={0.26} />
            <stop offset="100%" stopColor={colorAntes} stopOpacity={0} />
          </linearGradient>
          <linearGradient id={trazoId} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"            stopColor={colorAntes} />
            <stop offset={`${corte}%`}   stopColor={colorAntes} />
            <stop offset={`${corte}%`}   stopColor={colorDespues} />
            <stop offset="100%"          stopColor={colorDespues} />
          </linearGradient>
          <linearGradient id={areaId} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"            stopColor={colorAntes} stopOpacity={0.22} />
            <stop offset={`${corte}%`}   stopColor={colorAntes} stopOpacity={0.22} />
            <stop offset={`${corte}%`}   stopColor={colorDespues} stopOpacity={0.24} />
            <stop offset="100%"          stopColor={colorDespues} stopOpacity={0.06} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(176,131,232,.10)" vertical={false} />
        <XAxis dataKey="mes" tickFormatter={mesCorto} tick={EJE} tickLine={false} axisLine={{ stroke: "rgba(176,131,232,.22)" }} interval={3} />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={EJE} tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<CajaDeteccion deteccion={deteccion} camino={camino} />} />
        <ReferenceLine y={60} stroke="#dfb631" strokeOpacity={0.42} strokeDasharray="3 3"
          label={{ value: "umbral 60", position: "insideBottomLeft", fontSize: 9.5, fill: "rgba(223,182,49,.62)", offset: 6 }} />
        <Area type="monotone" dataKey="score" name="Score" stroke={hayCorte ? `url(#${trazoId})` : colorAntes} strokeWidth={2.2}
          fill={`url(#${hayCorte ? areaId : gradientId})`} dot={false} isAnimationActive={false} />
        {comparador && (
          <Line type="monotone" dataKey="otro" name={comparador.nombre} stroke="#e59f5e" strokeWidth={2.2} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
        )}
        {deteccion && (
          <ReferenceLine x={deteccion.mes} stroke="rgba(255,255,255,.72)" strokeDasharray="4 3"
            label={{
              value: `Aquí detectamos señales de ${deteccion.direccion}`,
              position: "insideTopLeft", fontSize: 10, fill: "rgba(255,255,255,.82)",
            }} />
        )}
        {detPunto && (
          <ReferenceDot x={detPunto.mes} y={detPunto.score} r={9}
            fill="#ffffff" fillOpacity={0.16} stroke="none" />
        )}
        {detPunto && (
          <ReferenceDot x={detPunto.mes} y={detPunto.score} r={5}
            fill="#ffffff" stroke="#0a0810" strokeWidth={2} />
        )}
        {camPunto && (
          <ReferenceDot x={camPunto.mes} y={camPunto.score} r={5.5}
            fill="rgba(10,8,16,0)" stroke={colorCam} strokeWidth={2} />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Waterfall aditivo: las contribuciones suman exactamente el score. */
export function Waterfall({ drivers, altura = 240 }: { drivers: Driver[]; altura?: number }) {
  const datos = drivers.map((d) => ({
    etiqueta: d.etiqueta,
    v: d.contribucion,
    p: d.p_peer,
    codigo: d.codigo,
    rango: d.rango,
    valor: d.valor,
    descripcion: d.descripcion,
    diagnostico: d.diagnostico,
  }));
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart data={datos} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="etiqueta" tick={{ ...EJE, fontSize: 12 }} width={168} tickLine={false} axisLine={false} />
        <Tooltip content={<CajaWaterfall />} cursor={{ fill: "rgba(255,255,255,.05)" }} />
        <Bar dataKey="v" name="Puntos" radius={[0, 4, 4, 0]} barSize={18} isAnimationActive={false}>
          {datos.map((d, i) => (
            <Cell key={i} fill={d.p >= 50 ? "#b083e8" : "#e59f5e"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function Sparkline({ datos, w = 92, h = 26 }: { datos: Punto[]; w?: number; h?: number }) {
  const vals = datos.map((d) => d.score);
  if (vals.length === 0) return null;
  const min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
  const pasos = Math.max(1, vals.length - 1);   // con un solo punto, solo el círculo final
  const pts = vals.map((v, i) => `${(i / pasos) * w},${h - ((v - min) / span) * (h - 4) - 2}`).join(" ");
  const color = banda(vals[vals.length - 1]).color;
  return (
    <svg width={w} height={h} className="overflow-visible" aria-hidden>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={w} cy={h - ((vals[vals.length - 1] - min) / span) * (h - 4) - 2} r={2.2} fill={color} />
    </svg>
  );
}

/** Histograma de scores por tramos de 10. Cada barra lleva el color de su banda. */
export function Histograma({ datos, altura = 180 }: { datos: Array<{ bucket: number; count: number }>; altura?: number }) {
  const filas = datos.map((d) => ({ tramo: `${d.bucket}–${d.bucket + 10}`, n: d.count, color: banda(d.bucket + 5).color }));
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart data={filas} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid stroke="rgba(176,131,232,.10)" vertical={false} />
        <XAxis dataKey="tramo" tick={EJE} tickLine={false} axisLine={{ stroke: "rgba(255,255,255,.12)" }} interval={0} />
        <YAxis tick={EJE} tickLine={false} axisLine={false} width={44} allowDecimals={false} />
        <Tooltip content={<Caja />} cursor={{ fill: "rgba(255,255,255,.05)" }} />
        <Bar dataKey="n" name="Empresas" radius={[4, 4, 0, 0]} barSize={26} isAnimationActive={false}>
          {filas.map((f, i) => <Cell key={i} fill={f.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
