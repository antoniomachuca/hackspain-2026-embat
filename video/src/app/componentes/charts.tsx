import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ReferenceLine, ReferenceDot, BarChart, Bar, Cell, CartesianGrid, Area, AreaChart,
} from "recharts";
import { mesCorto, num, banda } from "../lib/format";
import type { Punto, Driver } from "../lib/data";

/**
 * Los mismos gráficos que la app, con dos cambios obligados por el vídeo:
 *
 *   · sin `ResponsiveContainer`. Mide con un ResizeObserver, que en un render
 *     sin interacción llega tarde y deja el primer fotograma en blanco. Aquí
 *     el ancho se pasa a mano, que además es constante en todo el vídeo.
 *   · sin la animación de recharts, que va por reloj. El movimiento lo manda
 *     `progreso` ∈ [0,1], que sale del frame: así cada fotograma es puro y
 *     el render sale idéntico a la previsualización.
 *
 * El resto —colores, márgenes, grosores, ejes— es literal.
 */

const EJE = { fontSize: 11, fill: "#afafbb" };

/** Trayectoria de 24 meses. El patrón de Moody's EDF-X: la historia, no el gauge. */
export function Trayectoria({ datos, alerta, comparador, altura = 220, ancho = 840, progreso = 1 }: {
  datos: Punto[]; alerta?: string; comparador?: { nombre: string; datos: Punto[] };
  altura?: number; ancho?: number; progreso?: number;
}) {
  // La línea se dibuja mes a mes; el eje no se mueve, para que el trazo avance
  // sobre una rejilla quieta en vez de comprimirse a cada fotograma.
  const visibles = Math.max(2, Math.round(datos.length * progreso));
  const merged = datos.map((d, i) => ({
    mes: d.mes,
    score: i < visibles ? d.score : null,
    ...(comparador ? { otro: i < visibles ? comparador.datos[i]?.score : null } : {}),
  }));
  const alertaPunto = alerta ? datos.find((d) => d.mes === alerta) : undefined;
  const alertaVisible = alertaPunto && datos.indexOf(alertaPunto) < visibles;
  return (
    <AreaChart width={ancho} height={altura} data={merged} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
      <defs>
        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#b083e8" stopOpacity={0.30} />
          <stop offset="100%" stopColor="#b083e8" stopOpacity={0} />
        </linearGradient>
      </defs>
      <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
      <XAxis dataKey="mes" tickFormatter={mesCorto} tick={EJE} tickLine={false} axisLine={{ stroke: "rgba(255,255,255,.12)" }} interval={3} />
      <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={EJE} tickLine={false} axisLine={false} width={44} />
      <Tooltip content={() => null} />
      <ReferenceLine y={45} stroke="rgba(255,255,255,.14)" strokeDasharray="3 3" />
      <Area type="monotone" dataKey="score" name="Score" stroke="#b083e8" strokeWidth={2.2} fill="url(#grad)" dot={false} isAnimationActive={false} connectNulls={false} />
      {comparador && (
        <Line type="monotone" dataKey="otro" name={comparador.nombre} stroke="#e59f5e" strokeWidth={2.2} strokeDasharray="4 3" dot={false} isAnimationActive={false} connectNulls={false} />
      )}
      {alertaVisible && (
        <ReferenceDot x={alertaPunto!.mes} y={alertaPunto!.score} r={5}
          fill="#e59f5e" stroke="#0a0810" strokeWidth={2} />
      )}
    </AreaChart>
  );
}

/** Waterfall aditivo: las contribuciones suman exactamente el score. */
export function Waterfall({ drivers, altura = 240, ancho = 840, progreso = 1 }: {
  drivers: Driver[]; altura?: number; ancho?: number; progreso?: number;
}) {
  // Escalonado: cada barra arranca un poco después que la anterior, y el eje
  // de categorías se queda fijo porque el dominio numérico no depende de él.
  const n = drivers.length;
  const datos = drivers.map((d, i) => {
    const t = Math.max(0, Math.min(1, progreso * (n + 2) - i));
    return { etiqueta: d.etiqueta, v: Math.round(d.contribucion * suave(t) * 100) / 100, p: d.p_peer };
  });
  const tope = Math.max(...drivers.map((d) => d.contribucion)) * 1.02;
  return (
    <BarChart width={ancho} height={altura} data={datos} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }}>
      <XAxis type="number" hide domain={[0, tope]} />
      <YAxis type="category" dataKey="etiqueta" tick={{ ...EJE, fontSize: 12 }} width={168} tickLine={false} axisLine={false} />
      <Bar dataKey="v" name="Puntos" radius={[0, 4, 4, 0]} barSize={18} isAnimationActive={false}>
        {datos.map((d, i) => (
          <Cell key={i} fill={d.p >= 50 ? "#b083e8" : "#e59f5e"} />
        ))}
      </Bar>
    </BarChart>
  );
}

export function Sparkline({ datos, w = 92, h = 26, progreso = 1 }: { datos: Punto[]; w?: number; h?: number; progreso?: number }) {
  const vals = datos.map((d) => d.score);
  const min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${h - ((v - min) / span) * (h - 4) - 2}`).join(" ");
  const color = banda(vals[vals.length - 1]).color;
  return (
    <svg width={w} height={h} className="overflow-visible" aria-hidden>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - progreso} />
      <circle cx={w} cy={h - ((vals[vals.length - 1] - min) / span) * (h - 4) - 2} r={2.2} fill={color}
        opacity={progreso > 0.98 ? 1 : 0} />
    </svg>
  );
}

const suave = (t: number) => (t <= 0 ? 0 : t >= 1 ? 1 : 1 - Math.pow(1 - t, 3));
