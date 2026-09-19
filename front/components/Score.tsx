/**
 * El score en pantalla: número grande + banda + estado en texto.
 * Nunca un gauge solo, nunca el color como único código (research §4 y §5).
 */

import type { Estado, Semaforo } from '@/lib/contract'
import { ESTADO_SIGNO, ESTADO_TEXTO, SEMAFORO_TEXTO, banda, colorScore, fmtNum, fmtPuntos } from '@/lib/format'

export function ScoreNumero({ score, tamano = 'grande' }: { score: number; tamano?: 'grande' | 'medio' }) {
  const b = banda(score)
  const color = colorScore(score)
  return (
    <div className="flex items-baseline gap-3">
      <span
        className={`tabular peso-medio leading-none ${tamano === 'grande' ? 'text-7xl' : 'text-4xl'}`}
        style={{ color }}
      >
        {fmtNum(score)}
      </span>
      <div className="flex flex-col">
        <span className="text-xs text-ink-2">/ 100</span>
        <span className="text-sm peso-medio" style={{ color }}>
          {b.etiqueta}
        </span>
      </div>
    </div>
  )
}

/** La banda continua ámbar → aguamarina, con la posición marcada. */
export function BandaScore({ score }: { score: number }) {
  return (
    <div className="w-full">
      <div className="relative h-1.5 w-full rounded-full bg-[linear-gradient(90deg,var(--score-critico),var(--score-bajo),var(--score-medio),var(--score-alto))]">
        <div
          className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow"
          style={{ left: `${score}%`, background: colorScore(score) }}
        />
      </div>
      <div className="tabular mt-1 flex justify-between text-[10px] text-ink-2">
        <span>0 · Riesgo</span>
        <span>35</span>
        <span>55</span>
        <span>75</span>
        <span>100 · Sólida</span>
      </div>
    </div>
  )
}

export function EstadoEtiqueta({ estado, tendencia }: { estado: Estado; tendencia?: number }) {
  const signo = ESTADO_SIGNO[estado]
  const color =
    signo === 'positivo' ? 'var(--positivo)' : signo === 'negativo' ? 'var(--negativo)' : 'var(--neutro)'
  const flecha = signo === 'positivo' ? '▲' : signo === 'negativo' ? '▼' : '▬'
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs peso-medio"
      style={{ color, borderColor: color, background: `color-mix(in srgb, ${color} 8%, transparent)` }}
    >
      <span aria-hidden className="text-[9px]">
        {flecha}
      </span>
      {ESTADO_TEXTO[estado]}
      {tendencia !== undefined && <span className="tabular opacity-70">{fmtPuntos(tendencia)}/mes</span>}
    </span>
  )
}

export function ConfianzaEtiqueta({ semaforo, valor }: { semaforo: Semaforo; valor: number }) {
  return (
    <span className="tabular text-xs text-ink-2">
      {SEMAFORO_TEXTO[semaforo]} · {Math.round(valor * 100)} %
    </span>
  )
}
