import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILLARS = ('L', 'C', 'D', 'fragility')


def number(value, digits=3):
    return 'n/d' if value is None else f'{value:.{digits}f}'.replace('.', ',')


def percent(value):
    return number(100 * value, 2) + r'\%'


def table(headers, records, alignment=None):
    alignment = alignment or 'l' + 'r' * (len(headers) - 1)
    lines = [r'\begin{center}', r'\small', r'\begin{tabular}{' + alignment + '}', r'\hline', ' & '.join(headers) + r' \\', r'\hline']
    lines.extend(' & '.join(map(str, record)) + r' \\' for record in records)
    return '\n'.join(lines + [r'\hline', r'\end{tabular}', r'\end{center}'])


def render(core, enriched, manifest, erp_manifest):
    coverage = core['coverage']
    parts = [r'''\section*{11. Resultados reproducibles del motor}
Se ejecutaron dos modos con idéntica configuración: banco por defecto y banco con snapshot ERP bajo hipótesis explícita de signo. La segunda ejecución no convierte esa hipótesis en verificada. Se procesaron los CSV completos; el manifiesto conserva sus huellas y las del código. Las tablas se generan automáticamente desde los JSON de validación, sin copiar resultados a mano.

\subsection*{11.1. Cobertura, priors y disponibilidad}''']
    parts.append(table(['Medida al último corte', 'Banco', 'ERP experimental'], [
        ['Sociedades con salida', coverage['companies'], enriched['coverage']['companies']],
        ['Meses por sociedad', coverage['months'], enriched['coverage']['months']],
        ['Sociedades con evidencia utilizable', coverage['endpoint_observed'], enriched['coverage']['endpoint_observed']],
        ['Priors neutrales marcados', coverage['endpoint_prior'], enriched['coverage']['endpoint_prior']],
        ['Calidad bancaria al menos 0,8', coverage['high_quality'], enriched['coverage']['high_quality']],
        ['Observaciones reales de caja', coverage['cash_known'], enriched['coverage']['cash_known']],
        ['Enriquecimientos ERP usados', coverage['erp_used'], enriched['coverage']['erp_used']],
        ['HHI utilizable', coverage['hhi_used'], enriched['coverage']['hhi_used']],
    ], 'p{10cm}rr'))
    parts.append(f"Se entregan {coverage['companies'] * coverage['months']} filas empresa-mes en cada modo. Los priors no son diagnósticos de salud observada. No se calculó liquidez histórica real en estas ejecuciones: la caja conocida es cero observaciones, no un saldo imputado de cero. El núcleo usa cobertura de flujos. El snapshot ERP de {erp_manifest['audit']['erp']['snapshot_as_of']} aprovecha {erp_manifest['audit']['erp']['companies_with_usable_snapshot']} sociedades; no se retropropaga a los meses anteriores.")
    parts.append(r'''\subsection*{11.2. Gates ejecutados}
Los límites 0,65 y 2\% se fijaron antes de ejecutar estos controles. El modo estricto devuelve un código de error si falla un control; no se cambian umbrales para ocultar fallos.''')
    labels = {
        'finite_outputs': 'Salidas numéricas finitas, sin NaNs',
        'strict_range': 'Score estrictamente dentro de [0,100]',
        'factor_domains': 'Dominios de todos los factores',
        'opposite_trajectories_control': 'Control de trayectorias opuestas',
        'exact_additive_waterfall': 'Waterfall exacto, incluido clipping',
        'spearman_below_065': r'Máximo $|r_s|<0{,}65$ en el corte final',
        'endpoint_saturation_below_2pct': r'Extremos inferiores al 2\% en el corte final',
        'synthetic_monotone_and_three_month_lead': 'Control monótono con al menos tres meses de aviso',
        'mature_month_correlations_below_065': 'Correlaciones bajo umbral en todos los cortes maduros',
        'mature_month_saturation_below_2pct': 'Saturación bajo umbral en todos los cortes maduros',
    }
    parts.append(table(['Control', 'Banco', 'ERP experimental'], [
        [labels[key], 'Cumple' if passed else 'NO CUMPLE', 'Cumple' if enriched['gates'][key] else 'NO CUMPLE']
        for key, passed in core['gates'].items()
    ], 'p{10cm}rr'))
    parts.append(r'''\subsection*{11.3. Correlaciones de Spearman}
Se excluyen los priors del cálculo de correlación. Además se repite en sociedades con calidad bancaria al menos 0,8. Son correlaciones descriptivas entre sociedades: las filiales de un grupo pueden ser dependientes, por lo que no se presentan p-valores que presupongan independencia. No se ajusta una regresión de un pilar contra los demás ni se aplica blanqueo estadístico para pasar este gate.''')
    matrix = core['correlations_all_observed']['matrix']
    parts.append(table(['Banco'] + [r'$F$' if key == 'fragility' else f'${key}$' for key in PILLARS], [
        [r'$F$' if left == 'fragility' else f'${left}$'] + [number(matrix[left][right]) for right in PILLARS] for left in PILLARS
    ]))
    parts.append(table(['Máximo absoluto fuera de diagonal', 'Banco', 'ERP experimental'], [
        ['Corte final, sociedades con evidencia', number(core['correlations_all_observed']['maximum_absolute_off_diagonal']), number(enriched['correlations_all_observed']['maximum_absolute_off_diagonal'])],
        ['Corte final, calidad bancaria alta', number(core['correlations_high_quality']['maximum_absolute_off_diagonal']), number(enriched['correlations_high_quality']['maximum_absolute_off_diagonal'])],
        ['Peor corte maduro, sociedades con evidencia', number(max(row['max_correlation_observed'] for row in core['monthly_diagnostics'])), number(max(row['max_correlation_observed'] for row in enriched['monthly_diagnostics']))],
        ['Peor corte maduro, calidad bancaria alta', number(max(row['max_correlation_high_quality'] for row in core['monthly_diagnostics'])), number(max(row['max_correlation_high_quality'] for row in enriched['monthly_diagnostics']))],
    ], 'p{10cm}rr'))
    parts.append(f"La matriz bancaria final utiliza {core['correlations_all_observed']['companies']} sociedades; la subcohorte de calidad alta, {core['correlations_high_quality']['companies']}. Se comprueban {len(core['monthly_diagnostics'])} cortes tras el calentamiento. Cumplir el umbral satisface un control de no redundancia extrema en esta muestra; no demuestra señal predictiva independiente.")
    parts.append(r'''\subsection*{11.4. Distribución y saturación}
Se distingue saturación por clipping de masas explicables por disponibilidad de datos. No se fuerza la distribución a uniforme ni se transforma el score a percentiles para aparentar calibración.''')
    distribution_rows = [[label, number(core['endpoint_score'][key], 2), number(enriched['endpoint_score'][key], 2)]
                         for key, label in [('min', 'Mínimo'), ('p05', 'P5'), ('median', 'Mediana'), ('p95', 'P95'), ('max', 'Máximo')]]
    distribution_rows.extend([
        ['Fracción en 0 o 100', percent(core['endpoint_saturation_all']), percent(enriched['endpoint_saturation_all'])],
        ['Peor saturación mensual, sin priors', percent(max(row['saturation_observed'] for row in core['monthly_diagnostics'])), percent(max(row['saturation_observed'] for row in enriched['monthly_diagnostics']))],
    ])
    parts.append(table(['Estadístico de score final', 'Banco', 'ERP experimental'], distribution_rows))
    parts.append(r'''La deuda sin desembolsos observados se queda en el prior 0,5, no se convierte en salud perfecta. Ese empate no es evidencia de calibración. El gate de extremos no valida probabilidades ni una correspondencia con ratings externos.

\subsection*{11.5. Controles de trayectoria y anticipación}
Para la comparación del enunciado se imponen dos bases lineales de 24 meses: 45 a 65 y 82 a 68. Se mantiene igual el resto de ajustes y se usa confirmación normalizada $x=2B/100-1$. Es un control algebraico del momentum y su suma, no una identificación de Northbrook o Velasco en los CSV.''')
    trajectory = core['trajectory_control']
    parts.append(table(['Caso idealizado', 'Base final', 'Momentum final', 'Score ajustado'], [
        ['Recuperación', trajectory['recovery_final_base'], number(trajectory['recovery_momentum']), number(trajectory['recovery_final_score'], 2)],
        ['Deterioro', trajectory['deterioration_final_base'], number(trajectory['deterioration_momentum']), number(trajectory['deterioration_final_score'], 2)],
    ]))
    parts.append(r'''El control de tesorería fija caja inicial 300, doce meses de cobros 120, pagos operativos 100 y deuda 5. Después los cobros bajan diez unidades por mes, hasta un suelo de cinco. La caja de referencia se acumula causalmente desde la reserva inicial, sin ajustar esa reserva al resultado del detector.

La alerta se activa si el score cae al menos cinco puntos respecto a la mediana de los tres meses previos al shock y el momentum es inferior a $-0{,}1$. La caja de referencia no entra como feature en el modo de núcleo bancario; un segundo modo sí aporta cada saldo conocido y compromisos 105. La monotonicidad se comprueba desde el inicio del deterioro hasta el primer saldo no positivo.''')
    stress = core['stress_control']
    parts.append(table(['Variante del control', 'Mes alerta', 'Mes caja no positiva', 'Antelación', 'Monótono'], [
        [label, row['first_alert_month_index'] + 1 if row['first_alert_month_index'] is not None else 'Sin alerta', stress['cash_nonpositive_month_index'] + 1,
         str(row['lead_months']) + ' meses' if row['lead_months'] is not None else 'n/d', 'Sí' if row['monotone_from_shock_to_cash_loss'] else 'No']
        for label, row in [('Solo banco', stress['variants']['bank_core']), ('Con caja conocida', stress['variants']['known_cash'])]
    ], 'p{4cm}rrrr'))
    parts.append(r'''Los meses se numeran desde uno. Estos resultados demuestran respuesta al escenario fijado, no ocho meses de anticipación general en empresas reales ni una precisión determinada de predicción del colapso. El saldo inicial y la intensidad del deterioro condicionan la antelación. Las pruebas unitarias también verifican que un bache aislado no activa momentum persistente.

\subsection*{11.6. Ejecución y entregables}
Desde la raíz del repositorio, usando NumPy y SciPy ya declarados en \texttt{requirements.txt}:
\begin{verbatim}
python3 algorythm/calc_score.py
python3 algorythm/validate_score.py --strict
python3 -m algorythm.calc_score --erp-snapshot-assumed-positive \
  --output algorythm/engine_results_erp
python3 -m algorythm.validate_score \
  --results algorythm/engine_results_erp --strict
python3 -m algorythm.render_score_report
python3 -m unittest algorythm.test_score_engine \
  algorythm.test_score_data algorythm.test_score_outputs -v
\end{verbatim}
La salida estándar está en \texttt{algorythm/engine\_results/}; la experimental, en \texttt{engine\_results\_erp/}. Cada una contiene CSV empresa-mes, panel NumPy, manifiesto y validación JSON. Los valores sin redondear permiten reconstruir exactamente cada waterfall. El validador rechaza artefactos cuyo código no coincide con el manifiesto.

El motor devuelve un diccionario de arrays, sin requerir Pandas. Las columnas principales son \texttt{score}, \texttt{liquidity\_points}, \texttt{collections\_points}, \texttt{debt\_points}, \texttt{momentum\_points}, \texttt{growth\_points}, \texttt{fragility\_points} y \texttt{clipping\_points}. Las pruebas comprueban también prefijos temporales, caja no retropropagada, ERP ausente, conversión inválida, unidades monetarias y estados sin evidencia.

\textbf{Conclusión.} Se entrega un índice aditivo ejecutable y controles reproducibles. No se ha demostrado calibración crediticia, independencia de los factores, disponibilidad histórica de caja ni anticipación empírica sobre Embat. El siguiente paso para afirmar capacidad de riesgo real exige etiquetas, semántica verificada y evaluación fuera de muestra.''')
    parts.append(f"Entorno de la ejecución bancaria: Python {manifest['runtime']['python']} y NumPy {manifest['runtime']['numpy']}. Los parámetros completos y hashes se conservan en el manifiesto.")
    return '\n\n'.join(parts) + '\n'


def main():
    reports = []
    for name in ('engine_results', 'engine_results_erp'):
        folder = ROOT / 'algorythm' / name
        with (folder / 'validation.json').open(encoding='utf-8') as source:
            validation = json.load(source)
        with (folder / 'score_manifest.json').open(encoding='utf-8') as source:
            manifest = json.load(source)
        reports.append((validation, manifest))
    text = render(reports[0][0], reports[1][0], reports[0][1], reports[1][1])
    path = ROOT / 'algorythm' / 'formula' / 'engine_benchmark_results.tex'
    path.write_text(text, encoding='utf-8')
    print(f'Rendered {path}')


if __name__ == '__main__':
    main()
