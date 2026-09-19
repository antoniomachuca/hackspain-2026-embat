import { num, mesCorto } from "@/lib/format";
import type { Punto } from "@/lib/data";

/**
 * Histórico + proyección a 12 meses, al modo de las fichas de cotización:
 * línea sólida hasta hoy, punto de corte, y abanico punteado hasta los tres
 * escenarios. El cono dice la incertidumbre; los tres puntos, su rango.
 *
 * El eje vertical se ajusta al recorrido real de los datos, no a 0–100: con
 * el dominio completo la serie se aplasta en una franja y el gráfico miente
 * sobre cuánto se ha movido.
 */
export function Prevision({
  datos, momentum, meses = 12, alto = 330, ancho = 1120,
}: { datos: Punto[]; momentum: number; meses?: number; alto?: number; ancho?: number }) {
  const hoy = datos[datos.length - 1].score;

  const deriva = momentum * 14;
  const central = clamp(hoy + deriva);
  const amplitud = 9 + Math.abs(momentum) * 13;
  const arriba = clamp(central + amplitud);
  const abajo = clamp(central - amplitud);

  const padL = 6, padR = 232, padT = 20, padB = 34;
  const w = ancho - padL - padR;
  const h = alto - padT - padB;
  const nHist = datos.length;
  const total = nHist - 1 + meses;

  // Dominio vertical ajustado, con un respiro del 12 % a cada lado
  const valores = [...datos.map((d) => d.score), arriba, abajo];
  const vMin = Math.min(...valores), vMax = Math.max(...valores);
  const margen = Math.max(6, (vMax - vMin) * 0.12);
  const lo = Math.max(0, vMin - margen), hi = Math.min(100, vMax + margen);

  const x = (i: number) => padL + (i / total) * w;
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * h;

  const xHoy = x(nHist - 1);
  const xFin = x(total);
  const yHoy = y(hoy);

  const linea = datos.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.score).toFixed(1)}`).join(" ");
  const cono = `M${xHoy},${yHoy} L${xFin},${y(arriba)} L${xFin},${y(abajo)} Z`;

  // Cada etiqueta ocupa dos líneas: se separan para que no se pisen nunca
  const HUECO = 54;
  // Semánticos inversos oficiales de Embat: éxito, aviso y peligro.
  const crudos = [
    { k: "Alto",  v: arriba, yy: y(arriba),  c: "#80efa2" },
    { k: "Medio", v: central, yy: y(central), c: "#dfb631" },
    { k: "Bajo",  v: abajo,  yy: y(abajo),   c: "#e5775b" },
  ];
  const etiquetas = separar(crudos, HUECO, padT + 12, alto - padB - 12);

  // Rejilla: tres líneas repartidas por el dominio real
  const guias = [lo + (hi - lo) * 0.25, lo + (hi - lo) * 0.5, lo + (hi - lo) * 0.75];

  return (
    <div className="w-full">
      <div className="flex items-baseline gap-2.5">
        <span className="tnum text-[26px] font-semibold leading-none" style={{ color: "var(--color-purple)" }}>
          {num(central)}
        </span>
        <span className="text-[12px] text-[var(--color-ink-3)]">/ 100</span>
      </div>
      <p className="mt-1 text-[12px] text-[var(--color-ink-3)]">
        Proyección a {meses} meses · escenario central
      </p>

      <svg viewBox={`0 0 ${ancho} ${alto}`} className="-mx-6 mt-2 w-[calc(100%+3rem)]" role="img"
        aria-label={`Histórico de ${nHist} meses y proyección a ${meses} meses`}>
        <defs>
          <linearGradient id="prev-cono" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#80efa2" stopOpacity="0.16" />
            <stop offset="50%" stopColor="#dfb631" stopOpacity="0.10" />
            <stop offset="100%" stopColor="#e5775b" stopOpacity="0.16" />
          </linearGradient>
          <linearGradient id="prev-bajo" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#b083e8" stopOpacity="0.20" />
            <stop offset="100%" stopColor="#b083e8" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="prev-eje" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#80efa2" />
            <stop offset="50%" stopColor="#dfb631" />
            <stop offset="100%" stopColor="#e5775b" />
          </linearGradient>
        </defs>

        {guias.map((g, i) => (
          <line key={i} x1={padL} x2={xFin} y1={y(g)} y2={y(g)} stroke="rgba(255,255,255,.05)" />
        ))}

        <path d={`${linea} L${xHoy},${padT + h} L${padL},${padT + h} Z`} fill="url(#prev-bajo)" />
        <path d={cono} fill="url(#prev-cono)" />
        <path d={linea} fill="none" stroke="#b083e8" strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />

        {crudos.map((e) => (
          <line key={e.k} x1={xHoy} y1={yHoy} x2={xFin} y2={e.yy}
            stroke={e.c} strokeOpacity={e.k === "Medio" ? 0.85 : 0.55}
            strokeWidth={e.k === "Medio" ? 1.8 : 1.4} strokeDasharray="4 5" />
        ))}

        <line x1={xFin} y1={y(arriba)} x2={xFin} y2={y(abajo)} stroke="url(#prev-eje)" strokeWidth="1.8" />

        <circle cx={xHoy} cy={yHoy} r="6.5" fill="#fff" />
        {crudos.map((e) => (
          <circle key={e.k} cx={xFin} cy={e.yy} r={e.k === "Medio" ? 7 : 5.5} fill={e.c} />
        ))}

        {/* Etiquetas, con guía al punto cuando se han tenido que desplazar */}
        {etiquetas.map((e) => {
          const d = e.v - hoy;
          const movida = Math.abs(e.yy - e.crudo) > 2;
          return (
            <g key={e.k}>
              {movida && (
                <path d={`M${xFin + 7},${e.crudo} L${xFin + 15},${e.yy - 5}`}
                  stroke={e.c} strokeOpacity="0.35" strokeWidth="1" fill="none" />
              )}
              <text x={xFin + 20} y={e.yy - 4} fill={e.c} fontSize="18" fontWeight="500">
                {e.k} · {num(e.v)}
              </text>
              <text x={xFin + 20} y={e.yy + 19} fontSize="16" fill={e.c} fillOpacity="0.72">
                {d >= 0 ? "+" : "−"}{num(Math.abs(d))} pts
              </text>
            </g>
          );
        })}

        <g>
          <rect x={xHoy - 66} y={yHoy - 46} width="120" height="32" rx="10" fill="#17112a" stroke="rgba(255,255,255,.12)" />
          <text x={xHoy - 6} y={yHoy - 25} fill="#fff" fontSize="16.5" textAnchor="middle">{num(hoy)} hoy</text>
        </g>

        <text x={padL} y={alto - 8} fill="#787d96" fontSize="15">{mesCorto(datos[0].mes)}</text>
        <text x={xHoy} y={alto - 8} fill="#787d96" fontSize="15" textAnchor="middle">{mesCorto(datos[nHist - 1].mes)}</text>
        <text x={xFin} y={alto - 8} fill="#787d96" fontSize="15" textAnchor="middle">+{meses}m</text>
      </svg>
    </div>
  );
}

const clamp = (v: number) => Math.max(1, Math.min(99, Math.round(v * 10) / 10));

/** Separa etiquetas que se solaparían, respetando el orden y los bordes. */
function separar<T extends { yy: number }>(items: T[], hueco: number, min: number, max: number) {
  const out = items.map((i) => ({ ...i, crudo: i.yy }));
  out.sort((a, b) => a.yy - b.yy);
  for (let i = 1; i < out.length; i++) {
    if (out[i].yy - out[i - 1].yy < hueco) out[i].yy = out[i - 1].yy + hueco;
  }
  const exceso = out[out.length - 1].yy - max;
  if (exceso > 0) for (const o of out) o.yy -= exceso;
  if (out[0].yy < min) {
    const falta = min - out[0].yy;
    for (const o of out) o.yy += falta;
  }
  return out;
}
