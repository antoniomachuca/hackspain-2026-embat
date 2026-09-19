"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Empresa } from "@/lib/data";
import type { OpcionComparar } from "@/lib/motor";
import { num, mesCorto, banda } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Trayectoria } from "@/components/charts";
import { Card, ScoreBadge, BandaChip, EstadoChip, Delta } from "@/components/ui";

export default function SplitScreen({
  sube,
  baja,
  opcionesSube = [],
  opcionesBaja = [],
}: {
  sube: Empresa;
  baja: Empresa;
  opcionesSube?: OpcionComparar[];
  opcionesBaja?: OpcionComparar[];
}) {
  const router = useRouter();
  const [xray, setXray] = useState(false);
  const dif = Math.abs(sube.score - baja.score);

  function cambiarSube(id: string) {
    router.push(`/comparar?sube=${id}&baja=${baja.id}`);
  }

  function cambiarBaja(id: string) {
    router.push(`/comparar?sube=${sube.id}&baja=${id}`);
  }

  const mesDetectBaja =
    baja.alerta?.mesDeteccion ??
    baja.trayectoria[Math.max(0, baja.trayectoria.length - 5)]?.mes ??
    "2026-05";

  return (
    <>
      <Cabecera
        titulo="Dos empresas, pocos puntos de diferencia"
        sub="La misma foto de hoy, dos historias opuestas"
        extra={
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-line-2)] p-1">
            <button
              onClick={() => setXray(false)}
              className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors ${
                !xray
                  ? "bg-[var(--color-deep)] text-white"
                  : "text-[var(--color-ink-3)] hover:bg-[var(--color-surface-3)]"
              }`}
            >
              Bureau tradicional
            </button>
            <button
              onClick={() => setXray(true)}
              className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors ${
                xray
                  ? "bg-[var(--color-deep)] text-white"
                  : "text-[var(--color-ink-3)] hover:bg-[var(--color-surface-3)]"
              }`}
            >
              X Ray
            </button>
          </div>
        }
      />

      <div>
        <Card className="mb-5 px-5 py-4">
          <p className="text-[13px] leading-relaxed">
            {xray ? (
              <>
                <strong className="font-medium">{sube.nombre}</strong> ({sube.id}) viene subiendo desde el mes 1.{" "}
                <strong className="font-medium">{baja.nombre}</strong> ({baja.id}) lleva {baja.alerta?.mesesAnticipacion ?? 4} meses
                torciéndose y lo vimos en {mesCorto(mesDetectBaja)}.
                Una es mucho mejor riesgo que la otra, y ahora se distingue cuál.
              </>
            ) : (
              <>
                En el mes 24 estas dos empresas sacan <strong className="tnum font-medium">{num(dif)} puntos</strong> de
                diferencia. Una es mucho mejor riesgo que la otra, y en la foto de hoy no se distingue cuál.
              </>
            )}
          </p>
        </Card>

        <div className="grid gap-5 lg:grid-cols-2">
          {[
            { emp: sube, rol: "sube" as const, opts: opcionesSube, onSelect: cambiarSube, label: "Trayectoria de mejora / recuperación" },
            { emp: baja, rol: "baja" as const, opts: opcionesBaja, onSelect: cambiarBaja, label: "Trayectoria de deterioro / tensión" },
          ].map(({ emp: e, rol, opts, onSelect, label }) => {
            const primerScore = e.trayectoria[0]?.score ?? 50;
            const ultimoMes = e.trayectoria[e.trayectoria.length - 1]?.mes ?? "2026-09";
            return (
              <Card key={e.id} className="overflow-hidden">
                <div className="flex items-start justify-between gap-4 border-b border-[var(--color-line)] px-5 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/${e.id}`}
                        className="truncate text-[14px] font-medium hover:text-[var(--color-aqua)]"
                      >
                        {e.nombre} <span className="text-[11px] text-[var(--color-ink-4)] font-normal">({e.id})</span>
                      </Link>
                    </div>
                    <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">{e.sector}</p>

                    {opts.length > 1 && (
                      <div className="mt-2 flex items-center gap-2">
                        <label className="text-[11px] text-[var(--color-ink-4)] shrink-0">Cambiar:</label>
                        <select
                          value={e.id}
                          onChange={(ev) => onSelect(ev.target.value)}
                          className="w-full max-w-[240px] truncate rounded border border-[var(--color-line-2)] bg-[var(--color-surface-2)] px-2 py-0.5 text-[11px] text-[var(--color-ink-2)]"
                        >
                          {opts.map((opt) => (
                            <option key={opt.id} value={opt.id}>
                              {opt.id} · {opt.estado} ({num(opt.score)} pts)
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <ScoreBadge score={e.score} size="lg" />
                    {xray && (
                      <div className="mt-1 flex justify-end">
                        <EstadoChip estado={e.estado} />
                      </div>
                    )}
                  </div>
                </div>

                {xray ? (
                  <div className="px-3 py-4">
                    <Trayectoria datos={e.trayectoria} alerta={e.alerta?.mesDeteccion} altura={200} />
                    <div className="flex items-center justify-between px-3 pt-2 text-[12px]">
                      <span className="tnum text-[var(--color-ink-3)]">
                        mes 1: {num(primerScore)} → mes 24: {num(e.score)}
                      </span>
                      <Delta v={e.score - primerScore} sufijo=" pts en 24 meses" />
                    </div>
                  </div>
                ) : (
                  <div className="flex h-[248px] flex-col items-center justify-center gap-2">
                    <p className="text-[12px] text-[var(--color-ink-4)]">Único dato disponible</p>
                    <p className="tnum text-[13px] text-[var(--color-ink-3)]">
                      Score a {mesCorto(ultimoMes)}
                    </p>
                    <BandaChip score={e.score} />
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        {xray && (
          <p className="mt-5 text-[11px] text-[var(--color-ink-4)]">
            Empresas reales extraídas de DuckDB ({sube.id} en {sube.estado} vs {baja.id} en {baja.estado}). En la foto estática la diferencia es de apenas {num(dif)} puntos, pero la serie temporal revela historias de solvencia opuestas.
          </p>
        )}
      </div>
    </>
  );
}
