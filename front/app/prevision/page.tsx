import { ForecastChart } from '@/components/ForecastChart'
import { getForecastPage } from '@/lib/forecast-api'
import { fmtNum } from '@/lib/format'

export default async function Prevision({ searchParams }: { searchParams: Promise<{ company?: string }> }) {
  const { company } = await searchParams
  let result
  try { result = await getForecastPage(company) } catch {
    return <div><h1 className="text-3xl peso-medio">Previsión de salud financiera</h1>
      <p className="mt-5 text-ink-2">Las previsiones no están disponibles en este momento. Vuelve a intentarlo cuando estén preparados los resultados.</p></div>
  }
  const { companies, forecast, benchmark } = result
  return <div>
    <h1 className="text-3xl peso-medio">Previsión de salud financiera</h1>
    <p className="mt-3 max-w-3xl text-sm text-ink-2">Explora cómo puede evolucionar la empresa y cuánto cambia la incertidumbre con el horizonte de predicción.</p>
    <form className="my-7 flex flex-wrap items-center gap-3" method="get">
      <label htmlFor="company" className="text-sm">Empresa</label>
      <select id="company" name="company" defaultValue={forecast?.company_id} className="rounded-lg border border-line bg-surface px-3 py-2 text-sm">
        {companies.map((c) => <option key={c.company_id} value={c.company_id}>{c.company_id}{c.status !== 'available' ? ' · historia insuficiente' : ''}</option>)}
      </select><button className="rounded-lg border border-line px-4 py-2 text-sm">Ver previsión</button>
    </form>
    {!forecast ? <p>Empresa no encontrada.</p> : forecast.status !== 'available' ?
      <p className="rounded-xl border border-line p-6 text-ink-2">Esta empresa necesita seis meses consecutivos de actividad con datos suficientes para generar una previsión.</p> :
      <ForecastChart key={forecast.company_id} forecast={forecast} />}
    <section className="mt-10">
      <h2 className="text-lg peso-medio">Comparación de modelos</h2>
      <p className="mt-2 text-sm text-ink-2">Modelos seleccionados con grupos de validación. Estos resultados corresponden a otros grupos, reservados para el test.</p>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm [&_td]:pr-5 [&_th]:pr-5">
        <thead><tr className="border-b border-line"><th className="py-3">Horizonte</th><th>Modelo</th><th>Error medio por grupo</th><th>Cobertura de la banda</th></tr></thead>
        <tbody>{Object.entries(benchmark.horizons).map(([h, row]) => <tr key={h} className="border-b border-line">
          <td className="py-3">{h} meses</td><td>{row.selected}</td><td>{fmtNum(row.test[row.selected].macro_group_mae)} puntos</td>
          <td>{Math.round(row.test[row.selected].interval_80_coverage * 100)} %</td></tr>)}</tbody>
      </table></div>
      <details className="mt-5 rounded-xl border border-line p-4">
        <summary className="cursor-pointer text-sm peso-medio">Ver los diez modelos en cada horizonte</summary>
        <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm [&_td]:pr-5 [&_th]:pr-5">
          <thead><tr className="border-b border-line"><th className="py-2">Meses</th><th>Modelo</th><th>Error por grupo</th><th>Acierto equilibrado de dirección</th><th>Cobertura</th></tr></thead>
          <tbody>{Object.entries(benchmark.horizons).flatMap(([h, row]) => Object.entries(row.test).map(([model, m]) =>
            <tr key={`${h}-${model}`} className="border-b border-line"><td className="py-2">{h}</td><td>{model}{model === row.selected ? ' · seleccionado' : ''}</td>
              <td>{fmtNum(m.macro_group_mae)}</td><td>{Math.round(m.balanced_direction_accuracy * 100)} %</td><td>{Math.round(m.interval_80_coverage * 100)} %</td></tr>))}</tbody>
        </table></div>
      </details>
      <p className="mt-5 text-xs text-ink-2">{benchmark.context.historical_value_coverage > 0 ?
        'Se compararon modelos con y sin contexto externo disponible a fecha de corte; el modelo seleccionado puede prescindir de él.' :
        'Sin contexto externo histórico verificable para esta evaluación. No se han supuesto sectores ni países ausentes.'}
        {' '}El escenario conservador representa la mediana, no una garantía ni una previsión de impago.</p>
    </section>
  </div>
}
