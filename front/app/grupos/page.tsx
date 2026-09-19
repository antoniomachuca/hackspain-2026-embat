import Link from "next/link";
import { GRUPOS_LISTA } from "@/lib/data";
import { num } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Card, ScoreBadge, BandaChip } from "@/components/ui";

export default function Grupos() {
  return (
    <>
      <Cabecera titulo="Grupos" sub={`${GRUPOS_LISTA.length} grupos empresariales`} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {GRUPOS_LISTA.map((g) => (
          <Link key={g.id} href={`/grupo/${g.id}`}>
            <Card className="px-5 py-4 transition-colors hover:bg-[var(--color-surface-2)]">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[14px] font-medium">{g.nombre}</p>
                  <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">{g.miembros.length} filiales · {g.id}</p>
                </div>
                <ScoreBadge score={g.consolidado} />
              </div>
              <div className="mt-3 flex items-center justify-between">
                <BandaChip score={g.consolidado} />
                <span className="tnum text-[11px] text-[var(--color-ink-4)]">cobertura {g.cobertura}%</span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </>
  );
}
