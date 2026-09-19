/** Server-only data access: API when configured, otherwise actual local benchmark artifacts. */
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import type { Forecast, ForecastBenchmark } from './forecast-contract'

const base = process.env.FORECAST_API_URL
const directory = process.env.XRAY_FORECAST_DIR ?? path.resolve(process.cwd(), '../algorythm/forecast_results')

async function request<T>(route: string): Promise<T> {
  const response = await fetch(`${base}${route}`, { cache: 'no-store', signal: AbortSignal.timeout(5000) })
  if (!response.ok) throw new Error(`Forecast HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export async function getForecastPage(id?: string) {
  if (base) {
    const [catalog, benchmark] = await Promise.all([
      request<{ companies: Pick<Forecast, 'company_id' | 'status'>[] }>('/api/forecasts'),
      request<ForecastBenchmark>('/api/benchmarks/forecasts'),
    ])
    const selected = id ?? catalog.companies.find((c) => c.status === 'available')?.company_id
    const forecast = selected ? await request<Forecast>(`/api/companies/${encodeURIComponent(selected)}/forecast`) : null
    if (forecast && forecast.run_id !== benchmark.run_id) throw new Error('Forecast artifacts from different runs')
    return { companies: catalog.companies, forecast, benchmark }
  }
  const [rawForecasts, rawBenchmark] = await Promise.all([
    readFile(path.join(directory, 'forecasts.json'), 'utf8'),
    readFile(path.join(directory, 'benchmark.json'), 'utf8'),
  ])
  const forecasts = JSON.parse(rawForecasts) as { run_id: string; companies: Record<string, Forecast> }
  const benchmark = JSON.parse(rawBenchmark) as ForecastBenchmark
  if (forecasts.run_id !== benchmark.run_id) throw new Error('Forecast artifacts from different runs')
  const companies = Object.values(forecasts.companies).map(({ company_id, status }) => ({ company_id, status }))
  const selected = id ?? companies.find((c) => c.status === 'available')?.company_id
  return { companies, forecast: selected ? forecasts.companies[selected] ?? null : null, benchmark }
}
