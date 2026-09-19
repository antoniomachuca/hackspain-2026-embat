import Link from "next/link";
import {
  empresa, grupo, recomendar, MI_EMPRESA, MES_ACTUAL, EMPRESAS_CON_SCORE,
  MODEL_VERSION, type Estado,
} from "@/lib/data";
import { eur, num, mesCorto } from "@/lib/format";
import { cargarEmpresa, cargarRecomendaciones, cargarFiliales, nombreDe } from "@/lib/motor";
import { Cabecera } from "@/components/shell";
import { Waterfall, Sparkline } from "@/components/charts";
import { Anillo } from "@/components/anillo";
import { Prevision } from "@/components/prevision";
import { Card, ScoreBadge, BandaChip, EstadoChip, Confianza, Delta, Boton } from "@/components/ui";

export default async function Resumen() {
  // El motor manda; si no responde, el front sigue con los datos de demostración.
  const real = await cargarEmpresa(MI_EMPRESA);
  const e = real ?? empresa(MI_EMPRESA) ?? EMPRESAS_CON_SCORE[1];

  const [rk, rawFiliales] = await Promise.all([
    cargarRecomendaciones(e.id),
    cargarFiliales(e.grupo, e.id),
  ]);

  const g = grupo(e.grupo);
  const filiales = (rawFiliales && rawFiliales.length > 0)
    ? rawFiliales.map((f) => ({
        id: f.company_id,
        nombre: nombreDe(f.company_id),
        sector: f.erp ? `ERP ${f.erp}` : "Sin ERP",
        score: f.score,
        momentum: f.momentum,
        estado: f.state as Estado,
        mesesHistoria: f.state_eligible ? 24 : 8,
        trayectoria: [{ mes: "2026-09", score: f.score, nivel: f.base_health }],
      }))
    : g.miembros.filter((m) => m.id !== e.id);

  const todosScores = [e.score, ...filiales.map((f) => f.score)];
  const mediaGrupo = todosScores.reduce((a, b) => a + b, 0) / (todosScores.length || 1);
  const peorScore = Math.min(...todosScores);
  const consolidado = Math.round((0.65 * mediaGrupo + 0.35 * peorScore) * 10) / 10;
  const penalizacion = peorScore < 40 ? Math.round((40 - peorScore) * 0.25 * 10) / 10 : 0;

  const recomendada = rk?.recomendado ?? null;
  const rawSugerencias = rk?.sugerencias ?? [];
  const vistas = new Set<string>();
  const palancasSalud: typeof rawSugerencias = [];

  if (recomendada?.id) {
    vistas.add(recomendada.id);
    palancasSalud.push(recomendada);
  }

  for (const s of rawSugerencias) {
    if (!vistas.has(s.id)) {
      vistas.add(s.id);
      palancasSalud.push(s);
    }
  }

  const mejorCirculante = rk?.opcionesCirculante?.[0] ?? null;
  const whatif = rk?.whatif ?? null;
  const recos = recomendar(empresa(MI_EMPRESA) ?? EMPRESAS_CON_SCORE[1], 3);
  const percentil = e.drivers?.[0]?.p_peer ?? 50;

  return (
    <>
      <Cabecera
        titulo={e.nombre}
        sub={<>{e.sector} · {mesCorto(MES_ACTUAL)} · <span className="tnum text-[var(--color-ink-4)]">{real ? "motor conectado" : "modo demo"}{rk?.modelVersion ? ` · ${rk.modelVersion.slice(0, 12)}` : ""}</span></>}
        extra={<Boton tono="plano" href={`/empresa/${e.id}/escenarios`}>Simular mejoras</Boton>}
      />

      {/* ── Tu score y tu proyección ───────────────────────────────── */}
      <div className="grid gap-5 xl:grid-cols-[296px_1fr]">
        <Card className="relative flex flex-col items-center overflow-hidden px-6 py-6">
          <div className="pointer-events-none absolute -top-24 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full opacity-35 blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(176,131,232,.55), transparent 70%)" }} />
          <div className="relative flex w-full flex-col items-center">
            <p className="text-[12.5px] text-[var(--color-ink-3)]">Tu salud financiera</p>
            <div className="mt-3"><Anillo score={e.score} delta={e.score - e.scorePrev} estado={e.estado} tam={162} /></div>

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
          <Prevision
            datos={e.trayectoria} momentum={e.momentum}
            peer={e.peer} datosPeer={e.trayectoriaPeer}
            reparto={e.reparto} inflexion={e.inflexion}
          />
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
                Detección en {mesCorto(e.alerta.mesDeteccion)}
                {e.alerta.mesesAnticipacion == null
                  ? ""
                  : e.alerta.mesesAnticipacion > 0
                    ? ` · ${e.alerta.mesesAnticipacion} ${e.alerta.mesesAnticipacion === 1 ? "mes" : "meses"} antes del cambio material`
                    : e.alerta.mesesAnticipacion === 0
                      ? " · el mismo mes del cambio material"
                      : ` · cambio material ${-e.alerta.mesesAnticipacion} ${e.alerta.mesesAnticipacion === -1 ? "mes" : "meses"} antes: detección tardía`}
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
          <div className="-mx-2 mt-4"><Waterfall drivers={e.drivers} altura={260} /></div>
          <Link href={`/empresa/${e.id}/drivers`} className="mt-2 inline-block text-[12.5px] text-[var(--color-purple)] hover:underline">
            Ver el detalle
          </Link>
        </Card>

        <Card className="px-6 py-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-[15px] font-semibold tracking-tight">Qué puedes hacer (Simulador What-If)</h2>
              <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
                Diagnóstico de tesorería y palancas calculadas sobre el balance de {e.id}.
              </p>
            </div>
            {rk?.nSims ? (
              <span className="rounded-md border border-[rgba(255,255,255,.08)] bg-[rgba(255,255,255,.03)] px-2 py-0.5 text-[10.5px] text-[var(--color-ink-3)]">
                {rk.nSims} sims evaluadas
              </span>
            ) : null}
          </div>

          {/* ── Recomendación Ejecutiva Embat (Directa de balance / Telegram) ── */}
          {whatif && (
            <div className="mt-4 rounded-xl border border-[rgba(176,131,232,.25)] bg-[rgba(176,131,232,.06)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[var(--color-purple)]/20 px-2 py-0.5 text-[11px] font-medium text-[var(--color-purple)]">
                    ★ Solución Embat
                  </span>
                  <span className="text-[12px] font-semibold text-white">
                    {whatif.recommended_product}
                  </span>
                </div>
                <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10.5px] font-medium text-[var(--color-emerald)]">
                  {whatif.projected_state}
                </span>
              </div>
              <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--color-ink-2)]">
                {whatif.product_rationale}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 border-t border-[rgba(255,255,255,.08)] pt-2.5 text-[11.5px] text-[var(--color-ink-3)]">
                <span>
                  Inyección / tramo óptimo:{" "}
                  <strong className="tnum font-semibold text-white">
                    {eur(whatif.injection_amount)}
                  </strong>
                </span>
                <span>
                  Score proyectado:{" "}
                  <strong className="tnum font-semibold text-[var(--color-purple)]">
                    {num(whatif.projected_score)}
                  </strong>{" "}
                  <span className="text-[var(--color-emerald)] font-medium">
                    (+{num(whatif.delta_score)} pts)
                  </span>
                </span>
              </div>
            </div>
          )}

          {/* ── Rankings de Palancas (Salud + Circulante sin humo) ── */}
          <div className="mt-4 flex flex-col gap-2.5">
            {palancasSalud.length > 0 ? (
              <>
                {palancasSalud.slice(0, 3).map((s, idx) => {
                  const esRec = recomendada?.id === s.id && recomendada?.label === s.label;
                  return (
                    <Link
                      key={`${s.id}-${idx}`}
                      href={`/empresa/${e.id}/escenarios`}
                      className={`fila px-4 py-3.5 transition-all ${
                        esRec ? "border-l-2 border-l-[var(--color-purple)] bg-[rgba(176,131,232,.04)]" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-[13px] font-medium text-[var(--color-ink-1)]">
                              {s.label}
                            </p>
                            {esRec && (
                              <span className="rounded bg-[var(--color-purple)]/15 px-1.5 py-0.2 text-[10px] font-medium text-[var(--color-purple)]">
                                ★ Recomendada
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-3)]">
                            {s.agreement_type
                              ? `Acuerdo: ${s.agreement_type.replace(/_/g, " ")}`
                              : s.days
                              ? `Ajuste temporal: ${s.days} días`
                              : s.pct
                              ? `Optimización: ${Math.round(s.pct * 100)}%`
                              : "Palanca estructural de balance"}
                            {s.haircut ? ` · dto ${Math.round(s.haircut * 1000) / 10}%` : ""}
                          </p>
                        </div>
                        <Delta v={s.delta_score} sufijo=" pts" className="shrink-0 pt-0.5" />
                      </div>
                      <div className="tnum mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-[var(--color-ink-2)]">
                        {s.caja_liberada_eur && s.caja_liberada_eur > 0 && (
                          <span>
                            Caja liberada:{" "}
                            <strong className="font-medium text-white">
                              {eur(s.caja_liberada_eur)}
                            </strong>
                          </span>
                        )}
                        {s.eur_año && s.eur_año > 0 && (
                          <span>
                            Ahorro anual:{" "}
                            <strong className="font-medium text-white">
                              {eur(s.eur_año)}/año
                            </strong>
                          </span>
                        )}
                      </div>
                    </Link>
                  );
                })}

                {/* Opción de Circulante Puro (Caja sin computar CIRBE ni alterar score) */}
                {mejorCirculante && (
                  <Link
                    href={`/empresa/${e.id}/escenarios`}
                    className="fila px-4 py-3.5 border-dashed border-[rgba(255,255,255,.12)]"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-[13px] font-medium text-[var(--color-ink-1)]">
                            {mejorCirculante.label}
                          </p>
                          <span className="rounded bg-[rgba(255,255,255,.08)] px-1.5 py-0.2 text-[10px] text-[var(--color-ink-3)]">
                            Circulante puro
                          </span>
                        </div>
                        <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-3)]">
                          {mejorCirculante.agreement_type
                            ? `Acuerdo: ${mejorCirculante.agreement_type.replace(/_/g, " ")} · `
                            : ""}
                          Caja inmediata a proveedores sin computar endeudamiento ni alterar CIRBE
                        </p>
                      </div>
                      <span className="text-[11px] text-[var(--color-ink-4)] shrink-0 pt-0.5">
                        ΔS nulo
                      </span>
                    </div>
                    <div className="tnum mt-2 text-[11.5px] text-[var(--color-ink-2)]">
                      Caja liberada:{" "}
                      <strong className="font-medium text-white">
                        {eur(mejorCirculante.caja_liberada_eur ?? 0)}
                      </strong>
                    </div>
                  </Link>
                )}
              </>
            ) : (
              recos.map((r) => (
                <Link key={r.palanca.id} href={`/empresa/${e.id}/escenarios`} className="fila px-4 py-3.5">
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
              ))
            )}
          </div>

          <div className="mt-4 flex justify-end border-t border-[var(--color-line)] pt-3">
            <Link
              href={`/empresa/${e.id}/escenarios`}
              className="flex items-center gap-1 text-[12px] font-medium text-[var(--color-purple)] hover:underline"
            >
              Abrir simulador interactivo de palancas →
            </Link>
          </div>
        </Card>
      </div>

      {/* ── Tu grupo ───────────────────────────────────────────────── */}
      <Card className="mt-5 px-6 py-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[16px] font-semibold tracking-tight">{e.grupoNombre}</h2>
            <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
              Tus {todosScores.length} sociedades · consolidado {num(consolidado)} · penalización por contagio {num(penalizacion)}
            </p>
          </div>
          <Link href={`/grupo/${e.grupo}`} className="pildora">Ver el grupo</Link>
        </div>

        <div className="flex flex-col gap-2">
          {filiales.map((m) => (
            <Link key={m.id} href={`/${m.id}`}
              className="fila grid grid-cols-2 items-center gap-4 px-4 py-3.5 lg:grid-cols-[2fr_.6fr_.7fr_.8fr_.9fr]">
              <div className="col-span-2 min-w-0 lg:col-span-1">
                <p className="truncate text-[13.5px] font-medium">{m.nombre}</p>
                <p className="truncate text-[11px] text-[var(--color-ink-4)]">{m.sector}</p>
              </div>
              <div className="text-right">
                {m.mesesHistoria >= 12 ? <ScoreBadge score={m.score} size="sm" /> : <span className="text-[11.5px] text-[var(--color-ink-4)]">sin score</span>}
              </div>
              <div className="text-right">{m.mesesHistoria >= 12 && <Delta v={m.momentum} />}</div>
              <div className="hidden lg:block">{m.mesesHistoria >= 12 && <Sparkline datos={m.trayectoria} />}</div>
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
              style={{ left: `${percentil}%` }} />
          </div>
          <div className="tnum mt-2.5 flex justify-between text-[11px] text-[var(--color-ink-4)]">
            <span>P0</span><span>P25</span><span>P50</span><span>P75</span><span>P100</span>
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-[var(--color-ink-2)]">
            Estás en el <strong className="font-medium">percentil {percentil}</strong> de tu grupo de pares
            —empresas de tamaño y moneda comparables—. La anticipación de cada aviso se mide por episodio
            frente al cambio material y se muestra en el panel de detección de la ficha.
          </p>
        </div>
      </Card>
    </>
  );
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
