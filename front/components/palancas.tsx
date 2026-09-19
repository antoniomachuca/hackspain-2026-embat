"use client";
import { useState } from "react";
import type { Empresa } from "@/lib/data";
import type { ApiPalanca, ApiSugerencia, ApiWhatIfResponse, Familia } from "@/lib/api";
import { eur, num } from "@/lib/format";
import { DialogoSimulador } from "@/components/dialogo-simulador";

type Fila = {
  id: string; familia: Familia; nombre: string; detalle: string;
  deltaScore: number; caja: number | null; eurAnio: number | null;
  avisos: string[];
};

/**
 * Las acciones, separadas por familia.
 *
 * No es una etiqueta decorativa: salud cambia el negocio y circulante mueve
 * caja de sitio. Enseñarlas mezcladas diría que ampliar el plazo de pago y
 * cobrar antes son la misma clase de decisión, y no lo son.
 */
const MOTIVOS: Record<string, string> = {
  sin_linea: "no tiene línea de crédito",
  sin_factoring: "no usa factoring",
  sin_leasing: "no tiene leasing",
  sin_inversion: "no tiene inversiones que liquidar",
  sin_confirming: "no usa confirming",
  sin_interes: "no paga intereses observables",
  sin_debt_service: "no tiene servicio de deuda",
  sin_refunds: "no tiene devoluciones",
  sin_hhi_usable: "sus facturas no permiten medir concentración",
  sin_opex: "no tiene opex clasificable",
};

export function Palancas({ empresa, sugerencias, palancas, whatif, recomendado }:
  {
    empresa: Empresa; sugerencias?: ApiSugerencia[]; palancas?: ApiPalanca[];
    whatif?: ApiWhatIfResponse | null; recomendado?: ApiSugerencia | null;
  }) {
  const [verDescartadas, setVerDescartadas] = useState(false);
  const descartadas = (palancas ?? []).filter((p) => !p.es_aplicable);
  const aplicablesIds = (palancas ?? []).filter((p) => p.es_aplicable).map((p) => p.id);

  const detalle = (s: ApiSugerencia) => {
    const base = s.agreement_type
      ? `Acuerdo: ${s.agreement_type.replace(/_/g, " ")}`
      : s.days != null ? `${s.days} días de ajuste`
      : s.pct != null ? `${Math.round(s.pct * 100)} % de optimización`
      : "Palanca estructural de balance";
    return s.haircut != null ? `${base} · dto ${Math.round(s.haircut * 1000) / 10} %` : base;
  };

  // La recomendada del motor va primera; el resto, en su orden.
  const ordenadas = sugerencias?.length
    ? [
        ...(recomendado ? [recomendado] : []),
        ...sugerencias.filter((s) => !recomendado || s.id !== recomendado.id),
      ]
    : [];

  const filas: Fila[] = ordenadas.map((s) => ({
    id: s.id, familia: (s.familia as Familia), nombre: s.label.replace(/\s*\(.*\)$/, ""),
    detalle: detalle(s),
    deltaScore: s.delta_score, caja: s.caja_liberada_eur, eurAnio: s.eur_año,
    avisos: s.warnings ?? [],
  }));



  return (
    <>
      {/* La recomendación NO va en una caja propia: es el contenido de la
          sección. Anidar una tarjeta dentro de otra duplica bordes y hace que
          el bloque parezca un aviso pegado en vez de la respuesta. */}
      {whatif && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
            <div className="min-w-0 flex-1">
              <p className="embat-sello">Solución Embat</p>
              <p className="mt-2 text-[19px] font-semibold leading-snug tracking-tight">
                {whatif.recommended_product}
              </p>
            </div>
            <div className="text-right">
              <div className="flex items-baseline gap-2">
                <span className="tnum text-[34px] font-semibold leading-none" style={{ color: "var(--color-purple)" }}>
                  {num(whatif.projected_score)}
                </span>
                <span className="tnum text-[13px]" style={{ color: "var(--color-purple)" }}>
                  +{num(whatif.delta_score)}
                </span>
              </div>
              <p className="mt-1.5 text-[11px] text-[var(--color-ink-4)]">
                score proyectado · hoy {num(whatif.current_score)}
              </p>
            </div>
          </div>

          <p className="mt-3.5 max-w-3xl text-[12.5px] leading-relaxed text-[var(--color-ink-2)]">
            {whatif.product_rationale}
          </p>

          <div className="mt-5 flex flex-wrap gap-x-10 gap-y-3 border-t border-[var(--color-line)] pt-4">
            <Dato k="Tramo óptimo" v={eur(whatif.injection_amount)} />
            <Dato k="Estado proyectado" v={whatif.projected_state.toLowerCase()} />
            <Dato k="Ganancia de liquidez" v={`${num(whatif.liquidity_gain)} pts`} />
            <Dato k="Menos fragilidad" v={`${num(whatif.fragility_reduction)} pts`} />
          </div>
        </>
      )}

      {filas.length > 0 && (
        <DialogoSimulador
          empresa={empresa} aplicables={aplicablesIds} palancas={palancas}
          inicial={recomendado ?? sugerencias?.[0] ?? null} producto={whatif?.recommended_product ?? null}
          /* El número es el de palancas aplicables, que es lo que se va a ver
             dentro. Antes contaba las sugerencias y no cuadraba. */
          etiqueta={`Abrir el simulador · ${aplicablesIds.length || filas.length} palancas`}
        />
      )}

      {/* Por qué NO se propone el resto: REQ-B8.1 pide el motivo de rechazo,
          y enseñarlo es lo que demuestra que el catálogo se ha recorrido entero. */}
      {descartadas.length > 0 && (
        <div className="mt-5 border-t border-[var(--color-line)] pt-4">
          <button onClick={() => setVerDescartadas((v: boolean) => !v)}
            className="text-[11.5px] text-[var(--color-ink-3)] transition-colors hover:text-[var(--color-ink)]">
            {verDescartadas ? "Ocultar" : "Ver"} las {descartadas.length} palancas que no se le pueden aplicar
            <span className="ml-1.5 text-[var(--color-ink-4)]">{verDescartadas ? "▴" : "▾"}</span>
          </button>
          {verDescartadas && (
            <ul className="mt-3 flex flex-col gap-1.5">
              {descartadas.map((d) => (
                <li key={d.id} className="flex flex-wrap items-baseline gap-x-2 text-[11.5px]">
                  <span className="text-[var(--color-ink-3)]">{d.id.replace(/_/g, " ")}</span>
                  <span className="text-[var(--color-ink-4)]">
                    — {MOTIVOS[d.motivo_rechazo ?? ""] ?? d.motivo_rechazo}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

    </>
  );
}

function Dato({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
      <p className="tnum mt-1 text-[14px] font-medium">{v}</p>
    </div>
  );
}
