"use client";
import type { Empresa } from "@/lib/data";
import type { ApiPalanca, ApiSugerencia, ApiWhatIfResponse } from "@/lib/api";
import { eur, num } from "@/lib/format";
import { DialogoSimulador } from "@/components/dialogo-simulador";

function nombreDe(s: ApiSugerencia) {
  return s.label.replace(/\s*\(.*\)$/, "");
}

function detalleDe(s: ApiSugerencia) {
  const base = s.agreement_type
    ? `Acuerdo: ${s.agreement_type.replace(/_/g, " ")}`
    : s.days != null ? `${s.days} días`
    : s.pct != null ? `${Math.round(s.pct * 100)} %`
    : "Corte actual";
  return s.haircut != null ? `${base} · dto ${Math.round(s.haircut * 1000) / 10} %` : base;
}

/**
 * Acciones del motor: euros de /simulate, ΔS solo si el motor lo autoriza.
 * Confirming y el resto de circulante no inventan puntos.
 */
export function Palancas({ empresa, sugerencias, circulante, palancas, recomendado }:
  {
    empresa: Empresa;
    sugerencias?: ApiSugerencia[];
    circulante?: ApiSugerencia[];
    palancas?: ApiPalanca[];
    whatif?: ApiWhatIfResponse | null;
    recomendado?: ApiSugerencia | null;
  }) {
  const aplicablesIds = (palancas ?? []).filter((p) => p.es_aplicable).map((p) => p.id);
  const destacada = recomendado ?? sugerencias?.[0] ?? circulante?.[0] ?? null;
  return (
    <>
      {destacada && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
            <div className="min-w-0 flex-1">
              <p className="embat-sello">Simulación del motor</p>
              <p className="mt-2 text-[19px] font-semibold leading-snug tracking-tight">
                {nombreDe(destacada)}
              </p>
              <p className="mt-1 text-[12px] text-[var(--color-ink-3)]">{detalleDe(destacada)}</p>
            </div>
            <div className="text-right">
              {destacada.caja_liberada_eur != null && destacada.caja_liberada_eur > 0 ? (
                <>
                  <p className="tnum text-[34px] font-semibold leading-none" style={{ color: "var(--color-purple)" }}>
                    {eur(destacada.caja_liberada_eur, true)}
                  </p>
                  <p className="mt-1.5 text-[11px] text-[var(--color-ink-4)]">caja neta liberada · corte actual</p>
                </>
              ) : destacada.delta_score != null ? (
                <>
                  <p className="tnum text-[34px] font-semibold leading-none" style={{ color: "var(--color-purple)" }}>
                    {num(empresa.score + destacada.delta_score)}
                  </p>
                  <p className="mt-1.5 text-[11px] text-[var(--color-ink-4)]">
                    score proyectado · hoy {num(empresa.score)}
                  </p>
                </>
              ) : (
                <p className="text-[12px] text-[var(--color-ink-3)]">Sin euros ni ΔS en esta palanca</p>
              )}
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-x-10 gap-y-3 border-t border-[var(--color-line)] pt-4">
            {destacada.delta_score != null ? (
              <Dato k="Score" v={`${num(empresa.score)} → ${num(empresa.score + destacada.delta_score)}`} />
            ) : (
              <Dato k="Score" v="No se mueve" nota="circulante: mueve caja, no la nota" />
            )}
            {destacada.caja_liberada_eur != null && destacada.caja_liberada_eur > 0 && (
              <Dato k="Caja neta" v={eur(destacada.caja_liberada_eur)} nota="inmediatos en el corte" />
            )}
            {destacada.eur_año != null && destacada.eur_año > 0 && (
              <Dato k="Ahorro anual" v={eur(destacada.eur_año)} nota="del motor, no de una curva de tipos" />
            )}
          </div>
        </>
      )}

      {(aplicablesIds.length > 0 || destacada) && (
        <DialogoSimulador
          empresa={empresa} aplicables={aplicablesIds} palancas={palancas}
          inicial={recomendado ?? sugerencias?.[0] ?? circulante?.[0] ?? null}
          producto={destacada ? nombreDe(destacada) : null}
          etiqueta={`Abrir el simulador · ${aplicablesIds.length || (destacada ? 1 : 0)} palancas`}
        />
      )}
    </>
  );
}

function Dato({ k, v, nota }: { k: string; v: string; nota?: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-[var(--color-ink-4)]">{k}</p>
      <p className="tnum mt-1 text-[14px] font-medium">{v}</p>
      {nota && <p className="mt-0.5 text-[10.5px] text-[var(--color-ink-4)]">{nota}</p>}
    </div>
  );
}
