/**
 * Home de Embat: la cartera entera de clientes vista con X-Ray.
 * Quién está sano, quién crece, quién se tuerce, y qué hacer con cada uno.
 */
import Link from "next/link";
import { apiPortfolio, apiEmpresas, type ApiPortfolioItem } from "@/lib/api";
import { nombreDe } from "@/lib/motor";
import { ESTADO_LABEL, type Estado } from "@/lib/data";
import { LAST_CLOSED_MONTH, mesDePunto } from "@/lib/calendar";
import { num, mesCorto } from "@/lib/format";
import { SEGMENTOS, segmentoDe, type Segmento } from "@/lib/cartera";
import { Cabecera } from "@/components/shell";
import { GaleriaEmpresas } from "@/components/galeria-empresas";
import { Histograma, Trayectoria } from "@/components/charts";
import { Card, KPI, ScoreBadge, EstadoChip, Delta, Vacio } from "@/components/ui";

const POR_PAGINA = 25;
const VISTA_PREVIA = 3;   // dos enteros y el tercero difuminado
const ORDENES = ["score", "delta_3m", "momentum", "company_id", "group_id"] as const;
const ESTADOS_FILTRO = ["MEJORANDO", "RECUPERACION", "ESTABLE", "BACHE", "TORCIENDOSE", "DETERIORO", "EVALUACION_PENDIENTE"];

type Filtros = { orden: string; dir: "asc" | "desc"; estado: string; q: string; pagina: number };

function leerFiltros(sp: Record<string, string | string[] | undefined>): Filtros {
  const uno = (k: string) => (Array.isArray(sp[k]) ? sp[k]![0] : sp[k]) ?? "";
  const orden = (ORDENES as readonly string[]).includes(uno("orden")) ? uno("orden") : "score";
  return {
    orden,
    dir: uno("dir") === "asc" ? "asc" : "desc",
    estado: ESTADOS_FILTRO.includes(uno("estado")) ? uno("estado") : "",
    q: uno("q").slice(0, 20),
    pagina: Math.max(1, parseInt(uno("pagina") || "1", 10) || 1),
  };
}

function urlCon(f: Filtros, cambios: Partial<Filtros>) {
  const n = { ...f, ...cambios };
  const p = new URLSearchParams();
  if (n.orden !== "score") p.set("orden", n.orden);
  if (n.dir !== "desc") p.set("dir", n.dir);
  if (n.estado) p.set("estado", n.estado);
  if (n.q) p.set("q", n.q);
  if (n.pagina > 1) p.set("pagina", String(n.pagina));
  const qs = p.toString();
  return `/${qs ? `?${qs}` : ""}#cartera`;
}

const etiquetaEstado = (st: string) => ESTADO_LABEL[st as Estado] ?? (st === "EVALUACION_PENDIENTE" ? "Pendiente" : st);

export default async function Cartera({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const f = leerFiltros(await searchParams);

  const [pf, lista] = await Promise.all([
    apiPortfolio(10, 6),
    apiEmpresas({
      state: f.estado || undefined,
      search: f.q || undefined,
      order_by: f.orden,
      order_dir: f.dir,
      limit: POR_PAGINA,
      offset: (f.pagina - 1) * POR_PAGINA,
    }),
  ]);

  // Aquí no hay modo demo: una cartera de 1.286 empresas no se finge.
  if (!pf) {
    return (
      <>
        <Cabecera titulo="Cartera Embat" sub="Salud financiera de todos los clientes" />
        <Vacio
          titulo="El motor no responde"
          texto="Arranca el backend (uvicorn backend.main:app) para ver la cartera. Esta vista lee directamente de xray.duckdb."
        />
      </>
    );
  }

  const mes = (pf.calendar?.last_closed_month ?? LAST_CLOSED_MONTH).slice(0, 7);
  const trayectoria = pf.trajectory.map((t) => ({ mes: mesDePunto(t), score: t.average_score, nivel: t.median_score }));
  const pctRiesgo = pf.total_companies ? (pf.risk_companies_count / pf.total_companies) * 100 : 0;
  const totalLista = lista?.total ?? 0;
  const paginas = Math.max(1, Math.ceil(totalLista / POR_PAGINA));

  return (
    <>
      <Cabecera
        titulo="Cartera Embat"
        sub={
          <>
            {num(pf.total_companies, 0)} clientes · {num(pf.eligible_companies, 0)} con score · {mesCorto(mes)} · corte 1-sep
          </>
        }
      />

      {/* ── Los cuatro números ─────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KPI etiqueta="Score medio de la cartera" valor={num(pf.average_score)} nota={`mediana ${num(pf.median_score)} · solo con historia suficiente`} />
        <KPI etiqueta="Clientes en mejora" valor={num(pf.improving_companies_count, 0)} nota="mejorando o en recuperación" />
        <KPI etiqueta="Clientes en riesgo" valor={num(pf.risk_companies_count, 0)} nota={`${num(pctRiesgo)} % · bache, torciéndose o deterioro`} />
        <KPI etiqueta="Alertas este mes" valor={num(pf.alerts_last_month, 0)} nota={`emitidas en el corte del 1-sep (mes de ${mesCorto(mes)})`} />
      </div>

      {/* ── Cómo está y hacia dónde va ─────────────────────────────── */}
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card className="px-6 py-5">
          <h2 className="text-[15px] font-semibold tracking-tight">Cómo se reparte la cartera</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            {num(pf.eligible_companies, 0)} clientes con score, por tramos de diez puntos
          </p>
          <div className="mt-4"><Histograma datos={pf.histogram} /></div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {Object.entries(pf.distribution_by_state).map(([st, n]) => (
              <Link key={st} href={urlCon(f, { estado: st, pagina: 1 })} className="flex items-center gap-1.5 rounded-md bg-[rgba(255,255,255,.05)] px-2 py-1 hover:bg-[rgba(255,255,255,.1)]">
                <EstadoChip estado={st} /><span className="tnum text-[11.5px] text-[var(--color-ink-3)]">{num(n, 0)}</span>
              </Link>
            ))}
          </div>
        </Card>

        <Card className="px-6 py-5">
          <h2 className="text-[15px] font-semibold tracking-tight">Trayectoria media de la cartera</h2>
          <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
            Score medio mes a mes, 24 meses. Los primeros meses son de arranque del motor.
          </p>
          <div className="mt-4"><Trayectoria datos={trayectoria} altura={220} /></div>
        </Card>
      </div>

      {/* ── Qué hacer: tres segmentos ──────────────────────────────── */}
      <div className="mt-8 mb-3">
        <h2 className="text-[17px] font-semibold tracking-tight">Dónde actuar</h2>
        <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">
          Una regla sobre score, estado y variación a tres meses. Quien crece y usa Embat, interesa que siga creciendo.
        </p>
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        {pf.segments.map((s) => {
          const seg = SEGMENTOS[s.key];
          return (
            <Card key={s.key} className="flex flex-col px-5 py-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="rounded-md px-2 py-0.5 text-[12px] font-semibold" style={{ background: seg.bg, color: seg.color }}>{seg.label}</span>
                  <p className="mt-2 text-[12px] leading-relaxed text-[var(--color-ink-2)]">{s.action}</p>
                </div>
                <span className="tnum text-[28px] font-medium leading-none" style={{ color: seg.color }}>{num(s.count, 0)}</span>
              </div>
              <div className="mt-4 flex flex-col gap-1.5">
                {s.items.map((c) => <FilaEmpresa key={c.company_id} c={c} />)}
              </div>
            </Card>
          );
        })}
      </div>

      {/* ── Rankings ───────────────────────────────────────────────── */}
      <div className="mt-8 grid gap-5 xl:grid-cols-3">
        <Ranking titulo="Mejor score" sub="Los diez clientes más sólidos hoy" items={pf.top_score} />
        <Ranking titulo="Más crecen" sub="Mayor subida del score en tres meses" items={pf.top_growth} />
        <Ranking titulo="Más caen" sub="Mayor caída del score en tres meses" items={pf.top_decline} />
      </div>

      {/* ── Toda la cartera ────────────────────────────────────────── */}
      <Card className="mt-8 px-6 py-5" >
        <div id="cartera" className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-[15px] font-semibold tracking-tight">Todos los clientes</h2>
            <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
              {num(totalLista, 0)} resultados · página {f.pagina} de {paginas}
            </p>
          </div>
          <form method="get" action="/#cartera" className="flex flex-wrap items-center gap-2">
            <input type="hidden" name="orden" value={f.orden} />
            <input type="hidden" name="dir" value={f.dir} />
            <input name="q" defaultValue={f.q} placeholder="Buscar COMP_ o GROUP_" maxLength={20}
              className="h-9 w-full min-w-0 rounded-full border border-[rgba(255,255,255,.1)] bg-[rgba(255,255,255,.06)] px-3.5 text-[12.5px] outline-none placeholder:text-[var(--color-ink-4)] focus:border-[var(--color-purple)] sm:w-48" />
            <select name="estado" defaultValue={f.estado}
              className="h-9 rounded-full border border-[rgba(255,255,255,.1)] bg-[rgba(255,255,255,.06)] px-3 text-[12.5px] outline-none">
              <option value="">Todos los estados</option>
              {ESTADOS_FILTRO.map((st) => <option key={st} value={st}>{etiquetaEstado(st)}</option>)}
            </select>
            <button type="submit" className="pildora h-9">Filtrar</button>
            {(f.q || f.estado) && <Link href={urlCon(f, { q: "", estado: "", pagina: 1 })} className="text-[12px] text-[var(--color-ink-3)] hover:underline">Quitar filtros</Link>}
          </form>
        </div>

        <div className="mt-4 hidden grid-cols-[2fr_1fr_.6fr_.7fr_.7fr_.9fr_.9fr] gap-4 px-4 text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)] lg:grid">
          <Orden f={f} campo="company_id">Cliente</Orden>
          <Orden f={f} campo="group_id">Grupo</Orden>
          <Orden f={f} campo="score" derecha>Score</Orden>
          <Orden f={f} campo="delta_3m" derecha>Δ 3 m</Orden>
          <Orden f={f} campo="momentum" derecha>Momentum</Orden>
          <span>Estado</span>
          <span>Acción</span>
        </div>

        <div className="mt-2 flex flex-col gap-1.5">
          {(lista?.items ?? []).slice(0, VISTA_PREVIA).map((c, i) => {
            const segmento = segmentoDe({ score: c.score, estado: c.state, delta3m: c.delta_3m, elegible: c.state_eligible });
            return (
              <Link key={c.company_id} href={`/embat/${c.company_id}`}
                aria-hidden={i === VISTA_PREVIA - 1 || undefined}
                tabIndex={i === VISTA_PREVIA - 1 ? -1 : undefined}
                className={`fila grid grid-cols-2 items-center gap-3 px-4 py-3 lg:grid-cols-[2fr_1fr_.6fr_.7fr_.7fr_.9fr_.9fr] lg:gap-4 ${
                  i === VISTA_PREVIA - 1 ? "difuminada" : ""}`}>
                <div className="min-w-0">
                  <p className="truncate text-[13.5px] font-medium">{nombreDe(c.company_id)}</p>
                  <p className="truncate text-[11px] text-[var(--color-ink-4)]">{c.company_id}{c.erp ? ` · ERP ${c.erp}` : ""}</p>
                </div>
                <p className="truncate text-right text-[12px] text-[var(--color-ink-3)] lg:text-left">{c.group_id.replace("GROUP_", "Grupo ")}</p>
                <div className="text-right">
                  {c.state_eligible ? <ScoreBadge score={c.score} size="sm" /> : <span className="tnum text-[13px] text-[var(--color-ink-4)]">{num(c.score, 0)}</span>}
                </div>
                <div className="text-right"><Delta v={c.delta_3m} /></div>
                <div className="hidden text-right lg:block"><Delta v={c.momentum} /></div>
                <div className="hidden lg:block"><EstadoChip estado={c.state} /></div>
                <div className="hidden lg:block"><SegmentoChip s={segmento} /></div>
              </Link>
            );
          })}
          {lista && lista.items.length === 0 && (
            <p className="py-8 text-center text-[12.5px] text-[var(--color-ink-4)]">Ningún cliente cumple el filtro.</p>
          )}
        </div>

        <GaleriaEmpresas etiqueta={`Ver los ${num(totalLista, 0)} clientes`} total={totalLista} />

      </Card>
    </>
  );
}

function Orden({ f, campo, derecha, children }: { f: Filtros; campo: string; derecha?: boolean; children: React.ReactNode }) {
  const activo = f.orden === campo;
  const dir = activo && f.dir === "desc" ? "asc" : "desc";
  return (
    <Link href={urlCon(f, { orden: campo, dir, pagina: 1 })}
      className={`${derecha ? "text-right" : ""} hover:text-[var(--color-ink-2)] ${activo ? "text-[var(--color-ink-2)]" : ""}`}>
      {children}{activo ? (f.dir === "desc" ? " ↓" : " ↑") : ""}
    </Link>
  );
}

function SegmentoChip({ s }: { s: Segmento | null }) {
  if (!s) return <span className="text-[11px] text-[var(--color-ink-4)]">—</span>;
  const seg = SEGMENTOS[s];
  return <span className="rounded-md px-2 py-0.5 text-[11px] font-medium" style={{ background: seg.bg, color: seg.color }}>{seg.label}</span>;
}

function FilaEmpresa({ c, puesto }: { c: ApiPortfolioItem; puesto?: number }) {
  return (
    <Link href={`/embat/${c.company_id}`} className="fila grid grid-cols-[auto_1fr_auto_auto] items-center gap-3 px-3 py-2">
      {puesto !== undefined ? <span className="tnum w-5 text-[11px] text-[var(--color-ink-4)]">{puesto}</span> : <span className="w-0" />}
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium">{nombreDe(c.company_id)}</p>
        <p className="truncate text-[10.5px] text-[var(--color-ink-4)]">{etiquetaEstado(c.state)} · {c.group_id.replace("GROUP_", "Grupo ")}</p>
      </div>
      <Delta v={c.delta_3m} />
      <ScoreBadge score={c.score} size="sm" />
    </Link>
  );
}

function Ranking({ titulo, sub, items }: { titulo: string; sub: string; items: ApiPortfolioItem[] }) {
  return (
    <Card className="px-5 py-5">
      <h2 className="text-[15px] font-semibold tracking-tight">{titulo}</h2>
      <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">{sub}</p>
      <div className="mt-3 flex flex-col gap-1">
        {items.map((c, i) => <FilaEmpresa key={c.company_id} c={c} puesto={i + 1} />)}
      </div>
    </Card>
  );
}
