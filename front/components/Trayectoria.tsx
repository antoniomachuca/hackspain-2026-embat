'use client'

/**
 * El gráfico del reto (RF-B11.4).
 *
 * "Trayectoria, no foto" es la tesis del enunciado, así que el gráfico tiene que
 * DISTINGUIR VISUALMENTE nivel y tendencia. Por eso son dos paneles apilados que
 * comparten el eje de meses:
 *
 *   Arriba  · el score (línea) sobre el nivel (área tenue). Dónde está.
 *   Abajo   · la tendencia (barras con signo). Hacia dónde va.
 *
 * Nunca un gauge solo: el patrón de Moody's, D&B y Creditsafe es número grande +
 * banda + línea temporal (research §4).
 */

import {
  Area,
  Bar,
  BarChart,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { PuntoTrayectoria } from '@/lib/contract'
import { ESTADO_TEXTO, fmtMes, fmtNum, fmtPuntos } from '@/lib/format'

interface Props {
  puntos: PuntoTrayectoria[]
  color?: string
  /** Mes a marcar con una línea vertical: cuándo lo vio el monitor (B5). */
  mesDeteccion?: string
  alto?: number
  compacto?: boolean
}

export function Trayectoria({ puntos, color = 'var(--agua-oscuro)', mesDeteccion, alto = 200, compacto = false }: Props) {
  const ejeX = (
    <XAxis
      dataKey="mes"
      tickFormatter={fmtMes}
      tick={{ fontSize: 11, fill: 'var(--content-secondary)' }}
      tickLine={false}
      axisLine={{ stroke: 'var(--border-primary)' }}
      interval={Math.max(0, Math.floor(puntos.length / 6) - 1)}
      minTickGap={8}
    />
  )

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={alto}>
        <ComposedChart data={puntos} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`nivel-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.18} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <YAxis
            domain={[0, 100]}
            ticks={[0, 35, 55, 75, 100]}
            tick={{ fontSize: 11, fill: 'var(--content-secondary)' }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          {/* Las bandas del score, tenues: dan escala sin gritar */}
          <ReferenceLine y={75} stroke="var(--border-primary)" strokeDasharray="2 4" />
          <ReferenceLine y={55} stroke="var(--border-primary)" strokeDasharray="2 4" />
          <ReferenceLine y={35} stroke="var(--border-primary)" strokeDasharray="2 4" />
          {mesDeteccion && (
            <ReferenceLine
              x={mesDeteccion}
              stroke="var(--rosa)"
              strokeWidth={1.5}
              label={{ value: 'lo vimos aquí', position: 'insideTopRight', fontSize: 11, fill: 'var(--rosa)' }}
            />
          )}
          <Area type="monotone" dataKey="nivel" stroke="none" fill={`url(#nivel-${color})`} isAnimationActive={false} />
          <Line
            type="monotone"
            dataKey="score"
            stroke={color}
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />
          {ejeX}
          <Tooltip content={<Caja />} cursor={{ stroke: 'var(--border-secondary)' }} />
        </ComposedChart>
      </ResponsiveContainer>

      {!compacto && (
        <>
          <p className="mt-3 mb-1 text-[11px] uppercase tracking-wide text-ink-2">
            Tendencia · puntos de score por mes
          </p>
          <ResponsiveContainer width="100%" height={64}>
            <BarChart data={puntos} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
              <YAxis domain={[-3, 3]} hide />
              <ReferenceLine y={0} stroke="var(--border-secondary)" />
              <Bar dataKey="tendencia" isAnimationActive={false} radius={[1, 1, 1, 1]}>
                {puntos.map((p) => (
                  <Cell key={p.mes} fill={p.tendencia >= 0 ? 'var(--positivo)' : 'var(--negativo)'} />
                ))}
              </Bar>
              {ejeX}
              <Tooltip content={<Caja />} cursor={false} />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}

function Caja({ active, payload }: { active?: boolean; payload?: { payload: PuntoTrayectoria }[] }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="peso-medio mb-1">{fmtMes(p.mes)}</p>
      <p className="tabular text-ink-2">
        Score <span className="peso-medio text-ink">{fmtNum(p.score)}</span>
      </p>
      <p className="tabular text-ink-2">
        Nivel {fmtNum(p.nivel)} · Tendencia {fmtPuntos(p.tendencia)}/mes
      </p>
      <p className="mt-1 text-ink-3">{ESTADO_TEXTO[p.estado]}</p>
    </div>
  )
}
