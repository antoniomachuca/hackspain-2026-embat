import Link from "next/link";
import { cargarGrupos } from "@/lib/motor";
import { Cabecera } from "@/components/shell";
import { Card, ScoreBadge, BandaChip } from "@/components/ui";

export default async function Grupos() {
  const grupos = await cargarGrupos();

  return (
    <>
      <Cabecera
        titulo="Grupos Corporativos"
        sub={`${grupos.length} grupos empresariales consolidados · motor DuckDB`}
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {grupos.map((g) => (
          <Link key={g.id} href={`/grupo/${g.id}`}>
            <Card className="px-5 py-4 transition-colors hover:bg-[var(--color-surface-2)]">
              <div className="flex min-w-0 items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-medium" title={g.nombre}>{g.nombre}</p>
                  <p className="mt-0.5 truncate text-[12px] text-[var(--color-ink-3)]" title={`${g.company_count} filiales · ${g.id}${g.erp ? ` · ERP ${g.erp}` : ""}`}>
                    {g.company_count} filiales · {g.id}
                    {g.erp ? ` · ERP ${g.erp}` : ""}
                  </p>
                </div>
                <ScoreBadge score={g.average_score} />
              </div>
              <div className="mt-3 flex items-center justify-between">
                <BandaChip score={g.average_score} />
                <span className="tnum text-[11px] text-[var(--color-ink-4)]">
                  {g.risk_companies_count > 0 ? (
                    <span className="font-medium text-[var(--color-risk-3)]">
                      {g.risk_companies_count} en riesgo
                    </span>
                  ) : (
                    "0 en riesgo"
                  )}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </>
  );
}
