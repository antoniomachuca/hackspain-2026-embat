"use client";
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip,
  ReferenceLine, ReferenceDot, BarChart, Bar, Cell, CartesianGrid, Area, AreaChart,
} from "recharts";
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
          {p.name}: {num(p.value)}
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
};

function CajaDeteccion({ deteccion, active, payload, label }: {
  deteccion?: DeteccionMarca;
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  const base = <Caja active={active} payload={payload} label={label} />;
  if (!deteccion || label !== deteccion.mes) return base;
  const color = COLOR_DETECCION[deteccion.direccion as keyof typeof COLOR_DETECCION] ?? "#e59f5e";
  return (
    <div className="space-y-1">
      {base}
      <div className="glass rounded-xl px-3 py-2 max-w-[280px]">
        <p className="text-[11px] font-semibold" style={{ color }}>
          Detección de {deteccion.direccion}
        </p>
        {deteccion.texto && (
          <p className="mt-0.5 text-[11px] leading-snug text-[var(--color-ink-2)]">{deteccion.texto}</p>
        )}
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
  const merged = datos.map((d, i) => ({
    mes: d.mes, score: d.score,
    ...(comparador ? { otro: comparador.datos[i]?.score } : {}),
  }));
  const detPunto = deteccion ? datos.find((d) => d.mes === deteccion.mes) : undefined;
  const colorDet = deteccion
    ? COLOR_DETECCION[deteccion.direccion] ?? "var(--color-warm)"
    : "var(--color-warm)";
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <AreaChart data={merged} margin={{ top: 20, right: 12, bottom: 0, left: -18 }}>
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#b083e8" stopOpacity={0.30} />
            <stop offset="100%" stopColor="#b083e8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
        <XAxis dataKey="mes" tickFormatter={mesCorto} tick={EJE} tickLine={false} axisLine={{ stroke: "rgba(255,255,255,.12)" }} interval={3} />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={EJE} tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<CajaDeteccion deteccion={deteccion} />} />
        <ReferenceLine y={60} stroke="rgba(255,255,255,.14)" strokeDasharray="3 3" />
        <Area type="monotone" dataKey="score" name="Score" stroke="#b083e8" strokeWidth={2.2} fill="url(#grad)" dot={false} />
        {comparador && (
          <Line type="monotone" dataKey="otro" name={comparador.nombre} stroke="#e59f5e" strokeWidth={2.2} strokeDasharray="4 3" dot={false} />
        )}
        {deteccion && (
          <ReferenceLine x={deteccion.mes} stroke={colorDet} strokeDasharray="4 3"
            label={{
              value: `Aquí detectamos señales de ${deteccion.direccion}`,
              position: "insideTopLeft", fontSize: 10, fill: colorDet,
            }} />
        )}
        {detPunto && (
          <ReferenceDot x={detPunto.mes} y={detPunto.score} r={5}
            fill={colorDet} stroke="#0a0810" strokeWidth={2} />
        )}
        {camino && (
          <ReferenceDot x={camino.mes} y={camino.scoreProyectado} r={5.5}
            fill="rgba(10,8,16,0)" stroke="var(--color-warm)" strokeWidth={2} />
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
        <Bar dataKey="v" name="Puntos" radius={[0, 4, 4, 0]} barSize={18}>
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
  const min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${h - ((v - min) / span) * (h - 4) - 2}`).join(" ");
  const color = banda(vals[vals.length - 1]).color;
  return (
    <svg width={w} height={h} className="overflow-visible" aria-hidden>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={w} cy={h - ((vals[vals.length - 1] - min) / span) * (h - 4) - 2} r={2.2} fill={color} />
    </svg>
  );
}
