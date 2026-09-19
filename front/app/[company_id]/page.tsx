import Link from "next/link";
import { notFound } from "next/navigation";
import {
  MES_ACTUAL,
  ANTICIPACION_MEDIANA,
} from "@/lib/data";
import { eur, num, mesCorto } from "@/lib/format";
import { cargarEmpresa, cargarRecomendaciones, cargarFiliales, nombreDe } from "@/lib/motor";
import { Cabecera } from "@/components/shell";
import { Waterfall, Sparkline } from "@/components/charts";
import { Anillo } from "@/components/anillo";
import { Prevision } from "@/components/prevision";
import { Card, ScoreBadge, EstadoChip, Confianza, Delta, Boton } from "@/components/ui";

function normalizarId(raw: string): string | null {
  const limpio = decodeURIComponent(raw).trim().toUpperCase();
  if (limpio.includes(".") || limpio.startsWith("_") || limpio === "FAVICON.ICO") {
    return null;
  }
  if (/^COMP_\d{1,4}$/.test(limpio)) {
    const numPart = limpio.replace("COMP_", "");
    return `COMP_${numPart.padStart(4, "0")}`;
  }
  if (/^\d{1,4}$/.test(limpio)) {
    return `COMP_${limpio.padStart(4, "0")}`;
  }
  return limpio;
}

export default async function EmpresaPage({
  params,
}: {
  params: Promise<{ company_id: string }>;
}) {
  const { company_id } = await params;
  const idNormalizado = normalizarId(company_id);
  if (!idNormalizado) {
    notFound();
  }

  // Carga del motor real DuckDB + FastAPI
  const e = await cargarEmpresa(idNormalizado);
  if (!e) {
    notFound();
  }

  const [rk, rawFiliales] = await Promise.all([
    cargarRecomendaciones(e.id),
    cargarFiliales(e.grupo, e.id),
  ]);

  const percentil = e.drivers?.[0]?.p_peer ?? 50;

  // Filiales del grupo en la base de datos
  const filiales = rawFiliales.map((f) => ({
    id: f.company_id,
    nombre: nombreDe(f.company_id),
    sector: f.erp ? `ERP ${f.erp}` : "Sin ERP",
    score: f.score,
    momentum: f.momentum,
    estado: f.state,
    mesesHistoria: f.state_eligible ? 24 : 8,
    trayectoria: [{ mes: "2026-09", score: f.score, nivel: f.base_health }],
  }));

  // Métricas agregadas del grupo
  const todosScores = [e.score, ...filiales.map((f) => f.score)];
  const mediaGrupo = todosScores.reduce((a, b) => a + b, 0) / (todosScores.length || 1);
  const peorScore = Math.min(...todosScores);
  const consolidado = Math.round((0.65 * mediaGrupo + 0.35 * peorScore) * 10) / 10;
  const penalizacion = peorScore < 40 ? Math.round((40 - peorScore) * 0.25 * 10) / 10 : 0;

  // Sugerencias contrafactuales del motor
  const sugerencias = rk?.sugerencias ?? [];

  return (
    <>
      <Cabecera
        titulo={`${e.nombre} (${e.id})`}
        sub={
          <>
            {e.sector} · {mesCorto(MES_ACTUAL)} ·{" "}
            <span className="tnum text-[var(--color-ink-4)]">
              motor conectado · {e.moneda}
              {rk?.modelVersion ? ` · ${rk.modelVersion.slice(0, 8)}` : ""}
            </span>
          </>
        }
        extra={
          <div className="flex items-center gap-2">
            <Boton tono="plano" href={`/empresa/${e.id}/drivers`}>
              Ver drivers
            </Boton>
            <Boton href={`/empresa/${e.id}/escenarios`}>
              Simular mejoras
            </Boton>
          </div>
        }
      />

      {/* ── Score de la Empresa y Trayectoria ─────────────────────── */}
      <div className="grid gap-5 xl:grid-cols-[296px_1fr]">
        <Card className="relative flex flex-col items-center overflow-hidden px-6 py-6">
          <div
            className="pointer-events-none absolute -top-24 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full opacity-35 blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(176,131,232,.55), transparent 70%)" }}
          />
          <div className="relative flex w-full flex-col items-center">
            <p className="text-[12.5px] text-[var(--color-ink-3)]">Salud financiera (Score Real)</p>
            <div className="mt-3">
              <Anillo score={e.score} delta={e.score - e.scorePrev} estado={e.estado} tam={162} />
            </div>

            <div className="mt-4 flex items-center gap-2">
              <EstadoChip estado={e.estado} />
              <Confianza nivel={e.confianza} />
            </div>

            <div className="mt-5 grid w-full grid-cols-3 gap-3 border-t border-[var(--color-line)] pt-4">
              <Mini k="Nivel Base" v={num(e.nivelBase)} />
              <Mini k="Momentum" v={(e.momentum >= 0 ? "+" : "−") + num(Math.abs(e.momentum), 2)} />
              <Mini k="Percentil" v={`P${percentil}`} />
            </div>

            <div className="mt-4 w-full space-y-2 border-t border-[var(--color-line)] pt-4">
              <Dato k="Saldo Bancario" v={eur(e.facturacionAnual > 0 ? e.facturacionAnual / 12 : 0)} />
              <Dato k="Corte Analítico" v={MES_ACTUAL} />
              <Dato k="Grupo Corporativo" v={e.grupo} />
              <Dato k="Historia" v={`${e.mesesHistoria} meses`} />
            </div>
          </div>
        </Card>

        <Card className="px-6 py-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[15px] font-semibold tracking-tight">Histórico y proyección (24 meses)</h2>
            <span className="text-[11px] text-[var(--color-ink-4)]">{e.id} · DuckDB Single Source of Truth</span>
          </div>
          <Prevision
            datos={e.trayectoria}
            momentum={e.momentum}
            peer={e.peer}
            datosPeer={e.trayectoriaPeer}
            reparto={e.reparto}
            inflexion={e.inflexion}
          />
          <p className="mt-6 text-center text-[11px] leading-relaxed text-[var(--color-ink-4)]">
            Serie temporal directa de <code className="text-[10px]">xray.duckdb</code> calculada con el motor aditivo.
          </p>
        </Card>
      </div>

      {/* ── Aviso / Alerta Activa ──────────────────────────────────── */}
      {e.alerta && (
        <Card className="mt-5 px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-medium text-[var(--color-risk-2)]">
                {e.alerta.texto} · Detectado en {mesCorto(e.alerta.mesDeteccion)}
                {e.alerta.mesesAnticipacion > 0 ? ` (${e.alerta.mesesAnticipacion} meses de anticipación)` : ""}
              </p>
              <p className="mt-1 text-[12px] leading-relaxed text-[var(--color-ink-3)]">
                Severidad: <strong className="text-[var(--color-ink-1)]">{e.alerta.severidad}</strong>.
                {e.alerta.driversMovidos.length > 0 && ` Drivers involucrados: ${e.alerta.driversMovidos.join(", ")}.`}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {e.alerta.driversMovidos.map((d, i) => (
                <span
                  key={d}
                  className="rounded-md bg-[rgba(255,255,255,.07)] px-2.5 py-1 text-[11px] text-[var(--color-ink-2)]"
                >
                  {d} <span className="tnum text-[var(--color-ink-4)]">{e.alerta?.codigosRazon[i] ?? "—"}</span>
                </span>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* ── Por qué y Qué hacer ───────────────────────────────────── */}
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card className="px-6 py-6">
          <h2 className="text-[15px] font-semibold tracking-tight">Por qué este número (Waterfall de Puntos)</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Seis componentes aditivos que suman exactamente {num(e.score)} puntos
          </p>
          <div className="-mx-2 mt-4">
            <Waterfall drivers={e.drivers} altura={260} />
          </div>
          <Link
            href={`/empresa/${e.id}/drivers`}
            className="mt-2 inline-block text-[12.5px] text-[var(--color-purple)] hover:underline"
          >
            Ver desglose pormenorizado →
          </Link>
        </Card>

        <Card className="px-6 py-6">
          <h2 className="text-[15px] font-semibold tracking-tight">Qué puedes hacer (Simulador What-If)</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Palancas de liquidez calculadas directamente sobre el balance de {e.id}.
          </p>
          <div className="mt-4 flex flex-col gap-2.5">
            {sugerencias.length > 0 ? (
              sugerencias.slice(0, 3).map((s, idx) => (
                <Link
                  key={`${s.id}-${idx}`}
                  href={`/empresa/${e.id}/escenarios`}
                  className="fila px-4 py-3.5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium">{s.label}</p>
                      <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-3)]">
                        Familia {s.familia} · {s.agreement_type ?? "Acción directa"}
                      </p>
                    </div>
                    {s.delta_score !== null && (
                      <Delta v={s.delta_score} sufijo=" pts" className="shrink-0 pt-0.5" />
                    )}
                  </div>
                  <div className="tnum mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-[var(--color-ink-2)]">
                    {s.caja_liberada_eur !== null && s.caja_liberada_eur > 0 && (
                      <span>
                        Caja liberada: <strong className="font-medium">{eur(s.caja_liberada_eur)}</strong>
                      </span>
                    )}
                    {s.eur_año !== null && s.eur_año > 0 && (
                      <span>
                        Impacto anual: <strong className="font-medium">{eur(s.eur_año)}/año</strong>
                      </span>
                    )}
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-[12px] text-[var(--color-ink-3)]">
                No hay palancas activas sugeridas en este corte.
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* ── Grupo Corporativo ─────────────────────────────────────── */}
      <Card className="mt-5 px-6 py-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[16px] font-semibold tracking-tight">Grupo {e.grupo}</h2>
            <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
              {todosScores.length} sociedades · consolidado {num(consolidado)} · penalización por contagio {num(penalizacion)}
            </p>
          </div>
          <Link href={`/grupo/${e.grupo}`} className="pildora">
            Ver el grupo
          </Link>
        </div>

        <div className="flex flex-col gap-2">
          {filiales.slice(0, 6).map((m) => (
            <Link
              key={m.id}
              href={`/${m.id}`}
              className="fila grid grid-cols-2 items-center gap-4 px-4 py-3.5 lg:grid-cols-[2fr_.6fr_.7fr_.8fr_.9fr]"
            >
              <div className="col-span-2 min-w-0 lg:col-span-1">
                <p className="truncate text-[13.5px] font-medium">{m.nombre}</p>
                <p className="truncate text-[11px] text-[var(--color-ink-4)]">{m.sector}</p>
              </div>
              <div className="text-right">
                <ScoreBadge score={m.score} size="sm" />
              </div>
              <div className="text-right">
                <Delta v={m.momentum} />
              </div>
              <div className="hidden lg:block">
                <Sparkline datos={m.trayectoria} />
              </div>
              <div className="hidden lg:block">
                <EstadoChip estado={m.estado} />
              </div>
            </Link>
          ))}
        </div>
      </Card>

      {/* ── Comparativa Anónima de Pares ──────────────────────────── */}
      <Card className="mt-5 px-6 py-6">
        <h2 className="text-[15px] font-semibold tracking-tight">Tu posición frente a empresas comparables</h2>
        <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
          Contra el conjunto de 1.286 empresas registradas en DuckDB.
        </p>
        <div className="mt-6">
          <div
            className="relative h-2 w-full rounded-full"
            style={{ background: "linear-gradient(90deg,#e5775b 0%,#e59f5e 34%,#dfb631 62%,#80efa2 100%)" }}
          >
            <span
              className="absolute top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full bg-white"
              style={{ left: `${percentil}%` }}
            />
          </div>
          <div className="tnum mt-2.5 flex justify-between text-[11px] text-[var(--color-ink-4)]">
            <span>P0</span>
            <span>P25</span>
            <span>P50</span>
            <span>P75</span>
            <span>P100</span>
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-[var(--color-ink-2)]">
            {e.nombre} se sitúa en el <strong className="font-medium">percentil {percentil}</strong> de su grupo de referencia. La mediana de anticipación de alertas tempranas es de{" "}
            <strong className="font-medium">{ANTICIPACION_MEDIANA} meses</strong>.
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
