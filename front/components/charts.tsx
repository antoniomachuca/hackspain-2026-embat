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
  return (
    <div className="glass rounded-xl px-3 py-2">
      <p className="text-[11px] text-[var(--color-ink-3)]">{mesCorto(label)}</p>
      {payload.map((p: any) => (
        <p key={p.name} className="tnum text-[13px] font-medium" style={{ color: p.color }}>
          {p.name}: {num(p.value)}
        </p>
      ))}
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
  const datos = drivers.map((d) => ({ etiqueta: d.etiqueta, v: d.contribucion, p: d.p_peer }));
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart data={datos} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="etiqueta" tick={{ ...EJE, fontSize: 12 }} width={168} tickLine={false} axisLine={false} />
        <Tooltip content={<Caja />} cursor={{ fill: "rgba(255,255,255,.05)" }} />
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
