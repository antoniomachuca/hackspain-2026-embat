/**
 * Flujos intragrupo: quién mueve dinero a quién dentro de cada grupo de la cartera.
 * Los flujos no vienen en el dataset; se infieren emparejando salidas y entradas
 * del mismo día y mismo importe entre sociedades del mismo grupo.
 */
import Link from "next/link";
import { apiGrafo, apiGrafoResumen } from "@/lib/api";
import { eur, num, mesCorto } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Grafo } from "@/components/grafo";
import { Card, KPI, ScoreBadge, Vacio } from "@/components/ui";

const nombreGrupo = (g: string) => g.replace("GROUP_", "Grupo ");
const corto = (id: string) => id.replace("COMP_", "");

export default async function Flujos({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const uno = (k: string) => (Array.isArray(sp[k]) ? sp[k]![0] : sp[k]) ?? "";
  const minimo = uno("min") === "3" ? 3 : 2;

  const resumen = await apiGrafoResumen(40, minimo);
  if (!resumen) {
    return (
      <>
        <Cabecera titulo="Flujos intragrupo" />
        <Vacio titulo="El motor no responde" texto="Arranca el backend para calcular los flujos sobre xray.duckdb." />
      </>
    );
  }

  const pedido = uno("grupo").trim().toUpperCase();
  const gid = pedido ? (pedido.startsWith("GROUP_") ? pedido : `GROUP_${pedido.padStart(4, "0")}`) : resumen.groups[0]?.group_id;
  const grafo = gid ? await apiGrafo(gid, minimo) : null;
  const enLista = resumen.groups.find((g) => g.group_id === gid);
  const url = (cambios: { grupo?: string; min?: number }) => {
    const p = new URLSearchParams();
    const g = cambios.grupo ?? gid; const m = cambios.min ?? minimo;
    if (g) p.set("grupo", g); if (m !== 2) p.set("min", String(m));
    return `/grafo?${p.toString()}`;
  };

  return (
    <>
      <Cabecera
        titulo="Flujos intragrupo"
        sub={<>{num(resumen.groups_with_flows, 0)} grupos con flujos detectados · {num(resumen.total_edges, 0)} flujos · {eur(resumen.total_eur, true)} emparejados</>}
        extra={
          <div className="flex items-center gap-1 rounded-full bg-[rgba(255,255,255,.06)] p-1 text-[12px]">
            {[2, 3].map((m) => (
              <Link key={m} href={url({ min: m })}
                className={`rounded-full px-3 py-1.5 ${minimo === m ? "bg-[rgba(255,255,255,.14)] text-[var(--color-ink)]" : "text-[var(--color-ink-3)] hover:text-[var(--color-ink)]"}`}>
                ≥ {m} coincidencias
              </Link>
            ))}
          </div>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[320px_1fr]">
        {/* ── Grupos con más movimiento interno ─────────────────────── */}
        <Card className="px-4 py-4 xl:max-h-[calc(100vh-140px)] xl:overflow-y-auto">
          <p className="px-2 text-[10.5px] uppercase tracking-wider text-[var(--color-ink-4)]">Grupos por volumen interno</p>
          <div className="mt-2 flex flex-col gap-1">
            {resumen.groups.map((g) => (
              <Link key={g.group_id} href={url({ grupo: g.group_id })}
                className={`fila grid grid-cols-[1fr_auto] items-center gap-3 px-3 py-2.5 ${g.group_id === gid ? "border-l-2 border-l-[var(--color-purple)] bg-[rgba(176,131,232,.06)]" : ""}`}>
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium">{nombreGrupo(g.group_id)}</p>
                  <p className="tnum truncate text-[11px] text-[var(--color-ink-4)]">{g.companies} sociedades · {g.edges} flujos · {eur(g.eur, true)}</p>
                </div>
                <ScoreBadge score={g.average_score} size="sm" />
              </Link>
            ))}
          </div>
        </Card>

        {/* ── El mapa ───────────────────────────────────────────────── */}
        <div className="min-w-0">
          {grafo ? (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <KPI etiqueta="Sociedades" valor={num(grafo.nodes.length, 0)} nota={`${grafo.nodes.filter((n) => n.eur_in + n.eur_out > 0).length} con flujos internos`} />
                <KPI etiqueta="Flujos detectados" valor={num(grafo.edges.length, 0)} nota={`${num(grafo.edges.reduce((s, e) => s + e.matches, 0), 0)} movimientos emparejados`} />
                <KPI etiqueta="Volumen interno" valor={eur(grafo.edges.reduce((s, e) => s + e.eur, 0), true)} nota={enLista ? `score medio ${num(enLista.average_score)} · peor ${num(enLista.worst_score)}` : "—"} />
              </div>

              <Card className="mt-3 px-6 py-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-[16px] font-semibold tracking-tight">{nombreGrupo(grafo.group_id)}</h2>
                    <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">Pulsa una sociedad para abrir su ficha. Las flechas van del que paga al que cobra.</p>
                  </div>
                  <Link href={`/grupo/${grafo.group_id}`} className="pildora">Ver el grupo</Link>
                </div>
                <div className="mt-3">
                  {grafo.edges.length > 0
                    ? <Grafo nodos={grafo.nodes} aristas={grafo.edges} vista="embat" />
                    : <Vacio titulo="Sin flujos internos con este umbral" texto="Baja a ≥ 2 coincidencias o elige otro grupo." />}
                </div>
              </Card>

              {grafo.edges.length > 0 && (
                <Card className="mt-5 px-6 py-5">
                  <h2 className="text-[15px] font-semibold tracking-tight">Flujos por volumen</h2>
                  <div className="mt-3 flex flex-col gap-1.5">
                    {grafo.edges.slice(0, 12).map((a) => {
                      const o = grafo.nodes.find((n) => n.company_id === a.source);
                      const d = grafo.nodes.find((n) => n.company_id === a.target);
                      return (
                        <div key={`${a.source}-${a.target}`} className="fila grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-2.5 lg:grid-cols-[1.4fr_.5fr_.7fr_.6fr]">
                          <p className="text-[13px]">
                            <Link href={`/embat/${a.source}`} className="font-medium hover:underline">Sociedad {corto(a.source)}</Link>
                            {o && <span className="tnum text-[11px] text-[var(--color-ink-4)]"> {num(o.score, 0)}</span>}
                            <span className="mx-2 text-[var(--color-purple)]">→</span>
                            <Link href={`/embat/${a.target}`} className="font-medium hover:underline">Sociedad {corto(a.target)}</Link>
                            {d && <span className="tnum text-[11px] text-[var(--color-ink-4)]"> {num(d.score, 0)}</span>}
                          </p>
                          <p className="tnum hidden text-right text-[12px] text-[var(--color-ink-3)] lg:block">{a.matches} coinc.</p>
                          <p className="tnum text-right text-[13px] font-medium">{eur(a.eur)}</p>
                          <p className="tnum hidden text-right text-[11.5px] text-[var(--color-ink-4)] lg:block">último {mesCorto(a.last_date.slice(0, 7))}</p>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}
            </>
          ) : (
            <Vacio titulo="Grupo no encontrado" texto={`No hay sociedades registradas para ${gid ?? "ese grupo"}.`} />
          )}

          <Card className="mt-5 px-6 py-4">
            <p className="text-[12px] leading-relaxed text-[var(--color-ink-3)]">
              <strong className="font-medium text-[var(--color-ink-2)]">Cómo se infiere.</strong> El dataset no dice quién paga a quién: las contrapartes están anonimizadas por sociedad.
              Un flujo A → B es una salida de A y una entrada de B, del mismo grupo, el mismo día y por el mismo importe (≥ 500 €).
              Dentro de un grupo esto ocurre 24 veces más que entre grupos distintos (4,5 frente a 0,19 coincidencias por par), así que es señal.
              Un par con ≥ 2 coincidencias tiene un 1,6 % de probabilidad de ser casualidad; con ≥ 3, un 0,1 %.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
