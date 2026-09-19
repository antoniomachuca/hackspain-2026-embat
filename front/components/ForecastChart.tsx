'use client'

import { useState } from 'react'
import { ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Forecast } from '@/lib/forecast-contract'
import { fmtMes, fmtNum } from '@/lib/format'

export function ForecastChart({ forecast }: { forecast: Forecast }) {
  const [horizon, setHorizon] = useState(6)
  const selected = forecast.points.find((p) => p.horizon_months === horizon)
  const data: { as_of: string; observed?: number; pessimistic?: number; conservative?: number; optimistic?: number }[] =
    forecast.history.map((p, i) => ({ as_of: p.as_of, observed: p.eligible ? p.score : undefined,
      ...(i === forecast.history.length - 1
        ? { pessimistic: p.score, conservative: p.score, optimistic: p.score } : {}) }))
  // Keep the monthly axis even when only 1/3/6M anchors are predicted.
  for (let h = 1; h <= horizon; h++) {
    const date = new Date(`${forecast.as_of}T12:00:00Z`)
    date.setUTCMonth(date.getUTCMonth() + h)
    const point = forecast.points.find((p) => p.horizon_months === h)
    data.push({ as_of: date.toISOString().slice(0, 10), ...(point ? {
      pessimistic: point.pessimistic, conservative: point.conservative, optimistic: point.optimistic,
    } : {}) })
  }
  return (
    <section className="rounded-2xl border border-line p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div><h2 className="text-lg font-medium">Tres escenarios para los próximos meses</h2>
          <p className="mt-1 text-sm text-ink-2">Score observado y previsión · escala 0–100</p></div>
        <div className="flex gap-2" aria-label="Horizonte de previsión">
          {[1, 3, 6].map((h) => <button key={h} onClick={() => setHorizon(h)} aria-pressed={horizon === h}
            className={`rounded-full border px-4 py-2 text-sm ${horizon === h ? 'border-agua bg-surface-2' : 'border-line'}`}>
            {h} {h === 1 ? 'mes' : 'meses'}</button>)}
        </div>
      </div>
      <div className="mb-3 flex flex-wrap gap-5 text-xs">
        <span>━━ Observado</span><span style={{ color: 'var(--color-success)' }}>┄ Optimista · P90</span>
        <span style={{ color: 'var(--color-aqua-deep)' }}>┄ Conservador / central · P50</span>
        <span style={{ color: 'var(--color-danger)' }}>┄ Pesimista · P10</span>
      </div>
      <ResponsiveContainer width="100%" height={330}>
        <ComposedChart data={data} margin={{ top: 20, right: 15, bottom: 5, left: -20 }}>
          <XAxis dataKey="as_of" tickFormatter={fmtMes} minTickGap={40} tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
          <ReferenceLine x={forecast.as_of} stroke="var(--color-ink-3)" strokeDasharray="3 3"
            label={{ value: 'Previsión →', position: 'insideTopRight', fontSize: 11 }} />
          <Tooltip labelFormatter={(label) => fmtMes(String(label))} formatter={(value) => typeof value === 'number' ? fmtNum(value) : '—'} />
          <Line type="linear" dataKey="observed" name="Observado" stroke="var(--color-ink)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line type="linear" dataKey="optimistic" name="Optimista · P90" stroke="var(--color-success)" strokeDasharray="6 4" connectNulls dot={{ r: 3 }} isAnimationActive={false} />
          <Line type="linear" dataKey="conservative" name="Conservador · P50" stroke="var(--color-aqua-deep)" strokeWidth={2.5} strokeDasharray="6 4" connectNulls dot={{ r: 3 }} isAnimationActive={false} />
          <Line type="linear" dataKey="pessimistic" name="Pesimista · P10" stroke="var(--color-danger)" strokeDasharray="6 4" connectNulls dot={{ r: 3 }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="mt-3 text-xs text-ink-2">Los puntos son previsiones a 1, 3 y 6 meses; las líneas intermedias los unen.
        P10–P90 busca cubrir el 80 % de resultados en cada horizonte. No garantiza una trayectoria completa.</p>
      {selected && <>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {[["Mejora", selected.probability_up], ["Estabilidad", selected.probability_stable], ["Deterioro", selected.probability_down]].map(([label, p]) =>
            <div key={label} className="rounded-xl bg-surface-2 p-4"><p className="text-xs text-ink-2">{label} estimada</p>
              <p className="mt-1 text-xl tabular-nums">{Math.round(Number(p) * 100)} %</p></div>)}
        </div>
        <p className="mt-2 text-xs text-ink-2">Mejora y deterioro: cambios superiores a 3 puntos respecto al score actual.</p>
        <div className="mt-7 grid gap-6 md:grid-cols-2">
          <div><h3 className="text-sm font-medium">Por qué esta previsión</h3>
            <p className="mt-2 text-sm text-ink-2">De {fmtNum(forecast.current_score)} a {fmtNum(selected.conservative)} puntos en {horizon} meses.</p>
            <ul className="mt-3 space-y-2 text-sm">{selected.explanation.contributions.map((c) =>
              <li key={c.feature} className="flex justify-between gap-3"><span>{featureLabel(c.feature)}</span><span className="tabular-nums">{c.points >= 0 ? '+' : ''}{fmtNum(c.points)}</span></li>)}
              <li className="flex justify-between"><span>Referencia, calibración y otros ajustes</span><span className="tabular-nums">{fmtNum(selected.explanation.reference_delta + selected.explanation.other_points + selected.explanation.calibration_points + selected.explanation.clipping_points)}</span></li>
            </ul><p className="mt-3 text-xs text-ink-2">Contribuciones del modelo; no demuestran causalidad.
              {selected.explanation.method === 'sequential_replacement_order_dependent' && ' El reparto depende del orden de las variables.'}</p>
          </div>
          <div><h3 className="text-sm font-medium">Qué precisión tuvo en empresas reservadas</h3>
            <p className="mt-3 text-sm text-ink-2">Error absoluto medio: {fmtNum(selected.test_mae)} puntos.</p>
            <p className="mt-2 text-sm text-ink-2">La banda cubrió el {Math.round(selected.test_interval_coverage * 100)} % de los resultados del test.</p>
            <p className="mt-2 text-xs text-ink-2">Modelo: {selected.model}. Previsión del score bancario sobre el dataset sintético del reto.</p>
          </div>
        </div>
      </>}
    </section>
  )
}

function featureLabel(feature: string) {
  const names: Record<string, string> = { score_actual: 'Score actual', score_media_3m: 'Media de 3 meses',
    score_media_6m: 'Media de 6 meses', pendiente_6m: 'Tendencia de 6 meses', volatilidad_6m: 'Variabilidad del score',
    liquidez: 'Liquidez', cobros: 'Cobros', deuda: 'Deuda', momentum: 'Tendencia reciente', crecimiento: 'Crecimiento',
    fragilidad: 'Fragilidad', margen_flujos: 'Margen de caja', margen_media_3m: 'Margen de caja a 3 meses',
    margen_media_6m: 'Margen de caja a 6 meses', calidad: 'Calidad de datos', log_cobros: 'Volumen de cobros',
    log_pagos: 'Volumen de pagos', carga_deuda: 'Carga de deuda', concentracion: 'Concentración de clientes',
    persistence: 'Continuidad del score', trailing_mean: 'Media reciente', damped_trend: 'Tendencia amortiguada', seasonal: 'Patrón anual' }
  return names[feature] ?? feature.replaceAll('_', ' ')
}
