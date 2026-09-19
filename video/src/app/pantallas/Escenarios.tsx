import Link from "../componentes/enlace";
import { PALANCAS, simular } from "../lib/data";
import { EMPRESA_DEMO } from "./Resumen";
import { eur, num, banda } from "../lib/format";
import { Cabecera } from "../componentes/shell";
import { Card, CardHead, ScoreBadge, Delta, Boton } from "../componentes/ui";

/**
 * El simulador de la app. Mismo marcado que
 * `front-dashboard/app/empresa/[id]/escenarios/simulador.tsx`; lo único que
 * cambia es de dónde sale el estado: allí lo pone el usuario con el ratón,
 * aquí lo pone el frame. La simulación es la misma función `simular()`, así
 * que las cifras del vídeo son las que devuelve el motor, no un decorado.
 */
export function Escenarios({ palancaId, valor, generado }: {
  palancaId: string; valor: number; generado: boolean;
}) {
  const e = EMPRESA_DEMO;
  const palanca = PALANCAS.find((p) => p.id === palancaId)!;
  const sim = simular(e, palancaId, valor);
  const b = banda(sim.scoreNuevo);
  const recorrido = (valor - palanca.min) / (palanca.max - palanca.min);

  return (
    <>
      <Cabecera
        titulo="Escenarios"
        sub={<><span className="underline decoration-[var(--color-line-2)] underline-offset-2">{e.nombre}</span> · contrafactual recomputado, no extrapolado</>}
        extra={<Boton tono="plano" href={`/empresa/${e.id}`}>Volver a la ficha</Boton>}
      />
      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit">
          <CardHead titulo="Palanca" sub="Las ocho del catálogo" />
          <div className="flex flex-col gap-0.5 p-2">
            {PALANCAS.map((p) => (
              <span key={p.id}
                className={`block rounded-lg px-3 py-2 text-left text-[13px] ${
                  p.id === palancaId ? "bg-[var(--color-surface-3)] font-medium" : "text-[var(--color-ink-3)]"}`}>
                {p.nombre}
              </span>
            ))}
          </div>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHead titulo={palanca.nombre} sub={palanca.descripcion} />
            <div className="px-5 py-5">
              <div className="flex items-baseline justify-between">
                <span className="text-[12px] text-[var(--color-ink-3)]">{palanca.unidad}</span>
                <span className="tnum text-[20px] font-medium">{valor}</span>
              </div>
              {/* El <input type=range> nativo no se puede arrastrar en un
                  render; se dibuja la misma pista con la posición exacta. */}
              <div className="relative mt-3 h-4">
                <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-[rgba(255,255,255,.14)]" />
                <div className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-[var(--color-purple)]"
                  style={{ width: `${recorrido * 100}%` }} />
                <span className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--color-purple)] shadow-[0_2px_8px_rgba(0,0,0,.6)]"
                  style={{ left: `${recorrido * 100}%` }} />
              </div>
              <div className="tnum mt-1 flex justify-between text-[11px] text-[var(--color-ink-4)]">
                <span>{palanca.min}</span><span>{palanca.max}</span>
              </div>
            </div>
          </Card>

          <div className="grid gap-3 sm:grid-cols-4">
            <Card className="px-5 py-4">
              <p className="text-[12px] text-[var(--color-ink-3)]">Score simulado</p>
              <div className="mt-1.5 flex items-baseline gap-2">
                <ScoreBadge score={sim.scoreNuevo} />
                <Delta v={sim.deltaScore} sufijo=" pts" />
              </div>
              <p className="tnum mt-1 text-[11px] text-[var(--color-ink-4)]">desde {num(e.score)}</p>
            </Card>
            <Card className="px-5 py-4">
              <p className="text-[12px] text-[var(--color-ink-3)]">Caja liberada</p>
              <p className="tnum mt-1.5 text-[22px] font-medium leading-none">{sim.cajaLiberada > 0 ? eur(sim.cajaLiberada) : "—"}</p>
              <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">aritmética pura</p>
            </Card>
            <Card className="px-5 py-4">
              <p className="text-[12px] text-[var(--color-ink-3)]">Coste de financiación</p>
              <p className="tnum mt-1.5 text-[22px] font-medium leading-none">{sim.deltaBps} bps</p>
              <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">tipo implícito observado</p>
            </Card>
            <Card className="px-5 py-4">
              <p className="text-[12px] text-[var(--color-ink-3)]">Ahorro anual</p>
              <p className="tnum mt-1.5 text-[22px] font-medium leading-none">{sim.eurAnio > 0 ? eur(sim.eurAnio) : "—"}</p>
              <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">sobre la deuda viva</p>
            </Card>
          </div>

          <Card>
            <CardHead titulo="La frase" sub="Lo que el director financiero se lleva" />
            <div className="px-5 py-5">
              <p className="text-[15px] leading-relaxed">
                {palanca.nombre.toLowerCase()} <span className="tnum font-medium">{valor} {palanca.unidad}</span>
                {" → "}<span className="font-medium" style={{ color: b.color }}>+{num(sim.deltaScore)} puntos</span>
                {sim.cajaLiberada > 0 && <> → <span className="tnum font-medium">{eur(sim.cajaLiberada)}</span> de caja</>}
                {sim.eurAnio > 0 && <> → <span className="tnum font-medium">{eur(sim.eurAnio)}/año</span> de ahorro</>}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Boton>Generar documento</Boton>
                <span className="text-[11px] text-[var(--color-ink-4)]">
                  P2 · el único punto donde interviene un modelo de lenguaje
                </span>
              </div>
            </div>
          </Card>

          {generado && (
            <Card>
              <CardHead titulo="Propuesta de pronto pago" sub="Borrador generado · revísalo antes de enviar" />
              <div className="px-5 py-5 text-[13px] leading-relaxed text-[var(--color-ink-2)]">
                <p className="text-[12px] text-[var(--color-ink-3)]">Para: clientes con mayor retraso de cobro</p>
                <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">Asunto: Descuento por pago anticipado — {e.nombre}</p>
                <div className="mt-3 space-y-2 border-l-2 border-[var(--color-line-2)] pl-4">
                  <p>Estimados señores,</p>
                  <p>
                    Con el fin de agilizar nuestro circuito de cobros, les ofrecemos un descuento del 2,0 % sobre
                    las facturas abonadas con {valor} días de antelación respecto a su vencimiento.
                  </p>
                  <p className="tnum">
                    La tasa propuesta se sitúa por debajo del coste de nuestra línea de crédito, por lo que
                    resulta ventajosa para ambas partes. Importe afectado estimado: {eur(sim.cajaLiberada)}.
                  </p>
                  <p>Quedamos a su disposición.</p>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
