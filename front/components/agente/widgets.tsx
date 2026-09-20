"use client";
/**
 * Widgets del asistente: cada herramienta del MCP tiene una manera de verse.
 *
 * El modelo no genera HTML. Elige qué datos pedir y aquí se decide cómo se
 * pintan, reutilizando los mismos componentes que el resto de X Ray para que
 * un score, un estado o una trayectoria se vean igual en el chat que en la
 * ficha. Si una herramienta no tiene widget, se muestra su JSON plegado.
 */
import Link from "next/link";
import type { Driver, Punto, Episodio } from "@/lib/data";
import { eur, num, mesCorto } from "@/lib/format";
import { nombreDe, driversDe } from "@/lib/motor";
import type { ApiEmpresa } from "@/lib/api";
import { SEGMENTOS, segmentoDe } from "@/lib/cartera";
import { datosDe, etiquetaHerramienta } from "@/lib/agente";
import { Card, KPI, ScoreBadge, EstadoChip, Delta } from "@/components/ui";
import { Histograma, Trayectoria } from "@/components/charts";
import { Anillo } from "@/components/anillo";
import { Desglose } from "@/components/desglose";
import { EpisodiosPanel } from "@/components/episodios";
import { Prevision } from "@/components/prevision";

// ── Formas que devuelve el MCP (recortadas en backend/mcp_server.py) ────────
type Fila = {
  company_id: string; group_id: string; erp?: string | null; score: number; state: string;
  delta_3m: number; momentum: number; state_eligible: boolean; segment?: string | null;
};
type PuntoMcp = { mes: string; score: number; base_health: number; state: string; momentum: number };

const puntos = (h: PuntoMcp[] | undefined): Punto[] => (h ?? []).map((p) => ({ mes: p.mes, score: p.score, nivel: p.base_health }));
const grupoCorto = (g: string) => g.replace("GROUP_", "Grupo ");

// ── Piezas comunes ─────────────────────────────────────────────────────────
function Titulo({ children, sub }: { children: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="mb-3">
      <h3 className="text-[13.5px] font-semibold tracking-tight">{children}</h3>
      {sub && <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">{sub}</p>}
    </div>
  );
}

function SegmentoChip({ f }: { f: Fila }) {
  const s = f.segment ?? segmentoDe({ score: f.score, estado: f.state, delta3m: f.delta_3m, elegible: f.state_eligible });
  if (!s || !(s in SEGMENTOS)) return null;
  const seg = SEGMENTOS[s as keyof typeof SEGMENTOS];
  return <span className="rounded-md px-1.5 py-0.5 text-[10.5px] font-medium" style={{ background: seg.bg, color: seg.color }}>{seg.label}</span>;
}

function FilaEmpresa({ f, puesto }: { f: Fila; puesto?: number }) {
  return (
    <Link href={`/embat/${f.company_id}`} className="fila grid grid-cols-[auto_1fr_auto_auto] items-center gap-3 px-3 py-2 hover:bg-[rgba(255,255,255,.08)]">
      {puesto !== undefined ? <span className="tnum w-4 text-[11px] text-[var(--color-ink-4)]">{puesto}</span> : <span className="w-0" />}
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium">{nombreDe(f.company_id)}</p>
        <p className="flex flex-wrap items-center gap-1.5 text-[10.5px] text-[var(--color-ink-4)]">
          <EstadoChip estado={f.state} /><SegmentoChip f={f} /><span>{grupoCorto(f.group_id)}</span>
        </p>
      </div>
      <Delta v={f.delta_3m} />
      {f.state_eligible ? <ScoreBadge score={f.score} size="sm" /> : <span className="tnum text-[13px] text-[var(--color-ink-4)]">{num(f.score, 0)}</span>}
    </Link>
  );
}

function ListaEmpresas({ items, numerar, vacio = "Ninguna empresa cumple el filtro." }: { items: Fila[]; numerar?: boolean; vacio?: string }) {
  if (!items.length) return <p className="py-3 text-center text-[12px] text-[var(--color-ink-4)]">{vacio}</p>;
  return <div className="flex flex-col gap-1.5">{items.map((f, i) => <FilaEmpresa key={f.company_id} f={f} puesto={numerar ? i + 1 : undefined} />)}</div>;
}

function Dato({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-[rgba(255,255,255,.04)] px-3 py-2">
      <p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
      <p className="tnum mt-0.5 text-[13px] font-medium">{v}</p>
    </div>
  );
}

// ── Widgets ────────────────────────────────────────────────────────────────
type Resumen = {
  as_of: string; total_companies: number; eligible_companies: number; average_score: number; median_score: number;
  risk_companies_count: number; improving_companies_count: number; alerts_last_month: number;
  distribution_by_state: Record<string, number>; histogram: Array<{ bucket: number; count: number }>;
  top_score: Fila[]; top_growth: Fila[]; top_decline: Fila[];
  segments: Array<{ key: string; label: string; action: string; count: number; items: Fila[] }>;
};
function WResumen({ d }: { d: Resumen }) {
  return (
    <div>
      <Titulo sub={`${num(d.total_companies, 0)} clientes · ${num(d.eligible_companies, 0)} con score · corte ${mesCorto(d.as_of.slice(0, 7))}`}>Cartera Embat</Titulo>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <KPI etiqueta="Score medio" valor={num(d.average_score)} nota={`mediana ${num(d.median_score)}`} />
        <KPI etiqueta="En mejora" valor={num(d.improving_companies_count, 0)} />
        <KPI etiqueta="En riesgo" valor={num(d.risk_companies_count, 0)} nota="bache, torciéndose o deterioro" />
        <KPI etiqueta="Alertas del mes" valor={num(d.alerts_last_month, 0)} />
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <Histograma datos={d.histogram} altura={150} />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(d.distribution_by_state).map(([st, n]) => (
              <span key={st} className="flex items-center gap-1.5 rounded-md bg-[rgba(255,255,255,.05)] px-2 py-1">
                <EstadoChip estado={st} /><span className="tnum text-[11px] text-[var(--color-ink-3)]">{num(n, 0)}</span>
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          {d.segments.map((s) => {
            const seg = SEGMENTOS[s.key as keyof typeof SEGMENTOS];
            return (
              <div key={s.key} className="flex items-center justify-between rounded-xl bg-[rgba(255,255,255,.04)] px-3 py-2">
                <div className="min-w-0">
                  <span className="rounded-md px-2 py-0.5 text-[11px] font-semibold" style={{ background: seg?.bg, color: seg?.color }}>{seg?.label ?? s.label}</span>
                  <p className="mt-1 truncate text-[11px] text-[var(--color-ink-3)]">{s.action}</p>
                </div>
                <span className="tnum text-[22px] font-medium" style={{ color: seg?.color }}>{num(s.count, 0)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function WBusqueda({ d }: { d: { total: number; items: Fila[] } }) {
  return (
    <div>
      <Titulo sub={`${num(d.total, 0)} cumplen el filtro · se muestran ${d.items.length}`}>Empresas</Titulo>
      <ListaEmpresas items={d.items} numerar />
    </div>
  );
}

type Alerta = { alert_id: string; company_id: string; group_id: string; as_of: string; state: string; severity: string; direction: string; score: number; delta_score: number; drivers: Array<{ field: string; delta_points: number }> };
function WAlertas({ d }: { d: { total?: number; items: Alerta[] } }) {
  const color = (s: string) => (s === "ALTA" ? "#e5775b" : s === "MEDIA" ? "#e59f5e" : "var(--color-ink-3)");
  return (
    <div>
      <Titulo sub={d.total != null ? `${num(d.total, 0)} alertas · se muestran ${d.items.length}` : undefined}>Alertas del monitor</Titulo>
      {!d.items.length && <p className="py-3 text-center text-[12px] text-[var(--color-ink-4)]">Sin alertas con ese filtro.</p>}
      <div className="flex flex-col gap-1.5">
        {d.items.map((a) => (
          <Link key={a.alert_id} href={`/embat/${a.company_id}`} className="fila grid grid-cols-[1fr_auto_auto] items-center gap-3 px-3 py-2 hover:bg-[rgba(255,255,255,.08)]">
            <div className="min-w-0">
              <p className="flex flex-wrap items-center gap-1.5 text-[13px] font-medium">
                {nombreDe(a.company_id)}
                <span className="rounded-md px-1.5 py-0.5 text-[10.5px] font-semibold" style={{ color: color(a.severity), background: "rgba(255,255,255,.06)" }}>{a.severity}</span>
              </p>
              <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10.5px] text-[var(--color-ink-4)]">
                <EstadoChip estado={a.state} /><span>{mesCorto(a.as_of.slice(0, 7))}</span>
                {a.drivers[0] && <span>· {a.drivers[0].field.replace(/_/g, " ")} {a.drivers[0].delta_points > 0 ? "+" : ""}{num(a.drivers[0].delta_points)}</span>}
              </p>
            </div>
            <Delta v={a.delta_score} />
            <ScoreBadge score={a.score} size="sm" />
          </Link>
        ))}
      </div>
    </div>
  );
}

type Ficha = ApiEmpresa & {
  total_balance: number | null; overdue_invoices_count: number; overdue_invoices_amount: number; total_pending_amount: number;
  suggested_action: string | null; dso: number; dpo: number; dias_caja: number; annual_revenue: number; line_utilization: number;
  latest_alert: { as_of: string; state: string; severity: string; score: number; delta_score: number } | null;
  episodio_destacado: { direccion: string; deteccion: string; estado_confirmacion: string; meses_anticipacion: number | null; texto: string } | null;
};
function WFicha({ d }: { d: Ficha }) {
  const drivers: Driver[] = driversDe(d.waterfall, d);
  const seg = segmentoDe({ score: d.score, estado: d.state, delta3m: d.delta_3m, elegible: d.state_eligible });
  return (
    <div>
      <div className="flex flex-wrap items-center gap-5">
        <Anillo score={d.score} tam={136} grosor={8} estado={d.state} />
        <div className="min-w-0 flex-1">
          <Link href={`/embat/${d.company_id}`} className="text-[16px] font-semibold tracking-tight hover:underline">{nombreDe(d.company_id)}</Link>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">{d.company_id} · {grupoCorto(d.group_id)}{d.erp ? ` · ERP ${d.erp}` : " · sin ERP"} · corte {mesCorto(d.as_of.slice(0, 7))}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <EstadoChip estado={d.state} />
            {seg && <span className="rounded-md px-2 py-0.5 text-[11px] font-medium" style={{ background: SEGMENTOS[seg].bg, color: SEGMENTOS[seg].color }}>{SEGMENTOS[seg].label}</span>}
            <span className="text-[11.5px] text-[var(--color-ink-3)]">Δ 3 m</span><Delta v={d.delta_3m} />
          </div>
          {d.suggested_action && <p className="mt-2 text-[12px] leading-relaxed text-[var(--color-ink-2)]">{d.suggested_action}</p>}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <Dato k="Saldo" v={d.total_balance != null ? eur(d.total_balance, true) : "—"} />
        <Dato k="Vencidas" v={`${num(d.overdue_invoices_count, 0)} · ${eur(d.overdue_invoices_amount, true)}`} />
        <Dato k="DSO" v={`${num(d.dso, 0)} d`} />
        <Dato k="DPO" v={`${num(d.dpo, 0)} d`} />
        <Dato k="Días de caja" v={num(d.dias_caja, 0)} />
        <Dato k="Línea usada" v={`${num(d.line_utilization, 0)} %`} />
      </div>
      <div className="mt-3">
        <p className="mb-1 text-[11px] uppercase tracking-wider text-[var(--color-ink-4)]">De dónde sale el score</p>
        <Desglose drivers={drivers} score={d.score} />
      </div>
      {d.episodio_destacado && (
        <p className="mt-3 rounded-xl bg-[rgba(255,255,255,.04)] px-3 py-2 text-[12px] leading-relaxed text-[var(--color-ink-2)]">
          <span className="font-medium" style={{ color: d.episodio_destacado.direccion === "deterioro" ? "var(--color-warm)" : "#80efa2" }}>Episodio de {d.episodio_destacado.direccion}</span>
          {" · "}{d.episodio_destacado.texto}
        </p>
      )}
    </div>
  );
}

function WHistoria({ d }: { d: { company_id: string; history: PuntoMcp[] } }) {
  const p = puntos(d.history);
  return (
    <div>
      <Titulo sub={`${p.length} meses · score mes a mes`}>Trayectoria de {nombreDe(d.company_id)}</Titulo>
      <Trayectoria datos={p} altura={200} />
    </div>
  );
}

function WEpisodios({ d }: { d: { company_id: string; episodios: Episodio[]; episodio_destacado: number | null; history: PuntoMcp[] } }) {
  if (!d.episodios?.length) {
    return (<div><Titulo>Episodios de {nombreDe(d.company_id)}</Titulo><p className="text-[12px] text-[var(--color-ink-4)]">El motor no ha detectado cambios de régimen en esta empresa.</p></div>);
  }
  return (
    <div>
      <Titulo sub={`${d.episodios.length} ${d.episodios.length === 1 ? "episodio" : "episodios"} detectados`}>Episodios de {nombreDe(d.company_id)}</Titulo>
      <EpisodiosPanel episodios={d.episodios} destacado={d.episodio_destacado} trayectoria={puntos(d.history)} />
    </div>
  );
}

function WComparables({ d }: { d: { company_id: string; quartile: number; label: string; n_companies: number; peer_history: Array<{ mes: string; mediana: number }>; history: PuntoMcp[] } }) {
  const propios = puntos(d.history);
  const pares: Punto[] = d.peer_history.map((p) => ({ mes: p.mes, score: p.mediana, nivel: p.mediana }));
  // Alinear por mes: la Trayectoria empareja por índice.
  const porMes = new Map(pares.map((p) => [p.mes, p]));
  const alineados = propios.map((p) => porMes.get(p.mes) ?? { mes: p.mes, score: NaN, nivel: NaN });
  return (
    <div>
      <Titulo sub={`${d.label} · ${num(d.n_companies, 0)} empresas en el cuartil ${d.quartile}`}>{nombreDe(d.company_id)} frente a sus pares</Titulo>
      <Trayectoria datos={propios} comparador={{ nombre: "Mediana del cuartil", datos: alineados }} altura={200} />
    </div>
  );
}

type Factura = { invoice_id: string; issue_date: string | null; due_date: string | null; paid_date: string | null; total_amount: number; pending_amount: number; status: string; counterparty_id: string | null; concept: string | null };
function WFacturas({ d }: { d: { company_id: string; total: number; overdue_count: number; total_pending_amount: number; invoices: Factura[] } }) {
  const estado = (s: string) => (s === "overdue" ? "Vencida" : s === "pending" ? "Pendiente" : s === "paid" ? "Pagada" : s);
  return (
    <div>
      <Titulo sub={`${num(d.total, 0)} facturas · ${num(d.overdue_count, 0)} vencidas · ${eur(d.total_pending_amount)} pendientes`}>Facturas de {nombreDe(d.company_id)}</Titulo>
      <Tabla cab={["Factura", "Vence", "Estado", "Importe", "Pendiente"]}
        filas={d.invoices.map((f) => [f.invoice_id, f.due_date ?? "—", estado(f.status), eur(f.total_amount), eur(f.pending_amount)])}
        derecha={[3, 4]} />
    </div>
  );
}

type Grupo = { group_id: string; erp: string | null; company_count: number; average_score: number; consolidated_score: number; contagion_penalty: number; worst_company_id: string; best_company_id: string; risk_companies_count: number; companies: Fila[] };
function WGrupo({ d }: { d: Grupo }) {
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Titulo sub={`${num(d.company_count, 0)} sociedades · ${num(d.risk_companies_count, 0)} en riesgo${d.erp ? ` · ERP ${d.erp}` : ""}`}>
          <Link href={`/grupo/${d.group_id}`} className="hover:underline">{grupoCorto(d.group_id)}</Link>
        </Titulo>
        <div className="flex items-center gap-4">
          <div className="text-right"><p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Consolidado</p><ScoreBadge score={d.consolidated_score} /></div>
          <div className="text-right"><p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Media</p><ScoreBadge score={d.average_score} /></div>
        </div>
      </div>
      <ListaEmpresas items={[...d.companies].sort((a, b) => a.score - b.score)} />
    </div>
  );
}

type Flujos = { group_id: string; nodes: Array<{ company_id: string; score: number; state: string; delta_3m: number; eur_out: number; eur_in: number }>; edges: Array<{ source: string; target: string; matches: number; eur: number; last_date: string }>; edges_total: number };
function WFlujos({ d }: { d: Flujos }) {
  return (
    <div>
      <Titulo sub={`${d.nodes.length} sociedades · ${num(d.edges_total, 0)} flujos detectados · mismo día, mismo importe`}>
        Flujos dentro de <Link href={`/grafo`} className="hover:underline">{grupoCorto(d.group_id)}</Link>
      </Titulo>
      <div className="grid gap-3 lg:grid-cols-2">
        <Tabla cab={["Sociedad", "Score", "Sale", "Entra"]}
          filas={[...d.nodes].sort((a, b) => (b.eur_out + b.eur_in) - (a.eur_out + a.eur_in)).slice(0, 12).map((n) => [nombreDe(n.company_id), num(n.score, 0), eur(n.eur_out, true), eur(n.eur_in, true)])}
          derecha={[1, 2, 3]} />
        <Tabla cab={["De", "A", "Movs.", "Euros"]}
          filas={d.edges.slice(0, 12).map((e) => [nombreDe(e.source), nombreDe(e.target), num(e.matches, 0), eur(e.eur, true)])}
          derecha={[2, 3]} />
      </div>
    </div>
  );
}

type WhatIf = { company_id: string; current_score: number; current_state: string; projected_score: number; projected_state: string; delta_score: number; injection_amount: number; is_optimal_computed: boolean; liquidity_gain: number; fragility_gain: number; collections_gain: number; recommended_product: string; product_rationale: string };
function WWhatIf({ d }: { d: WhatIf }) {
  return (
    <div>
      <Titulo sub={`${nombreDe(d.company_id)} · inyección de ${eur(d.injection_amount)}${d.is_optimal_computed ? " (tramo mínimo calculado por el motor)" : ""}`}>Qué pasaría si</Titulo>
      <div className="flex flex-wrap items-center gap-6">
        <div><p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Hoy</p><ScoreBadge score={d.current_score} size="lg" /><div className="mt-1"><EstadoChip estado={d.current_state} /></div></div>
        <span className="text-[28px] text-[var(--color-ink-4)]" aria-hidden>→</span>
        <div><p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Con la inyección</p><ScoreBadge score={d.projected_score} size="lg" /><div className="mt-1 flex items-center gap-2"><EstadoChip estado={d.projected_state} /><Delta v={d.delta_score} sufijo=" pts" /></div></div>
        <div className="grid grid-cols-3 gap-2">
          <Dato k="Liquidez" v={<Delta v={d.liquidity_gain} />} />
          <Dato k="Fragilidad" v={<Delta v={d.fragility_gain} />} />
          <Dato k="Cobros" v={<Delta v={d.collections_gain} />} />
        </div>
      </div>
      {d.recommended_product && (
        <p className="mt-3 rounded-xl bg-[rgba(176,131,232,.10)] px-3 py-2 text-[12px] leading-relaxed text-[var(--color-ink-2)] ring-1 ring-[rgba(176,131,232,.18)]">
          <span className="font-semibold text-[var(--color-purple)]">{d.recommended_product}</span>{d.product_rationale ? ` · ${d.product_rationale}` : ""}
        </p>
      )}
    </div>
  );
}

type Sugerencia = { id: string; familia?: string; label?: string; delta_score?: number; caja_liberada_eur?: number; eur_año?: number; days?: number; pct?: number; agreement_type?: string };
function WPalancas({ d }: { d: { company_id: string; sugerencias: Sugerencia[]; recomendado: Sugerencia | null } }) {
  const detalle = (s: Sugerencia) => s.agreement_type ? `acuerdo: ${s.agreement_type.replace(/_/g, " ")}` : s.days != null ? `${s.days} días` : s.pct != null ? `${Math.round(s.pct * 100)} %` : s.familia ?? "";
  const max = Math.max(...d.sugerencias.map((s) => Math.abs(s.delta_score ?? 0)), 0.01);
  return (
    <div>
      <Titulo sub={`${d.sugerencias.length} palancas aplicables, por puntos de score que aportan`}>Palancas para {nombreDe(d.company_id)}</Titulo>
      {!d.sugerencias.length && <p className="text-[12px] text-[var(--color-ink-4)]">El motor no encuentra palancas aplicables con los datos de esta empresa.</p>}
      <div className="flex flex-col gap-1.5">
        {d.sugerencias.map((s, i) => {
          const reco = d.recomendado?.id === s.id;
          return (
            <div key={`${s.id}-${i}`} className={`rounded-xl px-3 py-2 ${reco ? "bg-[rgba(176,131,232,.10)] ring-1 ring-[rgba(176,131,232,.22)]" : "bg-[rgba(255,255,255,.04)]"}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="min-w-0 truncate text-[12.5px] font-medium">{s.label ?? s.id.replace(/_/g, " ")}{reco && <span className="ml-2 text-[10.5px] font-semibold text-[var(--color-purple)]">recomendada</span>}</p>
                <div className="flex items-center gap-3">
                  {s.caja_liberada_eur ? <span className="tnum text-[11.5px] text-[var(--color-ink-3)]">{eur(s.caja_liberada_eur, true)} de caja</span> : null}
                  <Delta v={s.delta_score ?? 0} sufijo=" pts" />
                </div>
              </div>
              <div className="mt-1.5 flex items-center gap-2">
                <div className="h-[4px] flex-1 overflow-hidden rounded-full bg-[rgba(255,255,255,.06)]"><div className="h-full rounded-full" style={{ width: `${(Math.abs(s.delta_score ?? 0) / max) * 100}%`, background: (s.delta_score ?? 0) >= 0 ? "#b083e8" : "#e59f5e" }} /></div>
                <span className="text-[10.5px] text-[var(--color-ink-4)]">{detalle(s)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

type Simulacion = { company_id: string; baseline: { score: number; state?: string | null }; projected: { score: number; state?: string | null }; delta_score: number | null; caja_liberada_eur: number; warnings: string[]; levers: Array<{ id: string; label?: string }> };
function WSimulacion({ d }: { d: Simulacion }) {
  return (
    <div>
      <Titulo sub={`${nombreDe(d.company_id)} · ${d.levers.map((l) => l.label ?? l.id.replace(/_/g, " ")).join(" + ")}`}>Simulación de palancas</Titulo>
      <div className="flex flex-wrap items-center gap-6">
        <div><p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Hoy</p><ScoreBadge score={d.baseline.score} size="lg" />{d.baseline.state && <div className="mt-1"><EstadoChip estado={String(d.baseline.state)} /></div>}</div>
        <span className="text-[28px] text-[var(--color-ink-4)]" aria-hidden>→</span>
        <div><p className="text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Con las palancas</p><ScoreBadge score={d.projected.score} size="lg" /><div className="mt-1 flex items-center gap-2">{d.projected.state && <EstadoChip estado={String(d.projected.state)} />}<Delta v={d.delta_score ?? d.projected.score - d.baseline.score} sufijo=" pts" /></div></div>
        <Dato k="Caja liberada" v={eur(d.caja_liberada_eur)} />
      </div>
      {d.warnings?.length > 0 && <ul className="mt-3 list-disc pl-5 text-[11.5px] text-[var(--color-ink-3)]">{d.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
    </div>
  );
}

type PrevisionMcp = { company_id: string; status: string; meses: number; current_score: number | null; alto: number[]; medio: number[]; bajo: number[]; history: PuntoMcp[] };
function WPrevision({ d }: { d: PrevisionMcp }) {
  const datos = puntos(d.history);
  const momentum = d.history.at(-1)?.momentum ?? 0;
  const completa = d.alto.length === d.meses && d.medio.length === d.meses && d.bajo.length === d.meses;
  return (
    <div>
      <Titulo sub={`Histórico y ${d.meses} meses proyectados en tres escenarios${completa ? "" : " · el motor no ha podido proyectar esta empresa"}`}>Previsión de {nombreDe(d.company_id)}</Titulo>
      <Prevision datos={datos} momentum={momentum} proyeccion={completa ? { alto: d.alto, medio: d.medio, bajo: d.bajo } : null} meses={d.meses} alto={260} />
    </div>
  );
}

function Tabla({ cab, filas, derecha = [] }: { cab: string[]; filas: React.ReactNode[][]; derecha?: number[] }) {
  if (!filas.length) return <p className="py-3 text-center text-[12px] text-[var(--color-ink-4)]">Sin filas.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead><tr className="text-left text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">{cab.map((c, i) => <th key={c} className={`px-2 py-1.5 font-medium ${derecha.includes(i) ? "text-right" : ""}`}>{c}</th>)}</tr></thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i} className="border-t border-[var(--color-line)]">
              {f.map((c, j) => <td key={j} className={`tnum px-2 py-1.5 ${derecha.includes(j) ? "text-right" : ""}`}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Registro ───────────────────────────────────────────────────────────────
/* eslint-disable @typescript-eslint/no-explicit-any */
const REGISTRO: Record<string, (p: { d: any }) => React.ReactElement> = {
  resumen_cartera: WResumen,
  buscar_empresas: WBusqueda,
  alertas: WAlertas,
  ficha_empresa: WFicha,
  historia_empresa: WHistoria,
  episodios_empresa: WEpisodios,
  comparables_empresa: WComparables,
  facturas_empresa: WFacturas,
  grupo: WGrupo,
  flujos_intragrupo: WFlujos,
  que_pasaria_si: WWhatIf,
  palancas: WPalancas,
  simular_palancas: WSimulacion,
  prevision_estructural: WPrevision,
};
/* eslint-enable @typescript-eslint/no-explicit-any */

/** Un resultado de herramienta, ya en su Card. */
export function Widget({ herramienta, output, input }: { herramienta: string; output: unknown; input?: unknown }) {
  const { datos, error } = datosDe(output);
  const et = etiquetaHerramienta(herramienta);
  if (error || !datos) {
    return (
      <Card className="px-4 py-3">
        <p className="text-[12px] text-[var(--color-warm)]">{et.titulo}: {error ?? "sin datos"}</p>
      </Card>
    );
  }
  const Comp = REGISTRO[herramienta];
  return (
    <Card className="px-5 py-4">
      {Comp ? <Comp d={datos} /> : (
        <details>
          <summary className="cursor-pointer text-[12.5px] font-medium">{et.titulo}</summary>
          <pre className="mt-2 max-h-72 overflow-auto text-[11px] text-[var(--color-ink-3)]">{JSON.stringify(datos, null, 2)}</pre>
        </details>
      )}
      <p className="mt-3 text-[10.5px] text-[var(--color-ink-4)]">
        {et.titulo}{input && typeof input === "object" && Object.keys(input as object).length > 0 ? ` · ${resumenEntrada(input as Record<string, unknown>)}` : ""} · motor X Ray
      </p>
    </Card>
  );
}

function resumenEntrada(i: Record<string, unknown>) {
  return Object.entries(i).filter(([, v]) => v != null && v !== "").map(([k, v]) => `${k} ${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(", ").slice(0, 120);
}

/** Mientras la herramienta corre. */
export function WidgetCargando({ herramienta }: { herramienta: string }) {
  return (
    <div className="fila flex items-center gap-3 px-4 py-3">
      <span className="h-2 w-2 flex-none animate-pulse rounded-full bg-[var(--color-purple)]" />
      <span className="text-[12.5px] text-[var(--color-ink-3)]">{etiquetaHerramienta(herramienta).corriendo}…</span>
    </div>
  );
}
