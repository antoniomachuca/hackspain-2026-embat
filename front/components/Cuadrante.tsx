'use client'

/**
 * Cuadrante nivel × tendencia · toda la cartera de un vistazo.
 *
 * Patrón de Moody's EDF-X (research §4): una vista de dos ejes para situar la cartera
 * entera y ver cómo cada empresa se mueve entre cubos de alerta.
 *
 * Aquí es, además, donde la paradoja del enunciado se ve sola: Northbrook y Velasco caen
 * casi pegadas en el eje X (el nivel de hoy) y en extremos opuestos del eje Y (hacia
 * dónde van). Es el argumento del reto convertido en una sola imagen.
 */

import { useRouter } from 'next/navigation'
import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import type { RespuestaScore } from '@/lib/contract'
import { ESTADO_TEXTO, colorScore, fmtNum, fmtPuntos } from '@/lib/format'
import { nombre } from '@/lib/identity'

export function Cuadrante({ cartera }: { cartera: RespuestaScore[] }) {
  const router = useRouter()
  const datos = cartera
    .filter((s) => !s.scoring_pendiente)
    .map((s) => ({
      id: s.entity_id,
      nombre: nombre(s.entity_id),
      x: s.score,
      y: s.tendencia,
      estado: s.estado,
      color: colorScore(s.score),
    }))

  return (
    <div className="rounded-2xl border border-line p-6">
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <h2 className="peso-medio text-sm">Dónde está y hacia dónde va</h2>
        <p className="text-xs text-ink-2">Cada punto es una empresa · clic para abrir</p>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 24, left: 0 }}>
          <CartesianGrid stroke="var(--border-primary)" strokeDasharray="2 4" />
          <XAxis
            type="number"
            dataKey="x"
            name="Score"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tick={{ fontSize: 11, fill: 'var(--content-secondary)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--border-primary)' }}
            label={{ value: 'Score hoy  →', position: 'insideBottomRight', offset: -14, fontSize: 11, fill: 'var(--content-secondary)' }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Tendencia"
            domain={[-3, 3]}
            tick={{ fontSize: 11, fill: 'var(--content-secondary)' }}
            tickLine={false}
            axisLine={false}
            width={48}
            label={{ value: 'Tendencia ↑', angle: -90, position: 'insideLeft', fontSize: 11, fill: 'var(--content-secondary)' }}
          />
          <ZAxis range={[160, 160]} />
          <ReferenceLine y={0} stroke="var(--border-secondary)" />
          <ReferenceLine x={55} stroke="var(--border-secondary)" strokeDasharray="4 4" />
          <Tooltip content={<Caja />} cursor={{ strokeDasharray: '3 3' }} />
          <Scatter
            data={datos}
            isAnimationActive={false}
            onClick={(punto) => {
              const id = (punto as unknown as { payload?: { id?: string } }).payload?.id
              if (id) router.push(`/empresa/${id}`)
            }}
            className="cursor-pointer"
          >
            {datos.map((d) => (
              <Cell key={d.id} fill={d.color} fillOpacity={0.85} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-ink-2">
        <p>↖ Floja pero levantando — la apuesta del año que viene</p>
        <p>↗ Sólida y subiendo — ampliar límite</p>
        <p>↙ Floja y cayendo — actuar ya</p>
        <p>↘ Sólida pero torciéndose — el caso que nadie ve</p>
      </div>
    </div>
  )
}

function Caja({ active, payload }: { active?: boolean; payload?: { payload: { nombre: string; x: number; y: number; estado: keyof typeof ESTADO_TEXTO } }[] }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="peso-medio mb-1">{p.nombre}</p>
      <p className="tabular text-ink-2">
        Score {fmtNum(p.x)} · {fmtPuntos(p.y)}/mes
      </p>
      <p className="mt-1 text-ink-3">{ESTADO_TEXTO[p.estado]}</p>
    </div>
  )
}
