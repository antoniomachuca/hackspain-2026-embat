import Link from "next/link";
import { notFound } from "next/navigation";
import { empresa } from "@/lib/data";
import { cargarEmpresa } from "@/lib/motor";
import { num, mesCorto } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Waterfall } from "@/components/charts";
import { Card, CardHead, ScoreBadge, Delta, Boton } from "@/components/ui";

export default async function Drivers({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const e = (await cargarEmpresa(id)) ?? empresa(id);
  if (!e) notFound();
  const total = e.drivers.reduce((a, d) => a + d.contribucion, 0);

  return (
    <>
      <Cabecera
        titulo="Detalle de drivers"
        sub={<><Link href={`/${e.id}`} className="underline decoration-[var(--color-line-2)] underline-offset-2 hover:text-[var(--color-aqua)]">{e.nombre}</Link> · descomposición aditiva exacta</>}
        extra={<Boton tono="plano" href={`/${e.id}`}>Volver a la ficha</Boton>}
      />
      <div>
        <Card>
          <CardHead titulo="De dónde sale el score" sub="Cada barra es la contribución del factor en puntos" />
          <div className="px-3 py-5"><Waterfall drivers={e.drivers} altura={260} /></div>
        </Card>

        <Card className="mt-5 px-6 py-5">
          <h2 className="mb-4 text-[16px] font-semibold tracking-tight">Factores</h2>
          <div className="grid grid-cols-[1.5fr_1fr_1fr_.7fr] gap-4 px-4 pb-2 text-[10.5px] font-medium uppercase tracking-wider text-[var(--color-ink-4)]">
            <span>Factor</span><span>Valor</span><span className="text-right">Percentil</span><span className="text-right">Contribución</span>
          </div>
          <div className="flex flex-col gap-2">
            {e.drivers.map((d) => (
              <div key={d.feature} className="fila px-4 py-3">
                <div className="grid grid-cols-[1.5fr_1fr_1fr_.7fr] items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-[13.5px] font-medium">{d.etiqueta}</span>
                    {d.codigo && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[rgba(255,255,255,.08)] text-[var(--color-ink-3)]">
                        {d.codigo}
                      </span>
                    )}
                  </div>
                  <span className="tnum text-[12.5px] text-[var(--color-ink-2)]">{d.valor}</span>
                  <span className="tnum flex items-center justify-end gap-2 text-[12.5px]">
                    <span className="h-1 w-16 overflow-hidden rounded-full bg-[rgba(255,255,255,.10)]">
                      <span className="block h-full rounded-full" style={{ width: `${d.p_peer}%`, background: d.p_peer >= 50 ? "var(--color-purple)" : "var(--color-risk-2)" }} />
                    </span>
                    P{d.p_peer}
                  </span>
                  <span className="tnum text-right text-[13.5px] font-semibold">{num(d.contribucion, 2)}</span>
                </div>
                {d.descripcion && (
                  <p className="mt-1.5 text-[11px] text-[var(--color-ink-3)] leading-relaxed">
                    {d.descripcion} {d.diagnostico ? <span className="text-white/80 font-medium">· {d.diagnostico}</span> : null}
                  </p>
                )}
              </div>
            ))}
            <div className="panel-2 grid grid-cols-[1.5fr_1fr_1fr_.7fr] items-center gap-4 px-4 py-3">
              <span className="text-[13.5px] font-semibold">Score</span><span /><span />
              <span className="text-right"><ScoreBadge score={Math.round(total * 10) / 10} size="sm" /></span>
            </div>
          </div>
        </Card>

        <Card className="mt-5 px-6 py-5">
          <p className="text-[13px] font-medium">Qué se movió desde el mes pasado</p>
          <p className="mt-1.5 text-[12px] leading-relaxed text-[var(--color-ink-2)]">
            El score {e.score >= e.scorePrev ? "sube" : "baja"} {num(Math.abs(e.score - e.scorePrev))} puntos.
            El factor que más pesa es <strong className="font-medium">{e.drivers[0].etiqueta.toLowerCase()}</strong> ({e.drivers[0].valor},
            percentil {e.drivers[0].p_peer} de su grupo de pares), y el más débil es{" "}
            <strong className="font-medium">{e.drivers[e.drivers.length - 1].etiqueta.toLowerCase()}</strong>.
          </p>
          <p className="mt-2 text-[11px] text-[var(--color-ink-4)]">
            Toda cifra conserva unidad, divisa, fecha y procedencia. Ninguna sale de un modelo de lenguaje.
          </p>
        </Card>
      </div>
    </>
  );
}
