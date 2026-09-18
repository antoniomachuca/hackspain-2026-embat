/**
 * Explicabilidad en pantalla (B4).
 *
 * "El 71 % de los responsables financieros rechazaría una IA que no se explica, por
 * precisa que sea" (research §2). La explicabilidad no es un requisito del reto: es la
 * razón de compra.
 *
 * Forma: lista de 3-5 factores con signo y barra de peso, más los códigos de razón.
 * NUNCA un beeswarm de SHAP delante del jurado (PRODUCTO.md §7).
 */

import type { CodigoRazon, Driver } from '@/lib/contract'
import { BLOQUE_TEXTO, CODIGO_TEXTO, featureTexto, fmtNum, fmtPuntos } from '@/lib/format'

export function Drivers({ drivers }: { drivers: Driver[] }) {
  if (!drivers.length) {
    return <p className="text-sm text-ink-2">Sin drivers destacados este mes: ningún factor se movió lo suficiente.</p>
  }
  const max = Math.max(...drivers.map((d) => Math.abs(d.contribucion)))

  return (
    <ul className="space-y-4">
      {drivers.map((d) => {
        const positivo = d.contribucion >= 0
        const color = positivo ? 'var(--positivo)' : 'var(--negativo)'
        return (
          <li key={d.feature}>
            <div className="mb-1.5 flex items-baseline justify-between gap-4">
              <span className="text-sm">
                {featureTexto(d.feature)}
                <span className="ml-2 text-xs text-ink-2">{BLOQUE_TEXTO[d.bloque]}</span>
              </span>
              <span className="tabular text-sm peso-medio whitespace-nowrap" style={{ color }}>
                {fmtPuntos(d.contribucion)} pts
              </span>
            </div>
            {/* Barra bidireccional desde el centro: el signo se ve sin leer el número */}
            <div className="relative h-1.5 w-full rounded-full bg-surface-2">
              <div
                className="absolute top-0 h-1.5 rounded-full"
                style={{
                  width: `${(Math.abs(d.contribucion) / max) * 50}%`,
                  left: positivo ? '50%' : undefined,
                  right: positivo ? undefined : '50%',
                  background: color,
                }}
              />
              <div className="absolute left-1/2 top-[-2px] h-2.5 w-px bg-line-2" />
            </div>
            <p className="tabular mt-1.5 text-xs text-ink-2">
              {fmtNum(d.valor)} {d.unidad} · percentil {Math.round(d.p_peer)} de su peer group
            </p>
          </li>
        )
      })}
    </ul>
  )
}

export function CodigosRazon({ codigos }: { codigos: CodigoRazon[] }) {
  if (!codigos.length) return null
  return (
    <ul className="space-y-2">
      {codigos.map((c) => (
        <li key={c} className="flex gap-2.5 text-sm text-ink-3">
          <span className="tabular mt-0.5 shrink-0 rounded border border-line px-1.5 text-[10px] text-ink-2">
            {c.slice(0, 5)}
          </span>
          {CODIGO_TEXTO[c]}
        </li>
      ))}
    </ul>
  )
}
