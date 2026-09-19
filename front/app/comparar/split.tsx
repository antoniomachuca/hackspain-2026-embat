"use client";
import { useState } from "react";
import Link from "next/link";
import type { Empresa } from "@/lib/data";
import { num, mesCorto, banda } from "@/lib/format";
import { Cabecera } from "@/components/shell";
import { Trayectoria } from "@/components/charts";
import { Card, ScoreBadge, BandaChip, EstadoChip, Delta } from "@/components/ui";

export default function SplitScreen({ sube, baja }: { sube: Empresa; baja: Empresa }) {
  const [xray, setXray] = useState(false);
  const dif = Math.abs(sube.score - baja.score);

  return (
    <>
      <Cabecera
        titulo="Dos empresas, pocos puntos de diferencia"
        sub="La misma foto de hoy, dos historias opuestas"
        extra={
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-line-2)] p-1">
            <button onClick={() => setXray(false)}
              className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors ${!xray ? "bg-[var(--color-deep)] text-white" : "text-[var(--color-ink-3)] hover:bg-[var(--color-surface-3)]"}`}>
              Bureau tradicional
            </button>
            <button onClick={() => setXray(true)}
              className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors ${xray ? "bg-[var(--color-deep)] text-white" : "text-[var(--color-ink-3)] hover:bg-[var(--color-surface-3)]"}`}>
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
                <strong className="font-medium">{sube.nombre}</strong> viene subiendo desde el mes 1.{" "}
                <strong className="font-medium">{baja.nombre}</strong> lleva {baja.alerta?.mesesAnticipacion ?? 4} meses
                torciéndose y lo vimos en {mesCorto(baja.alerta?.mesDeteccion ?? baja.trayectoria[19].mes)}.
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
          {[sube, baja].map((e) => (
            <Card key={e.id} className="overflow-hidden">
              <div className="flex items-start justify-between gap-4 border-b border-[var(--color-line)] px-5 py-4">
                <div>
                  <Link href={`/empresa/${e.id}`} className="text-[14px] font-medium hover:text-[var(--color-aqua)]">{e.nombre}</Link>
                  <p className="mt-0.5 text-[12px] text-[var(--color-ink-3)]">{e.sector}</p>
                </div>
                <div className="text-right">
                  <ScoreBadge score={e.score} size="lg" />
                  {xray && <div className="mt-1 flex justify-end"><EstadoChip estado={e.estado} /></div>}
                </div>
              </div>

              {xray ? (
                <div className="px-3 py-4">
                  <Trayectoria datos={e.trayectoria} alerta={e.alerta?.mesDeteccion} altura={200} />
                  <div className="flex items-center justify-between px-3 pt-2 text-[12px]">
                    <span className="tnum text-[var(--color-ink-3)]">
                      mes 1: {num(e.trayectoria[0].score)} → mes 24: {num(e.score)}
                    </span>
                    <Delta v={e.score - e.trayectoria[0].score} sufijo=" pts en 24 meses" />
                  </div>
                </div>
              ) : (
                <div className="flex h-[248px] flex-col items-center justify-center gap-2">
                  <p className="text-[12px] text-[var(--color-ink-4)]">Único dato disponible</p>
                  <p className="tnum text-[13px] text-[var(--color-ink-3)]">Score a {mesCorto(e.trayectoria[23].mes)}</p>
                  <BandaChip score={e.score} />
                </div>
              )}
            </Card>
          ))}
        </div>

        {xray && (
          <p className="mt-5 text-[11px] text-[var(--color-ink-4)]">
            Empresas elegidas por su trayectoria. Northbrook Foods y Velasco Industrial son los ejemplos del
            enunciado y no existen como tales en el dataset.
          </p>
        )}
      </div>
    </>
  );
}
