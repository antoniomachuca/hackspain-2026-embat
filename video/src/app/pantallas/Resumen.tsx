import Link from "../componentes/enlace";
import {
  empresa, grupo, recomendar, MI_EMPRESA, MES_ACTUAL, EMPRESAS_CON_SCORE,
  ANTICIPACION_MEDIANA, MODEL_VERSION,
} from "../lib/data";
import { eur, num, mesCorto } from "../lib/format";
import { Cabecera } from "../componentes/shell";
import { Waterfall, Sparkline } from "../componentes/charts";
import { Anillo } from "../componentes/anillo";
import { Prevision } from "../componentes/prevision";
import { Card, ScoreBadge, EstadoChip, Confianza, Delta, Boton } from "../componentes/ui";

/**
 * La pantalla de resumen del front, con el mismo marcado y las mismas clases
 * que `front/app/page.tsx`. Dos diferencias, las dos obligadas por el vídeo:
 *
 *   · la página del front es `async` y consulta al motor; aquí se usa la vía
 *     de demostración, que es a la que cae el front cuando el motor no está y
 *     la única que deja todos los paneles completos;
 *   · donde la app deja que el dato aparezca de golpe, entra un progreso que
 *     viene del frame.
 */
export type ProgresoResumen = {
  /** El score del anillo, contando desde 0 hasta el real. */
  anillo: number;
  /** Barrido de izquierda a derecha sobre el gráfico de previsión. */
  prevision: number;
  /** Crecimiento escalonado de las seis contribuciones. */
  waterfall: number;
  /** Aparición de las filas de palancas y de las sociedades del grupo. */
  filas: number;
  /** Palanca accionada: mueve la proyección. Capa propia del vídeo. */
  palanca?: { nombre: string; delta: number; mezcla: number };
  /** Id de la palanca que se resalta en la lista de recomendaciones. */
  destacada?: string;
};

/** La empresa de demostración: la misma a la que cae el front sin motor. */
export const EMPRESA_DEMO = empresa(MI_EMPRESA) ?? EMPRESAS_CON_SCORE[1];

/** Las tres palancas que el motor deja arriba tras simular las ocho. */
export const RECOS = recomendar(EMPRESA_DEMO, 3);

export function Resumen({ p }: { p: ProgresoResumen }) {
  const e = EMPRESA_DEMO;
  const g = grupo(e.grupo);
  const recos = RECOS;
  const filiales = g.miembros.filter((m) => m.id !== e.id);
  const percentil = e.drivers[0].p_peer;

  const scoreVivo = Math.round(e.score * p.anillo * 10) / 10;

  return (
    <>
      <Cabecera
        titulo={e.nombre}
        sub={<>{e.sector} · {mesCorto(MES_ACTUAL)} · <span className="tnum text-[var(--color-ink-4)]">{MODEL_VERSION}</span></>}
        extra={<Boton tono="plano" href={`/empresa/${e.id}/escenarios`}>Simular mejoras</Boton>}
      />

      {/* ── Tu score y tu proyección ───────────────────────────────── */}
      <div className="grid gap-5 xl:grid-cols-[296px_1fr]">
        <Card className="relative flex flex-col items-center overflow-hidden px-6 py-6">
          <div className="pointer-events-none absolute -top-24 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full opacity-35 blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(176,131,232,.55), transparent 70%)" }} />
          <div className="relative flex w-full flex-col items-center">
            <p className="text-[12.5px] text-[var(--color-ink-3)]">Tu salud financiera</p>
            <div className="mt-3"><Anillo score={scoreVivo} delta={e.score - e.scorePrev} tam={162} /></div>

            <div className="mt-4 flex items-center gap-2">
              <EstadoChip estado={e.estado} />
              <Confianza nivel={e.confianza} />
            </div>

            <div className="mt-5 grid w-full grid-cols-3 gap-3 border-t border-[var(--color-line)] pt-4">
              <Mini k="Nivel" v={num(e.nivelBase)} />
              <Mini k="Momentum" v={(e.momentum >= 0 ? "+" : "−") + num(Math.abs(e.momentum), 2)} />
              <Mini k="Percentil" v={`P${percentil}`} />
            </div>

            <div className="mt-4 w-full space-y-2 border-t border-[var(--color-line)] pt-4">
              <Dato k="Días de caja" v={`${e.diasCaja}`} />
              <Dato k="DSO / DPO" v={`${e.dso} / ${e.dpo} d`} />
              <Dato k="Uso de línea" v={`${e.utilizacionLinea}%`} />
              <Dato k="Historia" v={`${e.mesesHistoria} meses`} />
            </div>
          </div>
        </Card>

        <Card className="px-6 py-5">
          <h2 className="mb-3 text-[15px] font-semibold tracking-tight">Histórico y proyección</h2>
          {/* El barrido revela el dibujo tal cual, sin recalcularlo, para que
              las etiquetas del abanico no bailen mientras entra. Los otros
              tres lados se abren en negativo: el gráfico se sale del
              contenedor y con el recorte a cero perdía la leyenda. */}
          <div style={{ clipPath: p.prevision >= 1 ? undefined : `inset(-80px ${(1 - p.prevision) * 100}% -80px -60px)` }}>
            <Prevision
              datos={e.trayectoria} momentum={e.momentum}
              peer={e.peer} datosPeer={e.trayectoriaPeer}
              reparto={e.reparto} inflexion={e.inflexion}
              palanca={p.palanca}
            />
          </div>
          <p className="mt-6 text-center text-[11px] leading-relaxed text-[var(--color-ink-4)]">
            La proyección extiende tu inercia observada y abre la horquilla con el horizonte.
            Es un escenario, no una predicción cerrada.
          </p>
        </Card>
      </div>

      {/* ── Aviso, si lo hay ───────────────────────────────────────── */}
      {e.alerta && (
        <Card className="mt-5 px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-medium">
                Lo vimos {e.alerta.mesesAnticipacion} meses antes, en {mesCorto(e.alerta.mesDeteccion)}
              </p>
              <p className="mt-1 text-[12px] leading-relaxed text-[var(--color-ink-3)]">
                {e.alerta.texto}. Se movieron {e.alerta.driversMovidos.join(" y ").toLowerCase()}.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {e.alerta.driversMovidos.map((d, i) => (
                <span key={d} className="rounded-md bg-[rgba(255,255,255,.07)] px-2.5 py-1 text-[11px] text-[var(--color-ink-2)]">
                  {d} <span className="tnum text-[var(--color-ink-4)]">{e.alerta!.codigosRazon[i]}</span>
                </span>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* ── Por qué y qué hacer ────────────────────────────────────── */}
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card className="px-6 py-6">
          <h2 className="text-[15px] font-semibold tracking-tight">Por qué este número</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Seis contribuciones que suman exactamente tu score
          </p>
          <div className="-mx-2 mt-4"><Waterfall drivers={e.drivers} altura={260} ancho={756} progreso={p.waterfall} /></div>
          <Link href={`/empresa/${e.id}/drivers`} className="mt-2 inline-block text-[12.5px] text-[var(--color-purple)] hover:underline">
            Ver el detalle
          </Link>
        </Card>

        <Card className="px-6 py-6">
          <h2 className="text-[15px] font-semibold tracking-tight">Qué puedes hacer</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Simulado contra el motor. Ninguna cifra sale de un modelo de lenguaje.
          </p>
          <div className="mt-4 flex flex-col gap-2.5">
            {recos.map((r, i) => {
              const on = p.destacada === r.palanca.id;
              return (
                <Link key={r.palanca.id} href={`/empresa/${e.id}/escenarios`} className="fila block px-4 py-3.5"
                  style={{
                    ...entra(p.filas, i, recos.length),
                    ...(on
                      ? {
                          background: "rgba(128,239,162,.11)",
                          borderColor: "rgba(128,239,162,.40)",
                          boxShadow: "0 0 0 1px rgba(128,239,162,.22)",
                        }
                      : {}),
                  }}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium">
                        {r.palanca.nombre} · <span className="tnum font-normal">{r.valor} {r.palanca.unidad}</span>
                      </p>
                      <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-3)]">{r.palanca.descripcion}</p>
                    </div>
                    <Delta v={r.deltaScore} sufijo=" pts" className="shrink-0 pt-0.5" />
                  </div>
                  <div className="tnum mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-[var(--color-ink-2)]">
                    {r.cajaLiberada > 0 && <span>Caja <strong className="font-medium">{eur(r.cajaLiberada)}</strong></span>}
                    {r.eurAnio > 0 && <span>Ahorro <strong className="font-medium">{eur(r.eurAnio)}/año</strong></span>}
                  </div>
                </Link>
              );
            })}
          </div>
        </Card>
      </div>

      {/* ── Tu grupo ───────────────────────────────────────────────── */}
      <Card className="mt-5 px-6 py-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[16px] font-semibold tracking-tight">{g.nombre}</h2>
            <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
              Tus {g.miembros.length} sociedades · consolidado {num(g.consolidado)} · penalización por contagio {num(g.penalizacion)}
            </p>
          </div>
          <Link href={`/grupo/${g.id}`} className="pildora">Ver el grupo</Link>
        </div>

        <div className="flex flex-col gap-2">
          {filiales.map((m, i) => (
            <Link key={m.id} href={`/empresa/${m.id}`}
              className="fila grid grid-cols-2 items-center gap-4 px-4 py-3.5 lg:grid-cols-[2fr_.6fr_.7fr_.8fr_.9fr]"
              style={entra(p.filas, i, filiales.length)}>
              <div className="col-span-2 min-w-0 lg:col-span-1">
                <p className="truncate text-[13.5px] font-medium">{m.nombre}</p>
                <p className="truncate text-[11px] text-[var(--color-ink-4)]">{m.sector}</p>
              </div>
              <div className="text-right">
                {m.mesesHistoria >= 12 ? <ScoreBadge score={m.score} size="sm" /> : <span className="text-[11.5px] text-[var(--color-ink-4)]">sin score</span>}
              </div>
              <div className="text-right">{m.mesesHistoria >= 12 && <Delta v={m.momentum} />}</div>
              <div className="hidden lg:block">{m.mesesHistoria >= 12 && <Sparkline datos={m.trayectoria} progreso={p.filas} />}</div>
              <div className="hidden lg:block">{m.mesesHistoria >= 12 && <EstadoChip estado={m.estado} />}</div>
            </Link>
          ))}
        </div>
      </Card>
      {/* ── Comparativa anónima ────────────────────────────────────── */}
      <Card className="mt-5 px-6 py-6">
        <h2 className="text-[15px] font-semibold tracking-tight">Tu posición frente a empresas comparables</h2>
        <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
          Contra el conjunto anónimo de 250 grupos. Nunca se identifica a ninguna empresa.
        </p>
        <div className="mt-6">
          <div className="relative h-2 w-full rounded-full"
            style={{ background: "linear-gradient(90deg,#e5775b 0%,#e59f5e 34%,#dfb631 62%,#80efa2 100%)" }}>
            <span className="absolute top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full bg-white"
              style={{ left: `${percentil * p.filas}%` }} />
          </div>
          <div className="tnum mt-2.5 flex justify-between text-[11px] text-[var(--color-ink-4)]">
            <span>P0</span><span>P25</span><span>P50</span><span>P75</span><span>P100</span>
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-[var(--color-ink-2)]">
            Estás en el <strong className="font-medium">percentil {percentil}</strong> de tu grupo de pares
            —empresas de tamaño y moneda comparables—. La mediana de anticipación del sistema es de{" "}
            <strong className="font-medium">{ANTICIPACION_MEDIANA} meses</strong>, medida a una tasa fijada
            de una falsa alarma por empresa y año.
          </p>
        </div>
      </Card>
    </>
  );
}

/** Entrada escalonada: cada fila sube un poco más tarde que la anterior. */
function entra(p: number, i: number, n: number): React.CSSProperties {
  const t = Math.max(0, Math.min(1, p * (n + 1.5) - i));
  const s = 1 - Math.pow(1 - t, 3);
  return { opacity: s, transform: `translateY(${(1 - s) * 14}px)` };
}

function Dato({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[12px] text-[var(--color-ink-3)]">{k}</span>
      <span className="tnum text-[12.5px] font-medium">{v}</span>
    </div>
  );
}

function Mini({ k, v }: { k: string; v: string }) {
  return (
    <div className="text-center">
      <p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
      <p className="tnum mt-1 text-[17px] font-semibold leading-none">{v}</p>
    </div>
  );
}
