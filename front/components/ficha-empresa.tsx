/**
 * Ficha de una empresa. La misma para las dos audiencias:
 *  - vista "empresa": X-Ray como módulo que compra una empresa para verse a sí misma (/COMP_xxxx).
 *  - vista "embat":   la misma ficha leída desde Embat, con la lectura de cartera (/embat/COMP_xxxx).
 */
import Link from "next/link";
import { notFound } from "next/navigation";
import { MES_ACTUAL } from "@/lib/data";
import { eur, num, mesCorto, banda } from "@/lib/format";
import { cargarEmpresa, cargarRecomendaciones, cargarFiliales, cargarTrayectoriasFiliales, cargarPrevision, nombreDe } from "@/lib/motor";
import { SEGMENTOS, segmentoDe } from "@/lib/cartera";
import { Cabecera } from "@/components/shell";
import { Anillo } from "@/components/anillo";
import { Prevision } from "@/components/prevision";
import { Card, ScoreBadge, EstadoChip, Confianza, Delta, Boton, KPI } from "@/components/ui";
import { Palancas } from "@/components/palancas";
import { Desglose } from "@/components/desglose";
import { ListaGrupo } from "@/components/grupo";

export type Vista = "empresa" | "embat";

export function normalizarId(raw: string): string | null {
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

export async function FichaEmpresa({ id, vista }: { id: string; vista: Vista }) {
  const idNormalizado = normalizarId(id);
  if (!idNormalizado) {
    notFound();
  }

  // Carga del motor real DuckDB + FastAPI
  const e = await cargarEmpresa(idNormalizado);
  if (!e) {
    notFound();
  }

  const embat = vista === "embat";
  const segmento = segmentoDe(e);
  const seg = segmento ? SEGMENTOS[segmento] : null;

  const [rk, rawFiliales, proyeccion] = await Promise.all([
    cargarRecomendaciones(e.id),
    cargarFiliales(e.grupo, e.id),
    cargarPrevision(e.id),
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

  const trayectorias = await cargarTrayectoriasFiliales(filiales.map((f) => f.id), 12);
  const filialesLista = filiales.map((f) => ({
    id: f.id, nombre: f.nombre, score: f.score, momentum: f.momentum,
    evaluable: f.mesesHistoria >= 12,
    trayectoria: trayectorias[f.id]?.length ? trayectorias[f.id] : f.trayectoria,
  }));

  // Métricas agregadas del grupo
  const todosScores = [e.score, ...filiales.map((f) => f.score)];
  const mediaGrupo = todosScores.reduce((a, b) => a + b, 0) / (todosScores.length || 1);
  const peorScore = Math.min(...todosScores);
  const consolidado = Math.round((0.65 * mediaGrupo + 0.35 * peorScore) * 10) / 10;
  const penalizacion = peorScore < 40 ? Math.round((40 - peorScore) * 0.25 * 10) / 10 : 0;

  // Sugerencias contrafactuales del motor y What-If
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

  const whatif = rk?.whatif ?? null;

  return (
    <>
      <Cabecera
        titulo={embat ? `Cliente ${e.nombre}` : `${e.nombre} (${e.id})`}
        sub={
          <>
            {embat ? <>{e.id} · Grupo {e.grupo.replace("GROUP_", "")} · </> : <>{e.sector} · </>}
            {mesCorto(MES_ACTUAL)} ·{" "}
            <span className="tnum text-[var(--color-ink-4)]">
              motor conectado · {e.moneda}
              {rk?.modelVersion ? ` · ${rk.modelVersion.slice(0, 8)}` : ""}
            </span>
          </>
        }
        extra={
          <div className="flex items-center gap-2">
            {embat && (
              <Boton tono="plano" href="/">
                ← Cartera
              </Boton>
            )}
            <Boton tono="plano" href={`/empresa/${e.id}/drivers`}>
              Ver drivers
            </Boton>
            <Boton href={`/empresa/${e.id}/escenarios`}>
              Simular mejoras
            </Boton>
          </div>
        }
      />

      {/* ── Lectura para Embat: qué hacer con este cliente ────────── */}
      {embat && (
        <Card className="mb-5 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[15px] font-semibold tracking-tight">Lectura para Embat</p>
                {seg ? (
                  <span className="rounded-md px-2 py-0.5 text-[11px] font-medium" style={{ background: seg.bg, color: seg.color }}>
                    {seg.label}
                  </span>
                ) : (
                  <span className="rounded-md bg-[var(--color-surface-3)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-ink-3)]">
                    Sin acción
                  </span>
                )}
                {e.elegible === false && (
                  <span className="text-[11px] text-[var(--color-ink-4)]">historia insuficiente para estado</span>
                )}
              </div>
              <p className="mt-1.5 max-w-2xl text-[12.5px] leading-relaxed text-[var(--color-ink-2)]">
                {seg?.accion ?? "Cliente estable sin señal de cambio. No hay motivo para mover ficha: se sigue observando."}
              </p>
            </div>
            <div className="tnum grid grid-cols-3 gap-5 text-center">
              <div>
                <p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Score</p>
                <p className="mt-1"><ScoreBadge score={e.score} /></p>
              </div>
              <div>
                <p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Δ 3 meses</p>
                <p className="mt-2"><Delta v={e.delta3m ?? 0} sufijo=" pts" /></p>
              </div>
              <div>
                <p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Estado</p>
                <p className="mt-2"><EstadoChip estado={e.estado} /></p>
              </div>
            </div>
          </div>
          {whatif && (
            <p className="mt-3 border-t border-[var(--color-line)] pt-3 text-[12px] text-[var(--color-ink-3)]">
              Producto Embat con más efecto sobre su score:{" "}
              <strong className="font-medium text-[var(--color-ink-1)]">{whatif.recommended_product}</strong>
              {" "}· {eur(whatif.injection_amount)} → {num(whatif.projected_score)} pts ({whatif.delta_score >= 0 ? "+" : ""}{num(whatif.delta_score)}).
            </p>
          )}
        </Card>
      )}

      {/* ── Métricas Operativas de Circulante y Tesorería ───────────── */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 mb-5">
        <KPI
          etiqueta="Días de Caja (Runway)"
          valor={`${num(e.diasCaja, 1)} d`}
          nota={e.diasCaja < 15 ? "Liquidez tensionada (<15d)" : "Colchón de tesorería suficiente"}
        />
        <KPI
          etiqueta="DSO (Plazo medio cobro)"
          valor={`${num(e.dso, 1)} d`}
          nota="Periodo medio clientes"
        />
        <KPI
          etiqueta="DPO (Plazo medio pago)"
          valor={`${num(e.dpo, 1)} d`}
          nota="Periodo medio proveedores"
        />
        <KPI
          etiqueta="Facturación Anual"
          valor={eur(e.facturacionAnual)}
          nota="Volumen anualizado observado"
        />
      </div>

      {/* ── Score de la Empresa y Trayectoria ─────────────────────── */}
      <div className="grid gap-5 xl:grid-cols-[296px_1fr]">
        <Card className="relative flex flex-col items-center overflow-hidden px-6 py-6">
          <div
            className="pointer-events-none absolute -top-24 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full opacity-35 blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(176,131,232,.55), transparent 70%)" }}
          />
          <div className="relative flex w-full flex-col items-center">
            <p className="text-[12.5px] text-[var(--color-ink-3)]">{embat ? "Salud financiera del cliente" : "Salud financiera (Score Real)"}</p>
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
              <Dato k="Saldo Bancario" v={eur(e.saldoBancario ?? (e.facturacionAnual > 0 ? e.facturacionAnual / 12 : 0))} />
              <Dato k="Días de Caja" v={`${num(e.diasCaja, 1)} días`} />
              <Dato k="DSO / DPO" v={`${num(e.dso, 1)} d / ${num(e.dpo, 1)} d`} />
              {e.utilizacionLinea > 0 && <Dato k="Utilización Línea" v={`${num(e.utilizacionLinea)}%`} />}
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
            proyeccion={proyeccion}
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

      {/* ── Por qué y qué hacer ────────────────────────────────────── */}
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card className="px-6 py-6">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <h2 className="text-[15px] font-semibold tracking-tight">Por qué este número</h2>
              <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
                Pulsa un factor para ver su diagnóstico
              </p>
            </div>
            <Link href={`/empresa/${e.id}/drivers`} className="text-[12px] text-[var(--color-purple)] hover:underline">
              Ver el detalle
            </Link>
          </div>
          <div className="mt-3"><Desglose drivers={e.drivers} score={e.score} /></div>
        </Card>

        <Card className="seccion-embat px-6 py-6">
          <h2 className="text-[15px] font-semibold tracking-tight">
            {embat ? "Qué podría hacer el cliente" : "Qué puedes hacer"}
          </h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Diagnóstico de tesorería y palancas calculadas sobre el balance de {e.id}.
          </p>
          <div className="mt-4">
            <Palancas
              empresa={e}
              sugerencias={rk?.sugerencias}
              palancas={rk?.palancas}
              whatif={whatif}
              recomendado={recomendada}
            />
          </div>
        </Card>
      </div>

      {/* ── Grupo Corporativo ─────────────────────────────────────── */}
      <Card className="mt-5 px-6 py-5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <div>
            <h2 className="text-[15px] font-semibold tracking-tight">{e.grupoNombre}</h2>
            <p className="tnum mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
              {todosScores.length} sociedades · media {num(mediaGrupo)}
              {penalizacion > 0 && <> · −{num(penalizacion)} de contagio</>}
            </p>
          </div>
          <div className="flex items-baseline gap-2.5">
            <span className="text-[11px] text-[var(--color-ink-3)]">consolidado</span>
            <span className="tnum text-[24px] font-semibold leading-none"
              style={{ color: banda(consolidado).color }}>{num(consolidado)}</span>
            <Link href={`/grupo/${e.grupo}`} className="ml-2 text-[11.5px] text-[var(--color-purple)] hover:underline">
              Ver el grupo
            </Link>
          </div>
        </div>

        <div className="mt-4 border-t border-[var(--color-line)] pt-2">
          <ListaGrupo filiales={filialesLista} base={embat ? "/embat" : ""} />
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
