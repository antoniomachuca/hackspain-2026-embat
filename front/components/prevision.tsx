"use client";
import { useState } from "react";
import { num, mesCorto } from "@/lib/format";
import type { Punto, PuntoPeer, Reparto, Inflexion } from "@/lib/data";

/**
 * Histórico + proyección a 12 meses, al modo de las fichas de cotización:
 * línea sólida hasta hoy, punto de corte, y abanico punteado hasta los tres
 * escenarios. El cono dice la incertidumbre; los tres puntos, su rango.
 *
 * El eje vertical se ajusta al recorrido real de los datos, no a 0–100: con
 * el dominio completo la serie se aplasta en una franja y el gráfico miente
 * sobre cuánto se ha movido.
 *
 * Sobre ese esqueleto van tres capas más, todas colgadas del MISMO eje X. Si
 * se rompe esa alineación el dibujo deja de ser comparable consigo mismo:
 *
 *   · la mediana de su cuartil de tamaño — la línea que baja sola no es lo
 *     mismo que la línea que baja con todo su cuartil detrás;
 *   · la marca de la última inflexión: el mes en que cambió de régimen, con
 *     el reparto entre lo que es la empresa y lo que es el entorno;
 *   · la tira de abajo, mes a mes, partida en cuánta tendencia y cuánto
 *     bache hay en el movimiento: un pico que revierte no es una caída.
 *
 * Las tres son opcionales. Mientras el motor no las sirva, el gráfico es
 * exactamente el que era.
 */
const RANGOS = [6, 12, 24] as const;

export function Prevision({
  datos: datosTodos, momentum, proyeccion, peer, datosPeer: peerTodos, reparto: repartoTodo, inflexion,
  meses = 12, alto = 320, ancho = 1120,
}: {
  datos: Punto[];
  momentum: number;
  proyeccion?: { alto: number[]; medio: number[]; bajo: number[] } | null;
  peer?: { etiqueta: string; n: number };
  datosPeer?: PuntoPeer[];
  reparto?: Reparto[];
  inflexion?: Inflexion;
  meses?: number; alto?: number; ancho?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  // La ventana de histórico la elige quien mira; el horizonte sigue siendo 12 meses.
  const [rango, setRango] = useState<(typeof RANGOS)[number]>(24);
  const datos = datosTodos.slice(-rango);
  const datosPeer = peerTodos?.slice(-rango);
  const reparto = repartoTodo?.slice(-rango);
  if (datos.length === 0) {
    return <p className="py-8 text-center text-[12px] text-[var(--color-ink-4)]">No hay histórico suficiente para dibujar la previsión.</p>;
  }
  const hoy = datos[datos.length - 1].score;

  // Con previsión estructural el camino lo dicta el motor: proyecta la cuenta
  // y puntúa cada mes con el mismo score de producción. Sin ella, lo único
  // honesto que queda es prolongar la inercia observada.
  const completa = (v?: number[]) => Array.isArray(v) && v.length === meses;
  const estructural = !!proyeccion && completa(proyeccion.alto) && completa(proyeccion.medio) && completa(proyeccion.bajo);

  // Sin estructural la proyección no es una recta: se mueve con la volatilidad
  // observada y cada escenario tiene su forma de llegar. Alto remonta pronto
  // (ease-out), medio sigue la inercia, bajo aguanta y se desploma al final.
  const saltos = datos.slice(1).map((d, i) => d.score - datos[i].score);
  const mediaSalto = saltos.reduce((a, b) => a + b, 0) / (saltos.length || 1);
  const vol = Math.min(4.5, Math.sqrt(saltos.reduce((a, b) => a + (b - mediaSalto) ** 2, 0) / (saltos.length || 1)));

  // Las sendas del motor se pegan al último punto observado y se pintan tal
  // cual: si un mes el pesimista queda por encima del central, así se dibuja.
  // Reordenarlas a mano sería maquillar el resultado.
  const deriva = momentum * 14;
  const inercia = clamp(hoy + deriva);
  const amplitud = 9 + Math.abs(momentum) * 13;
  const sendas = estructural
    ? {
        Alto:  [hoy, ...proyeccion!.alto.map(clamp)],
        Medio: [hoy, ...proyeccion!.medio.map(clamp)],
        Bajo:  [hoy, ...proyeccion!.bajo.map(clamp)],
      }
    : {
        Alto:  senda(hoy, clamp(inercia + amplitud), meses, 0.62, vol, 9001),
        Medio: senda(hoy, inercia,                   meses, 0.92, vol, 9002),
        Bajo:  senda(hoy, clamp(inercia - amplitud), meses, 1.45, vol, 9003),
      };
  const arriba = sendas.Alto[meses];
  const central = sendas.Medio[meses];
  const abajo = sendas.Bajo[meses];

  // El margen inferior guarda sitio para la tira; el área de trazado no cambia.
  const padL = 56, padR = 210, padT = 20, padB = 44;
  const w = ancho - padL - padR;
  const h = alto - padT - padB;
  const nHist = datos.length;
  const total = nHist - 1 + meses;

  // Dominio vertical ajustado, con un respiro del 12 % a cada lado. Entra
  // también la mediana del cuartil: si se calcula solo con la empresa, la
  // línea de referencia se sale del lienzo justo cuando más se separan.
  const valores = [
    ...datos.map((d) => d.score),
    ...(datosPeer?.map((p) => p.mediana) ?? []),
    ...sendas.Alto, ...sendas.Medio, ...sendas.Bajo,
  ];
  const vMin = Math.min(...valores), vMax = Math.max(...valores);
  const margen = Math.max(6, (vMax - vMin) * 0.12);
  const lo = Math.max(0, vMin - margen), hi = Math.min(100, vMax + margen);

  const x = (i: number) => padL + (i / total) * w;
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * h;

  const xHoy = x(nHist - 1);
  const xFin = x(total);
  const yHoy = y(hoy);
  const paso = w / total;

  const linea = datos.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.score).toFixed(1)}`).join(" ");

  const pts = (vs: number[]) => vs.map((v, k) => `${x(nHist - 1 + k).toFixed(1)},${y(v).toFixed(1)}`);
  const traza = (vs: number[]) => `M${pts(vs).join(" L")}`;
  const cono = `M${pts(sendas.Alto).join(" L")} L${pts(sendas.Bajo).reverse().join(" L")} Z`;

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

  // ── La marca de inflexión. Solo la última: es la que importa hoy, y dos
  //    marcas en el mismo dibujo obligan a leerlo en vez de verlo.
  const iInf = inflexion ? datos.findIndex((d) => d.mes === inflexion.mes) : -1;
  const marca = iInf >= 0 && inflexion
    ? {
        x: x(iInf), y: y(datos[iInf].score),
        c: inflexion.direccion === "mejora" ? "#b083e8" : "#e59f5e",
        texto: `${inflexion.direccion === "mejora" ? "se anima" : "empieza a torcerse"} · ${mesCorto(inflexion.mes)}`,
        // Se ancla al lado que tiene sitio. La guía ya dice a qué mes se refiere.
        izquierda: x(iInf) - padL > 200,
      }
    : null;

  const hBase = hover === null ? null : datos[hover];
  const hPeer = hover === null ? null : datosPeer?.[hover];
  const hRep = hover === null ? null : reparto?.[hover];

  const capas = [
    `Histórico de ${nHist} meses y proyección a ${meses} meses`,
    datosPeer && `mediana de ${peer?.etiqueta.toLowerCase() ?? "su cuartil"} de fondo`,
  ].filter(Boolean).join(", ");

  return (
    <div className="w-full">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2.5">
            <span className="tnum text-[26px] font-semibold leading-none" style={{ color: "var(--color-purple)" }}>
              {num(central)}
            </span>
            <span className="text-[12px] text-[var(--color-ink-3)]">/ 100</span>
          </div>
          <p className="mt-1 text-[12px] text-[var(--color-ink-3)]">
            Proyección a {meses} meses · escenario central
          </p>
          <p className="mt-0.5 text-[11px] text-[var(--color-ink-4)]">
            {estructural
              ? "Las tres sendas proyectan cobros, gastos y deuda, y puntúan cada mes"
              : "Prolongación de la inercia observada: el motor no sirve previsión"}
          </p>
        </div>
        <div className="flex gap-1.5">
          {RANGOS.map((r) => (
            <button type="button" key={r} onClick={() => { setRango(r); setHover(null); }}
              aria-pressed={r === rango}
              className={`pildora ${r === rango ? "on" : ""}`} style={{ padding: "5px 13px", fontSize: 12 }}>
              {r}M
            </button>
          ))}
        </div>
      </div>

      <div className="relative -mr-6 mt-2 w-[calc(100%+1.5rem)]">
        <svg viewBox={`0 0 ${ancho} ${alto}`} className="w-full" role="img" aria-label={capas}>
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

          {/* La mediana del cuartil: una discontinua apagada y nada más. Con la
              banda intercuartílica pesaba más que la propia empresa. */}
          {datosPeer && (
            <path
              d={datosPeer.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.mediana).toFixed(1)}`).join(" ")}
              fill="none" stroke="#787d96" strokeWidth="1.6" strokeDasharray="6 6"
              strokeLinecap="round" opacity="0.8"
            />
          )}

          <path d={linea} fill="none" stroke="#b083e8" strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />

          {/* Cuándo empezó a torcerse */}
          {marca && (
            <g>
              <line x1={marca.x} x2={marca.x} y1={padT + 8} y2={marca.y - 10}
                stroke={marca.c} strokeWidth="1.2" strokeDasharray="4 4" opacity="0.45" />
              <circle cx={marca.x} cy={marca.y} r="5" fill="#120d1d" stroke={marca.c} strokeWidth="2.4" />
              <text x={marca.izquierda ? marca.x - 10 : marca.x + 10} y={padT + 6}
                textAnchor={marca.izquierda ? "end" : "start"} fontSize="15" fill={marca.c} fillOpacity="0.9">
                {marca.texto}
              </text>
            </g>
          )}

          {crudos.map((e) => (
            <path key={e.k} d={traza(sendas[e.k as keyof typeof sendas])} fill="none"
              stroke={e.c} strokeOpacity={e.k === "Medio" ? 0.9 : 0.6}
              strokeWidth={e.k === "Medio" ? 2 : 1.6} strokeDasharray="5 5"
              strokeLinejoin="round" strokeLinecap="round" />
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

          {/* La píldora de hoy se aparta cuando hay globo: si no, se solapan. */}
          {hover === null && (
            <g>
              <rect x={xHoy - 66} y={yHoy - 46} width="120" height="32" rx="10" fill="#17112a" stroke="rgba(255,255,255,.12)" />
              <text x={xHoy - 6} y={yHoy - 25} fill="#fff" fontSize="16.5" textAnchor="middle">{num(hoy)} hoy</text>
            </g>
          )}

          {/* La frontera: a la izquierda hay datos, a la derecha un modelo. */}
          <line x1={xHoy} x2={xHoy} y1={padT} y2={padT + h}
            stroke="rgba(255,255,255,.10)" strokeWidth="1" strokeDasharray="3 5" />

          {/* Guía del mes señalado */}
          {hover !== null && (
            <g pointerEvents="none">
              <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + h}
                stroke="#b083e8" strokeWidth="1" strokeOpacity="0.5" />
              <circle cx={x(hover)} cy={y(datos[hover].score)} r="5" fill="#b083e8" stroke="#120d1d" strokeWidth="2" />
            </g>
          )}

          {/* Zonas de escucha: una por mes, invisibles y de alto completo. */}
          {datos.map((d, i) => (
            <rect key={d.mes} x={x(i) - paso / 2} y={padT} width={paso}
              height={h} fill="transparent"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover((v) => (v === i ? null : v))} />
          ))}

          <text x={padL} y={alto - 8} fill="#787d96" fontSize="15">{mesCorto(datos[0].mes)}</text>
          <text x={xHoy} y={alto - 8} fill="#787d96" fontSize="15" textAnchor="middle">{mesCorto(datos[nHist - 1].mes)}</text>
          <text x={xFin} y={alto - 8} fill="#787d96" fontSize="15" textAnchor="middle">+{meses}m</text>
        </svg>

        {/* El globo va en HTML, no en SVG: hereda el cristal del sistema y el
            texto no se escala con el viewBox. */}
        {hBase && (() => {
          const arribaDelTodo = y(hBase.score) < padT + h * 0.34;
          return (
          <div
            className={`pointer-events-none absolute z-10 -translate-x-1/2 whitespace-nowrap rounded-xl border px-3 py-2 shadow-[0_8px_28px_rgba(0,0,0,.55)] ${arribaDelTodo ? "" : "-translate-y-full"}`}
            style={{
              left: `${(x(hover!) / ancho) * 100}%`,
              top: `${((y(hBase.score) + (arribaDelTodo ? 16 : -14)) / alto) * 100}%`,
              background: "#17112a", borderColor: "rgba(255,255,255,.12)",
            }}>
            <p className="text-[11px] text-[var(--color-ink-3)]">{mesCorto(hBase.mes)}</p>
            <p className="tnum text-[15px] font-medium leading-none">{num(hBase.score)}</p>
            {(hRep || hPeer) && (
              <p className="tnum mt-1 text-[11px] text-[var(--color-ink-2)]">
                {hRep && <>{hRep.delta >= 0 ? "+" : "−"}{num(Math.abs(hRep.delta))} pts</>}
                {hRep && hPeer && " · "}
                {hPeer && <>cuartil {num(hPeer.mediana)}</>}
              </p>
            )}
            {hRep && hRep.pctTendencia + hRep.pctBache > 0 && (
              <div className="mt-2 flex items-center gap-2.5 border-t border-[rgba(255,255,255,.10)] pt-2">
                <AnilloReparto tendencia={hRep.pctTendencia} bache={hRep.pctBache} />
                <div className="leading-tight">
                  <p className="tnum text-[11px]" style={{ color: "#b083e8" }}>
                    {hRep.pctTendencia} % tendencia
                  </p>
                  <p className="tnum text-[11px]" style={{ color: "#dfb631" }}>
                    {hRep.pctBache} % bache
                  </p>
                </div>
              </div>
            )}
            {/* Los tres factores que más movieron el mes. El anillo dice cuánto
                se queda; esto dice de dónde sale, con las palabras del motor. */}
            {hRep && hRep.drivers.length > 0 && (
              <ul className="mt-1.5 space-y-0.5">
                {[...hRep.drivers]
                  .sort((a, b) => Math.abs(b.points) - Math.abs(a.points))
                  .slice(0, 3)
                  .map((d) => (
                    <li key={d.field} className="flex items-baseline justify-between gap-4 text-[11px]">
                      <span className="text-[var(--color-ink-2)]">
                        {d.etiqueta}
                        <span className="ml-1 text-[var(--color-ink-4)]">{d.razon || d.reason}</span>
                      </span>
                      <span className="tnum" style={{ color: d.kind === "estructural" ? "#b083e8" : "#dfb631" }}>
                        {d.points >= 0 ? "+" : "−"}{num(Math.abs(d.points))}
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </div>
          );
        })()}
      </div>

      {(datosPeer || inflexion) && (
        <div className="mt-1.5 flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px] text-[var(--color-ink-4)]">
          <span className="inline-flex items-center gap-2">
            <i className="h-[2px] w-5 rounded-full" style={{ background: "#b083e8" }} />
            Tu score
          </span>
          {datosPeer && peer && (
            <span className="inline-flex items-center gap-2">
              <i className="h-[2px] w-5 rounded-full"
                style={{ backgroundImage: "repeating-linear-gradient(90deg,#787d96 0 4px,transparent 4px 8px)" }} />
              Mediana de tu {peer.etiqueta.toLowerCase()} · {peer.n} empresas
            </span>
          )}
        </div>
      )}

      {inflexion && (
        <p className="mt-1.5 text-[11.5px] leading-relaxed text-[var(--color-ink-3)]">{inflexion.frase}</p>
      )}
    </div>
  );
}

/**
 * Anillo del reparto del mes: cuánto del movimiento es tendencia y cuánto
 * bache. Dos arcos sobre la misma circunferencia, sin hueco entre ellos.
 */
function AnilloReparto({ tendencia, bache, tam = 38, grosor = 5 }:
  { tendencia: number; bache: number; tam?: number; grosor?: number }) {
  const total = Math.max(1, tendencia + bache);
  const r = (tam - grosor) / 2, cx = tam / 2;
  const circ = 2 * Math.PI * r;
  const lTend = (circ * tendencia) / total;
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center" style={{ width: tam, height: tam }}>
      <svg width={tam} height={tam} style={{ transform: "rotate(-90deg)" }}>
        {/* El bache ocupa toda la vuelta por debajo; la tendencia se pinta encima */}
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="#dfb631" strokeOpacity="0.85" strokeWidth={grosor} />
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="#b083e8" strokeWidth={grosor}
          strokeDasharray={`${lTend.toFixed(2)} ${circ.toFixed(2)}`} strokeLinecap="butt" />
      </svg>
      <span className="tnum absolute text-[10px] font-medium" style={{ color: "#b083e8" }}>
        {tendencia}
      </span>
    </span>
  );
}

/**
 * Camino de un escenario: puente browniano entre hoy y el destino. `forma`
 * curva la trayectoria y el ruido se escala con la volatilidad observada,
 * anulándose en los extremos para aterrizar exactamente en el objetivo.
 */
function senda(desde: number, hasta: number, n: number, forma: number, vol: number, semilla: number) {
  let s = semilla >>> 0;
  const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296 - 0.5);
  const paso: number[] = []; let acc = 0;
  for (let i = 0; i <= n; i++) { acc += r() * vol * 1.1; paso.push(acc); }
  const deriva = paso[n];
  const out: number[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const base = desde + (hasta - desde) * Math.pow(t, forma);
    const ruido = (paso[i] - deriva * t) * Math.sin(Math.PI * t);
    out.push(Math.max(1, Math.min(99, Math.round((base + ruido) * 10) / 10)));
  }
  out[0] = desde; out[n] = hasta;
  return out;
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
