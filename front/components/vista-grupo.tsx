import Link from "next/link";
import { cargarTrayectoriasFiliales, type GrupoDetalle } from "@/lib/motor";
import { apiGrafo } from "@/lib/api";
import { Grafo } from "@/components/grafo";
import { num, eur } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Trayectoria } from "@/components/charts";
import { Card, CardHead, KPI } from "@/components/ui";
import { ListaGrupo } from "@/components/grupo";

/**
 * Detalle de un grupo corporativo. Lo usan dos rutas: /grupo/[id] (Embat mirando la
 * cartera) y /[company_id]/grupo (una empresa mirando su propio grupo). `base` es el
 * prefijo de los enlaces a las filiales: "/embat" en la primera, "" en la segunda.
 */
export async function VistaGrupo({ g, base }: { g: GrupoDetalle; base: "" | "/embat" }) {
  const peor = g.peor;
  const [grafo, trayectorias] = await Promise.all([
    apiGrafo(g.id),
    cargarTrayectoriasFiliales(g.miembros.map((m) => m.id), 12),
  ]);

  // El listado del grupo solo trae un punto por filial; la historia real la
  // pide cada una por su lado, si no el minigráfico sería decorativo.
  const filiales = g.miembros.map((m) => ({
    id: m.id, nombre: m.nombre, score: m.score, momentum: m.momentum,
    evaluable: m.mesesHistoria >= 12,
    trayectoria: trayectorias[m.id]?.length ? trayectorias[m.id] : m.trayectoria,
  }));
  const volumenInterno = grafo?.edges.reduce((s, e) => s + e.eur, 0) ?? 0;

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

        {/* El contagio y la peor filial en una columna estrecha, y a su lado el
            mapa de flujos, que es lo que pide sitio de verdad. */}
        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,392px)_1fr]">
          <div className="flex flex-col gap-5">
            {peor && g.consolidado < g.media - 1 && (
              <Card className="px-5 py-4">
                <p className="text-[13px] leading-relaxed">
                  El grupo saca <strong className="tnum font-medium">{num(g.consolidado)}</strong>, pero{" "}
                  <Link href={`${base}/${peor.id}`} className="font-medium underline decoration-[var(--color-line-2)] underline-offset-2 hover:text-[var(--color-aqua)]">{peor.nombre}</Link>{" "}
                  saca <strong className="tnum font-medium">{num(peor.score)}</strong> y arrastra al consolidado.
                </p>
                <p className="mt-1.5 text-[11px] text-[var(--color-ink-4)]">
                  Penalización por contagio activa según el modelo de grupo de X-Ray ({num(g.penalizacion)} pts).
                </p>
              </Card>
            )}

            <Card className="flex flex-1 flex-col px-6 py-5">
              <div>
                <h2 className="text-[15px] font-semibold tracking-tight">Filiales</h2>
                <p className="tnum mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
                  {g.miembros.length} sociedades · {filiales.filter((f) => f.evaluable).length} con score
                </p>
              </div>
              <div className="mt-3 border-t border-[var(--color-line)] pt-2">
                <ListaGrupo filiales={filiales} base={base} visibles={6} />
              </div>
            </Card>
          </div>

          {grafo && grafo.edges.length > 0 ? (
            <Card className="flex flex-col px-6 py-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-[16px] font-semibold tracking-tight">Flujos entre sociedades</h2>
                  <p className="mt-0.5 text-[11.5px] text-[var(--color-ink-4)]">
                    {grafo.edges.length} flujos inferidos · {eur(volumenInterno, true)} · zoom, arrastre y clic en una sociedad
                  </p>
                </div>
                <Link href={`/grafo?grupo=${g.id}`} className="pildora">Ver en el mapa</Link>
              </div>
              <div className="mt-3 flex-1">
                <Grafo nodos={grafo.nodes} aristas={grafo.edges} destacar={peor?.id} alto={396} />
              </div>
            </Card>
          ) : (
            <Card className="flex items-center justify-center px-6 py-5">
              <p className="text-[12px] text-[var(--color-ink-4)]">
                Sin flujos detectados entre sus sociedades
              </p>
            </Card>
          )}
        </div>

        <Card className="mt-5">
          <CardHead titulo="Filial más débil" sub={peor ? `${peor.nombre} (${peor.id}) · Score: ${num(peor.score)}` : "Sin datos"} />
          <div className="px-3 py-4">
            {peor && <Trayectoria datos={peor.trayectoria} deteccion={peor.deteccion} camino={peor.camino} altura={230} />}
          </div>
        </Card>

      </div>
    </>
  );
}
