import Link from "next/link";
import { notFound } from "next/navigation";
import { empresa } from "@/lib/data";
import { cargarEmpresa } from "@/lib/motor";
import { num } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Anillo as AnilloDrivers } from "@/components/cascada";
import { Card, Boton } from "@/components/ui";

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
      <div className="flex flex-col gap-4">
        <Card className="px-6 py-6">
          <div className="mb-1 flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="text-[16px] font-semibold tracking-tight">De qué se compone el score</h2>
            <span className="text-[11.5px] text-[var(--color-ink-4)]">
              Pulsa un arco o un factor para ver su diagnóstico
            </span>
          </div>
          <AnilloDrivers drivers={e.drivers} score={Math.round(total * 10) / 10} />
        </Card>

        <Card className="px-6 py-5">
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
