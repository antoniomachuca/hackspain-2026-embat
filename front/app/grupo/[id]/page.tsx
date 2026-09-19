import Link from "next/link";
import { notFound } from "next/navigation";
import { cargarGrupoDetalle } from "@/lib/motor";
import { num } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Trayectoria, Sparkline } from "@/components/charts";
import { Card, CardHead, KPI, ScoreBadge, EstadoChip, Delta } from "@/components/ui";

export default async function Grupo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const g = await cargarGrupoDetalle(id);
  if (!g || !g.miembros.length) notFound();
  const peor = g.peor;

  return (
    <>
      <Cabecera
        titulo={g.nombre}
        sub={<>{g.miembros.length} filiales · cobertura de datos {g.cobertura}% · {g.id}</>}
      />
      <div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KPI etiqueta="Consolidado del grupo" valor={num(g.consolidado)} nota="65% media + 35% peor filial material" />
          <KPI etiqueta="Media simple" valor={num(g.media)} nota="sin ponderar" />
          <KPI etiqueta="Peor filial" valor={peor ? num(peor.score) : "—"} nota={peor ? `${peor.nombre} (${peor.id})` : "—"} />
          <KPI etiqueta="Filiales con score" valor={`${g.miembros.filter(m => m.mesesHistoria >= 12).length} de ${g.miembros.length}`} nota="el resto, sin historia suficiente" />
        </div>

        {peor && g.consolidado < g.media - 1 && (
          <Card className="mt-5 px-5 py-4">
            <p className="text-[13px] leading-relaxed">
              El grupo saca <strong className="tnum font-medium">{num(g.consolidado)}</strong>, pero{" "}
              <Link href={`/${peor.id}`} className="font-medium underline decoration-[var(--color-line-2)] underline-offset-2 hover:text-[var(--color-aqua)]">{peor.nombre}</Link>{" "}
              saca <strong className="tnum font-medium">{num(peor.score)}</strong> y arrastra al consolidado.
            </p>
            <p className="mt-1.5 text-[11px] text-[var(--color-ink-4)]">
              Penalización por contagio activa según el modelo de grupo de X-Ray ({num(g.penalizacion)} pts).
            </p>
          </Card>
        )}

        <Card className="mt-5">
          <CardHead titulo="Filial más débil" sub={peor ? `${peor.nombre} (${peor.id}) · Score: ${num(peor.score)}` : "Sin datos"} />
          <div className="px-3 py-4">{peor && <Trayectoria datos={peor.trayectoria} alerta={peor.alerta?.mesDeteccion} altura={190} />}</div>
        </Card>

        <Card className="mt-5 px-6 py-5">
          <h2 className="mb-4 text-[16px] font-semibold tracking-tight">Filiales</h2>
          <div className="flex flex-col gap-2">
            {g.miembros.map((m) => (
              <Link key={m.id} href={`/${m.id}`}
                className="fila grid grid-cols-2 items-center gap-4 px-4 py-3 lg:grid-cols-[1.9fr_.7fr_.6fr_.8fr_.9fr]">
                <div className="col-span-2 min-w-0 lg:col-span-1">
                  <p className="truncate text-[13.5px] font-medium">{m.nombre} <span className="text-[11px] text-[var(--color-ink-4)]">({m.id})</span></p>
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
      </div>
    </>
  );
}
