"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { PALANCAS, type Empresa } from "@/lib/data";
import { simularPalanca, type ResultadoSimulacion } from "@/lib/motor";
import type { ApiSugerencia, ApiPalanca } from "@/lib/api";
import { eur, num, banda } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Card, CardHead, ScoreBadge, Delta, Boton, BandaChip } from "@/components/ui";

export default function Simulador({
  empresa: e,
  recomendaciones,
  simInicial,
}: {
  empresa: Empresa;
  recomendaciones?: {
    sugerencias: ApiSugerencia[];
    palancas: ApiPalanca[];
    modelVersion: string | null;
    nSims: number;
  };
  simInicial?: ResultadoSimulacion;
}) {
  const [palancaId, setPalancaId] = useState(PALANCAS[0].id);
  const palanca = PALANCAS.find((p) => p.id === palancaId) ?? PALANCAS[0];
  const [valor, setValor] = useState(palanca.defecto);
  const [generado, setGenerado] = useState(false);
  const [cargando, setCargando] = useState(false);

  const [sim, setSim] = useState<ResultadoSimulacion>(
    simInicial ?? {
      scoreNuevo: e.score,
      deltaScore: 0,
      cajaLiberada: 0,
      deltaBps: 0,
      eurAnio: 0,
      inaplicable: false,
      esReal: false,
    }
  );

  const b = banda(sim.scoreNuevo);

  // Recomputar contrafactualmente en el backend ante movimientos del slider
  useEffect(() => {
    let activo = true;
    setCargando(true);

    const timer = setTimeout(async () => {
      try {
        const res = await simularPalanca(e.id, palancaId, valor, e);
        if (activo) {
          setSim(res);
          setCargando(false);
        }
      } catch {
        if (activo) setCargando(false);
      }
    }, 120);

    return () => {
      activo = false;
      clearTimeout(timer);
    };
  }, [e, palancaId, valor]);

  function cambiarPalanca(id: string) {
    const p = PALANCAS.find((x) => x.id === id)!;
    setPalancaId(id);
    setValor(p.defecto);
    setGenerado(false);
  }

  function aplicarSugerencia(sug: ApiSugerencia) {
    // Emparejar sugerencia del motor con catálogo UI
    const match = PALANCAS.find(
      (p) =>
        p.id === sug.id ||
        (p.id === "reducir_dso" && sug.id === "adelantar_cobros") ||
        (p.id === "pronto_pago" && sug.id === "descuento_pronto_pago") ||
        (p.id === "bajar_linea" && sug.id === "bajar_utilizacion_linea") ||
        (p.id === "reducir_concent" && sug.id === "reducir_concentracion") ||
        (p.id === "sustituir_fact" && sug.id === "sustituir_factoring")
    );

    if (match) {
      setPalancaId(match.id);
      let v = match.defecto;
      if (sug.days) v = sug.days;
      else if (sug.pct) v = Math.round(sug.pct * 100);
      else if (sug.haircut) v = Math.round(sug.haircut * 100);
      setValor(v);
      setGenerado(false);
    }
  }

  // Mapa de aplicabilidad de palancas evaluado por FastAPI
  const palancaInfoMap = new Map<string, ApiPalanca>();
  (recomendaciones?.palancas ?? []).forEach((p) => {
    palancaInfoMap.set(p.id, p);
    if (p.id === "adelantar_cobros") palancaInfoMap.set("reducir_dso", p);
    if (p.id === "descuento_pronto_pago") palancaInfoMap.set("pronto_pago", p);
    if (p.id === "bajar_utilizacion_linea") palancaInfoMap.set("bajar_linea", p);
    if (p.id === "reducir_concentracion") palancaInfoMap.set("reducir_concent", p);
    if (p.id === "sustituir_factoring") palancaInfoMap.set("sustituir_fact", p);
  });

  return (
    <>
      <Cabecera
        titulo="Escenarios"
        sub={
          <>
            <Link
              href={`/${e.id}`}
              className="underline decoration-[var(--color-line-2)] underline-offset-2 hover:text-[var(--color-aqua)]"
            >
              {e.nombre} ({e.id})
            </Link>{" "}
            · contrafactual recomputado honestamente por el motor de riesgo
          </>
        }
        extra={
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
              POST /api/simulate
            </span>
            <Boton tono="plano" href={`/${e.id}`}>
              Volver a la ficha
            </Boton>
          </div>
        }
      />
      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <div className="space-y-4">
          <Card className="h-fit">
            <CardHead titulo="Palanca" sub="Las ocho del catálogo analítico" />
            <div className="flex flex-col gap-0.5 p-2">
              {PALANCAS.map((p) => {
                const info = palancaInfoMap.get(p.id);
                const inaplicable = info && !info.es_aplicable;
                return (
                  <button
                    key={p.id}
                    onClick={() => cambiarPalanca(p.id)}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 text-left text-[13px] transition-colors ${
                      p.id === palancaId
                        ? "bg-[var(--color-surface-3)] font-medium"
                        : "hover:bg-[var(--color-surface-2)] text-[var(--color-ink-3)]"
                    }`}
                  >
                    <span>{p.nombre}</span>
                    {inaplicable && (
                      <span className="text-[10px] text-amber-400/80 bg-amber-500/10 px-1.5 py-0.5 rounded">
                        {info.motivo_rechazo?.replace("sin_", "sin ") ?? "inaplicable"}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </Card>

          {recomendaciones?.sugerencias && recomendaciones.sugerencias.length > 0 && (
            <Card className="h-fit">
              <CardHead
                titulo="Rankings recomendados"
                sub={`Top óptimas por el motor (${recomendaciones.nSims} simulaciones ejecutadas)`}
              />
              <div className="flex flex-col gap-1.5 p-2">
                {recomendaciones.sugerencias.slice(0, 4).map((sug, idx) => (
                  <button
                    key={idx}
                    onClick={() => aplicarSugerencia(sug)}
                    className="group rounded-lg border border-[var(--color-line-2)] p-2.5 text-left text-[12px] hover:border-[var(--color-aqua)] hover:bg-[var(--color-surface-2)] transition-colors"
                  >
                    <div className="flex items-center justify-between font-medium">
                      <span className="group-hover:text-[var(--color-aqua)]">{sug.label}</span>
                      <span className="text-emerald-400 font-mono">+{num(sug.delta_score)} pts</span>
                    </div>
                    {sug.caja_liberada_eur && (
                      <div className="mt-1 text-[11px] text-[var(--color-ink-4)]">
                        Libera {eur(sug.caja_liberada_eur)}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-5">
          {sim.inaplicable && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-[13px] text-amber-200">
              <strong className="font-semibold">Palanca rechazada por el motor:</strong>{" "}
              {sim.motivoRechazo}
              <p className="mt-1 text-[11px] text-amber-300/80">
                El motor analiza las cuentas y líneas vivas de la empresa y no permite simular productos no existentes en el balance.
              </p>
            </div>
          )}

          <Card>
            <div className="flex items-center justify-between border-b border-[var(--color-line)] px-5 py-4">
              <div>
                <h2 className="text-[15px] font-medium">{palanca.nombre}</h2>
                <p className="text-[12px] text-[var(--color-ink-3)]">{palanca.descripcion}</p>
              </div>
              <div className="flex items-center gap-2">
                {cargando && (
                  <span className="text-[11px] font-mono text-[var(--color-aqua)] animate-pulse">
                    recalculando...
                  </span>
                )}
                <span className="text-[11px] font-mono text-[var(--color-ink-4)]">
                  {sim.esReal ? "FastAPI contrafactual" : "cliente local"}
                </span>
              </div>
            </div>
            <div className="px-5 py-5">
              <div className="flex items-baseline justify-between">
                <label htmlFor="v" className="text-[12px] text-[var(--color-ink-3)]">
                  {palanca.unidad}
                </label>
                <span className="tnum text-[20px] font-medium">{valor}</span>
              </div>
              <input
                id="v"
                type="range"
                min={palanca.min}
                max={palanca.max}
                value={valor}
                onChange={(ev) => {
                  setValor(+ev.target.value);
                  setGenerado(false);
                }}
                className="mt-3 w-full accent-[var(--color-aqua)]"
              />
              <div className="tnum mt-1 flex justify-between text-[11px] text-[var(--color-ink-4)]">
                <span>{palanca.min}</span>
                <span>{palanca.max}</span>
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
              <p className="tnum mt-1.5 text-[22px] font-medium leading-none">
                {sim.cajaLiberada > 0 ? eur(sim.cajaLiberada) : "—"}
              </p>
              <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">
                {sim.esReal ? "circulante recomputado" : "aritmética pura"}
              </p>
            </Card>
            <Card className="px-5 py-4">
              <p className="text-[12px] text-[var(--color-ink-3)]">Coste de financiación</p>
              <p className="tnum mt-1.5 text-[22px] font-medium leading-none">{sim.deltaBps} bps</p>
              <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">tipo implícito observado</p>
            </Card>
            <Card className="px-5 py-4">
              <p className="text-[12px] text-[var(--color-ink-3)]">Ahorro anual</p>
              <p className="tnum mt-1.5 text-[22px] font-medium leading-none">
                {sim.eurAnio > 0 ? eur(sim.eurAnio) : "—"}
              </p>
              <p className="mt-1 text-[11px] text-[var(--color-ink-4)]">sobre la deuda viva</p>
            </Card>
          </div>

          <Card>
            <CardHead titulo="La frase" sub="Lo que el director financiero se lleva" />
            <div className="px-5 py-5">
              <p className="text-[15px] leading-relaxed">
                {palanca.nombre.toLowerCase()} <span className="tnum font-medium">{valor} {palanca.unidad}</span>
                {" → "}
                <span className="font-medium" style={{ color: b.color }}>
                  +{num(sim.deltaScore)} puntos
                </span>
                {sim.cajaLiberada > 0 && (
                  <> → <span className="tnum font-medium">{eur(sim.cajaLiberada)}</span> de caja</>
                )}
                {sim.eurAnio > 0 && (
                  <> → <span className="tnum font-medium">{eur(sim.eurAnio)}/año</span> de ahorro</>
                )}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Boton onClick={() => setGenerado(true)}>Generar documento</Boton>
                <span className="text-[11px] text-[var(--color-ink-4)]">
                  P2 · borrador ejecutivo con impacto de caja calculado por el motor
                </span>
              </div>
            </div>
          </Card>

          {generado && (
            <Card>
              <CardHead
                titulo="Propuesta de optimización"
                sub="Borrador generado con datos del motor · revísalo antes de enviar"
              />
              <div className="px-5 py-5 text-[13px] leading-relaxed text-[var(--color-ink-2)]">
                <p className="text-[12px] text-[var(--color-ink-3)]">Para: Dirección Financiera / Tesorería</p>
                <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">
                  Asunto: Plan contrafactual de circulante — {e.nombre} ({e.id})
                </p>
                <div className="mt-3 space-y-2 border-l-2 border-[var(--color-line-2)] pl-4">
                  <p>Estimados señores,</p>
                  <p>
                    Tras la reevaluación contrafactual efectuada por el motor analítico de solvencia, proponemos
                    activar la palanca de <strong>{palanca.nombre.toLowerCase()}</strong> fijando un objetivo de{" "}
                    <strong>{valor} {palanca.unidad}</strong>.
                  </p>
                  <p className="tnum">
                    El modelo proyecta una mejora de <strong>+{num(sim.deltaScore)} puntos</strong> en la salud
                    financiera
                    {sim.cajaLiberada > 0 ? `, liberando ${eur(sim.cajaLiberada)} netos de liquidez` : ""}
                    {sim.eurAnio > 0 ? ` y con un ahorro de ${eur(sim.eurAnio)} al año sobre la deuda viva` : ""}.
                  </p>
                  <p>Quedamos a su disposición para coordinar los trámites necesarios.</p>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
