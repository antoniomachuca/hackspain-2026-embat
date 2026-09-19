"use client";
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip,
  ReferenceLine, ReferenceDot, BarChart, Bar, Cell, CartesianGrid, Area, AreaChart,
} from "recharts";
import { mesCorto, num, banda } from "@/lib/format";
import type { Punto, Driver } from "@/lib/data";

const EJE = { fontSize: 11, fill: "#afafbb" };

function Caja({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const texto = typeof label === "string" && label.includes("-") ? mesCorto(label) : label;
  return (
    <div className="glass rounded-xl px-3 py-2">
      {texto && <p className="text-[11px] text-[var(--color-ink-3)]">{texto}</p>}
      {payload.map((p: any) => (
        <p key={p.name} className="tnum text-[13px] font-medium" style={{ color: p.color }}>
          {p.name}: {Number.isInteger(p.value) ? num(p.value, 0) : num(p.value)}
        </p>
      ))}
    </div>
  );
}

function CajaWaterfall({ active, payload }: any) {
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

/** Trayectoria de 24 meses. El patrón de Moody's EDF-X: la historia, no el gauge. */
export function Trayectoria({ datos, alerta, comparador, altura = 220 }: {
  datos: Punto[]; alerta?: string; comparador?: { nombre: string; datos: Punto[] }; altura?: number;
}) {
  const merged = datos.map((d, i) => ({
    mes: d.mes, score: d.score,
    ...(comparador ? { otro: comparador.datos[i]?.score } : {}),
  }));
  const alertaPunto = alerta ? datos.find((d) => d.mes === alerta) : undefined;
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <AreaChart data={merged} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#b083e8" stopOpacity={0.30} />
            <stop offset="100%" stopColor="#b083e8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
        <XAxis dataKey="mes" tickFormatter={mesCorto} tick={EJE} tickLine={false} axisLine={{ stroke: "rgba(255,255,255,.12)" }} interval={3} />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={EJE} tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<Caja />} />
        <ReferenceLine y={45} stroke="rgba(255,255,255,.14)" strokeDasharray="3 3" />
        <Area type="monotone" dataKey="score" name="Score" stroke="#b083e8" strokeWidth={2.2} fill="url(#grad)" dot={false} />
        {comparador && (
          <Line type="monotone" dataKey="otro" name={comparador.nombre} stroke="#e59f5e" strokeWidth={2.2} strokeDasharray="4 3" dot={false} />
        )}
        {alertaPunto && (
          <ReferenceDot x={alertaPunto.mes} y={alertaPunto.score} r={5}
            fill="#e59f5e" stroke="#0a0810" strokeWidth={2} />
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
        <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
        <XAxis dataKey="tramo" tick={EJE} tickLine={false} axisLine={{ stroke: "rgba(255,255,255,.12)" }} interval={0} />
        <YAxis tick={EJE} tickLine={false} axisLine={false} width={44} allowDecimals={false} />
        <Tooltip content={<Caja />} cursor={{ fill: "rgba(255,255,255,.05)" }} />
        <Bar dataKey="n" name="Empresas" radius={[4, 4, 0, 0]} barSize={26}>
          {filas.map((f, i) => <Cell key={i} fill={f.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
