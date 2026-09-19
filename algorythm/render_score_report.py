import json
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorythm.score_data import sha256


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
    for report, source in ((core, manifest), (enriched, erp_manifest)):
        if report.get('model_version') != source.get('model_version') or report.get('panels_sha256') != source.get('panels_sha256'):
            raise ValueError('Validation and scoring manifest differ; regenerate validation before rendering.')
    coverage = core['coverage']
    parts = [r'''\section*{8. Resultados reproducibles del motor}
Se ejecutaron dos modos con idéntica configuración: banco por defecto y banco con snapshot ERP bajo hipótesis explícita de signo. La segunda ejecución no convierte esa hipótesis en verificada. Se procesaron los CSV completos; el manifiesto conserva sus huellas y las del código. Las tablas se generan automáticamente desde los JSON de validación, sin copiar resultados a mano.

\subsection*{8.1. Cobertura, priors y disponibilidad}''']
    parts.append(table(['Medida al último corte', 'Banco', 'ERP experimental'], [
        ['Sociedades con salida', coverage['companies'], enriched['coverage']['companies']],
        ['Meses por sociedad', coverage['months'], enriched['coverage']['months']],
        ['Sociedades con evidencia utilizable', coverage['endpoint_observed'], enriched['coverage']['endpoint_observed']],
        ['Priors neutrales marcados', coverage['endpoint_prior'], enriched['coverage']['endpoint_prior']],
        ['Calidad bancaria al menos 0,8', coverage['high_quality'], enriched['coverage']['high_quality']],
        ['Observaciones reales de caja', coverage['cash_known'], enriched['coverage']['cash_known']],
        ['Enriquecimientos ERP usados', coverage['erp_used'], enriched['coverage']['erp_used']],
        ['HHI utilizable', coverage['hhi_used'], enriched['coverage']['hhi_used']],
        ['Trayectoria elegible para monitor', core['trajectory_states']['endpoint_eligible'], enriched['trajectory_states']['endpoint_eligible']],
        ['Comparación anual disponible', core['trajectory_states']['endpoint_seasonality_available'], enriched['trajectory_states']['endpoint_seasonality_available']],
    ], 'p{10cm}rr'))
    parts.append(f"Se entregan {coverage['companies'] * coverage['months']} filas empresa-mes en cada modo. Los priors no son diagnósticos de salud observada. No se calculó liquidez histórica real en estas ejecuciones: la caja conocida es cero observaciones, no un saldo imputado de cero. El núcleo usa cobertura de flujos. El snapshot ERP de {erp_manifest['audit']['erp']['snapshot_as_of']} aprovecha {erp_manifest['audit']['erp']['companies_with_usable_snapshot']} sociedades; no se retropropaga a los meses anteriores.")
    parts.append(r'''\subsection*{8.2. Gates ejecutados}
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
        'reproducible_state_classification': 'Estados reproducibles sobre el panel publicado',
        'priors_remain_unrated': 'Los priors no se presentan como salud evaluada',
    }
    parts.append(table(['Control', 'Banco', 'ERP experimental'], [
        [labels[key], 'Cumple' if passed else 'NO CUMPLE', 'Cumple' if enriched['gates'][key] else 'NO CUMPLE']
        for key, passed in core['gates'].items()
    ], 'p{10cm}rr'))
    parts.append(r'''\subsection*{8.3. Correlaciones de Spearman}
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
    parts.append(r'''\subsection*{8.4. Distribución y saturación}
Se distingue saturación por clipping de masas explicables por disponibilidad de datos. No se fuerza la distribución a uniforme ni se transforma el score a percentiles para aparentar calibración.''')
    distribution_rows = [[label, number(core['endpoint_score'][key], 2), number(enriched['endpoint_score'][key], 2)]
                         for key, label in [('min', 'Mínimo'), ('p05', 'P5'), ('median', 'Mediana'), ('p95', 'P95'), ('max', 'Máximo')]]
    distribution_rows.extend([
        ['Fracción en 0 o 100', percent(core['endpoint_saturation_all']), percent(enriched['endpoint_saturation_all'])],
        ['Peor saturación mensual, sin priors', percent(max(row['saturation_observed'] for row in core['monthly_diagnostics'])), percent(max(row['saturation_observed'] for row in enriched['monthly_diagnostics']))],
    ])
    parts.append(table(['Estadístico de score final', 'Banco', 'ERP experimental'], distribution_rows))
    parts.append(r'''La deuda sin desembolsos observados se queda en el prior 0,5, no se convierte en salud perfecta. Ese empate no es evidencia de calibración. El gate de extremos no valida probabilidades ni una correspondencia con ratings externos.

\subsection*{8.5. Controles de trayectoria y anticipación}
Para la comparación del enunciado se imponen dos bases lineales de 24 meses: 45 a 65 y 82 a 68. Se mantiene igual el resto de ajustes y se usa confirmación normalizada $x=2B/100-1$. Es un control algebraico del momentum y su suma, no una identificación de Northbrook o Velasco en los CSV.''')
    trajectory = core['trajectory_control']
    parts.append(table(['Caso idealizado', 'Base final', 'Momentum final', 'Score ajustado'], [
        ['Recuperación', trajectory['recovery_final_base'], number(trajectory['recovery_momentum']), number(trajectory['recovery_final_score'], 2)],
        ['Deterioro', trajectory['deterioration_final_base'], number(trajectory['deterioration_momentum']), number(trajectory['deterioration_final_score'], 2)],
    ]))
    parts.append(r'''El control de tesorería fija caja inicial 300, doce meses de cobros 120, pagos operativos 100 y deuda 5. Después los cobros bajan diez unidades por mes, hasta un suelo de cinco. La caja de referencia se acumula causalmente desde la reserva inicial, sin ajustar esa reserva al resultado del detector.

Este control matemático, distinto de la regla operativa del monitor, activa una señal si el score cae al menos cinco puntos respecto a la mediana de los tres meses previos al shock y el momentum es inferior a $-0{,}1$. La caja de referencia no entra como feature en el modo de núcleo bancario; un segundo modo sí aporta cada saldo conocido y compromisos 105. La monotonicidad se comprueba desde el inicio del deterioro hasta el primer saldo no positivo.''')
    stress = core['stress_control']
    parts.append(table(['Variante del control', 'Mes alerta', 'Mes caja no positiva', 'Antelación', 'Monótono'], [
        [label, row['first_alert_month_index'] + 1 if row['first_alert_month_index'] is not None else 'Sin alerta', stress['cash_nonpositive_month_index'] + 1,
         str(row['lead_months']) + ' meses' if row['lead_months'] is not None else 'n/d', 'Sí' if row['monotone_from_shock_to_cash_loss'] else 'No']
        for label, row in [('Solo banco', stress['variants']['bank_core']), ('Con caja conocida', stress['variants']['known_cash'])]
    ], 'p{4cm}rrrr'))
    parts.append(r'''Los meses se numeran desde uno. Estos resultados demuestran respuesta al escenario fijado, no ocho meses de anticipación general en empresas reales ni una precisión determinada de predicción del colapso. El saldo inicial y la intensidad del deterioro condicionan la antelación. Las pruebas unitarias también verifican que un bache aislado no activa momentum persistente.

\subsection*{8.6. Ejecución y entregables}
Desde la raíz del repositorio, usando NumPy y SciPy ya declarados en \texttt{requirements.txt}:
\begin{verbatim}
python3 algorythm/calc_score.py
python3 algorythm/validate_score.py --strict
python3 -m algorythm.calc_score --erp-snapshot-assumed-positive \
  --output algorythm/engine_results_erp
python3 -m algorythm.validate_score \
  --results algorythm/engine_results_erp --strict
python3 -m algorythm.behavior_benchmark --calibrate
python3 -m algorythm.behavior_benchmark --evaluate
python3 -m algorythm.behavior_benchmark --real-data
python3 -m algorythm.render_score_report
python3 -m unittest discover -s algorythm -p 'test_*.py' -v
python3 -m algorythm.score_monitor --watch
\end{verbatim}
La salida estándar está en \texttt{algorythm/engine\_results/}; la experimental, en \texttt{engine\_results\_erp/}. Cada una contiene CSV empresa-mes, panel NumPy, manifiesto y validación JSON. Los valores sin redondear permiten reconstruir exactamente cada waterfall. El validador rechaza artefactos cuyo código no coincide con el manifiesto.

El motor devuelve un diccionario de arrays, sin requerir Pandas. Las columnas principales son \texttt{score}, \texttt{liquidity\_points}, \texttt{collections\_points}, \texttt{debt\_points}, \texttt{momentum\_points}, \texttt{growth\_points}, \texttt{fragility\_points} y \texttt{clipping\_points}. Las pruebas comprueban también prefijos temporales, caja no retropropagada, ERP ausente, conversión inválida, unidades monetarias y estados sin evidencia.

\textbf{Conclusión.} Se entrega un índice aditivo ejecutable y controles reproducibles. No se ha demostrado calibración crediticia, independencia de los factores, disponibilidad histórica de caja ni anticipación empírica sobre Embat. El siguiente paso para afirmar capacidad de riesgo real exige etiquetas, semántica verificada y evaluación fuera de muestra.''')
    parts.append(f"Entorno de la ejecución bancaria: Python {manifest['runtime']['python']} y NumPy {manifest['runtime']['numpy']}. Los parámetros completos y hashes se conservan en el manifiesto.")
    return '\n\n'.join(parts) + '\n'


def render_trajectory(synthetic, real, core):
    tests = synthetic['test']
    cfg = synthetic['config']
    parts = [r'''\section*{9. Trayectorias, monitor y evaluación temporal}
\subsection*{9.1. Protocolo y separación de evidencias}
Se fijó el protocolo antes de ejecutar las nuevas pruebas: 400 trayectorias por escenario, 36 meses, cambios a partir del índice 12, ruido autocorrelacionado y siete familias. La semilla 101 es de desarrollo; 202 es validación y 303 es test. Los parámetros financieros del score no se optimizaron sobre estas etiquetas sintéticas. Solo se compararon dos o tres confirmaciones del monitor en desarrollo; se congeló la opción admisible más rápida antes de evaluar las otras semillas.

El escenario gradual se distingue del abrupto. La caja de evaluación tras el cambio parte de una reserva entre 0,5 y 6 meses de pagos, fijada por el generador y nunca introducida como feature. Las trayectorias que no agotan caja se declaran censuradas. Esta construcción no convierte los escenarios propios en empresas reales ni en un test externo del leaderboard.''']
    parts.append(f"La configuración seleccionada requiere {cfg['persistence_months']} valores mensuales consecutivos de momentum fuera de $\\pm {number(cfg['momentum_threshold'], 2)}$, calidad bancaria al menos {number(cfg['minimum_quality'], 2)} en las dos ventanas comparadas y bases maduras. Se requieren {cfg['neutral_persistence_months']} meses neutros para cerrar un episodio. El nivel 60 diferencia giro temprano de deterioro con base débil; son reglas de diseño, no umbrales de impago calibrados.")
    parts.append(r'''\subsection*{9.2. Sensibilidad en el test sintético reservado}
Detección en seis meses significa emisión posterior al inicio del cambio y antes de que transcurran seis observaciones mensuales. El retraso se mide desde el inicio de ese cambio, sin retrotraer la fecha de alerta al primer indicio aún no confirmado.''')
    parts.append(table(['Escenario', 'Detectado en 6 meses', 'Retraso mediano'], [
        [label, percent(tests[key]['detection_within_6_months']), number(tests[key]['median_delay_months'], 1) + ' meses']
        for key, label in [('deterioration', 'Deterioro gradual'), ('improvement', 'Mejora'), ('recovery', 'Recuperación'), ('abrupt_deterioration', 'Deterioro abrupto')]
    ]))
    parts.append(f"En deterioro gradual, {percent(tests['deterioration']['fraction_detected_while_base_at_least_60'])} de las detecciones se produce con base todavía al menos 60. La diferencia entre sensibilidades de mejora y deterioro es {number(100 * synthetic['bidirectional_recall_gap'], 2)} puntos porcentuales: la respuesta es bidireccional, pero no se afirma igualdad perfecta.")
    parts.append(r'''\subsection*{9.3. Falsas alertas y límite de estacionalidad}
Se cuentan eventos adversos emitidos, incluidas escaladas de severidad, por empresa-año elegible. No se limita artificialmente la emisión a una alerta anual para pasar el control. La fracción de series con alguna falsa alerta mide otra cosa: acumula el riesgo de error a lo largo de todo el horizonte.''')
    parts.append(table(['Serie sin deterioro estructural', 'Avisos adversos/año', 'Series con falso aviso'], [
        [label, number(tests[key]['adverse_alerts_per_company_year']), percent(tests[key]['false_adverse_path_fraction'])]
        for key, label in [('stable', 'Estable con ruido'), ('pulse', 'Bache de un mes'), ('seasonal', 'Ciclo anual repetitivo')]
    ]))
    parts.append(f"Con comparación anual disponible, la tasa adversa en series estacionales es {number(tests['seasonal']['adverse_alerts_per_year_when_annual_context_available'])} por empresa-año. La fracción acumulada de falsos avisos estacionales sigue siendo alta: no se oculta. Antes de observar un ciclo comparable no se puede identificar con certeza que una caída sea estacional. El control anual requiere dos ventanas trimestrales actuales y sus equivalentes del año anterior; exige al menos dos observaciones fiables en cada bloque y compatibilidad de ambas diferencias dentro de 0,02.")
    parts.append(r'''\subsection*{9.4. Antelación: evento observado frente a predicción}
La antelación solo se calcula cuando se conoce la fecha del evento de referencia. El feed operativo mantiene \texttt{lead\_months=null}; no transforma el momentum en una fecha de quiebra ni añade ocho meses a todas las alertas.''')
    control = synthetic['operational_cash_control']
    parts.append(f"En el control fijo con caja inicial 300, el monitor confirmado avisa en el mes {control['first_confirmed_alert_month_index'] + 1} y la caja se hace no positiva en el mes {control['cash_nonpositive_month_index'] + 1}: antelación {control['lead_months']} meses. Es distinto del aviso matemático de ocho meses de la sección anterior, que usa otra regla y no incorpora las tres confirmaciones operativas.")
    parts.append(table(['Escenario con caja de referencia', 'Colapsos', 'Censuradas', 'Aviso al menos 3 meses antes'], [
        [label, tests[key]['cash_collapses'], tests[key]['cash_paths_censored'], percent(tests[key]['fraction_collapses_warned_3_months'])]
        for key, label in [('deterioration', 'Deterioro gradual'), ('abrupt_deterioration', 'Deterioro abrupto')]
    ]))
    parts.append(r'''Un shock abrupto con poca reserva puede agotar caja antes de acumular confirmaciones. No se garantiza antelación universal: el filtro intercambia rapidez por estabilidad. Las reservas y severidad prefijadas del generador condicionan estos porcentajes.

\subsection*{9.5. Reserva interna por grupos sobre los CSV de Embat}''')
    parts.append(f"Se reservaron {len(real['held_out_groups'])} grupos, {real['held_out_companies']} sociedades, sin utilizarlos para seleccionar parámetros del monitor. Tras exigir cobertura suficiente en las ventanas comparadas y futuras quedan {real['usable_company_cutoffs']} observaciones empresa-corte de {real.get('observed_companies', 0)} sociedades y {real.get('observed_groups', 0)} grupos. La evaluación usa los cortes de marzo y junio de 2026 y los tres meses siguientes. Este dataset ya se había explorado: no es un test externo ciego.")
    parts.append(f"La prueba técnica de puntuar esas empresas separadas del resto del lote arroja una diferencia máxima de {number(real['technical_generalization_max_batch_difference'])}. Esto verifica ausencia de dependencia de las otras filas, no precisión financiera sobre empresas nuevas.")
    if real.get('status') == 'evaluated_auxiliary_proxy':
        associations = real['future_coverage_spearman']
        intervals = real['grouped_intervals']['intervals']
        parts.append(table(['Ordenación frente a cobertura futura', 'Spearman', r'Intervalo bootstrap 95\%'], [
            [label, number(associations[key]), '[' + '; '.join(number(value) for value in intervals[key]) + ']' if intervals and intervals[key] else 'n/d']
            for key, label in [('score', 'Score dinámico'), ('q3', 'Cobertura persistida, 3 meses'), ('q6', 'Cobertura persistida, 6 meses')]
        ]))
        parts.append(table(['Señal actual frente a cambio próximo', 'Señales', 'Precisión sobre proxy', 'Recall sobre proxy'], [
            [label, real[key]['signals'], percent(real[key]['precision_on_proxy']) if real[key]['precision_on_proxy'] is not None else 'n/d', percent(real[key]['recall_on_proxy']) if real[key]['recall_on_proxy'] is not None else 'n/d']
            for key, label in [('deterioration', 'Deterioro'), ('improvement', 'Mejora')]
        ]))
        parts.append(f"La asociación de momentum con el cambio del siguiente trimestre es {number(real['future_change_spearman']['momentum'])}. Los cambios consecutivos comparten el nivel actual con signos opuestos; ruido, estacionalidad y reversión a la media pueden contribuir a esa asociación. No justifica invertir el signo del momentum para maquillar el test.")
    parts.append(r'''\textbf{Resultado no concluyente para precisión financiera.} La cobertura futura es un objetivo auxiliar de flujos, no una etiqueta de salud. Los intervalos de ranking son amplios y no demuestran superioridad frente a persistencia a seis meses. Las señales de trayectoria actual no predicen bien la dirección del trimestre siguiente en esta reserva. No se reajustaron parámetros contra ese resultado.

\subsection*{9.6. Monitor implementado y cobertura operativa}
Cada ejecución de \texttt{calc\_score.py} publica estados, manifiesto y avisos. \texttt{score\_monitor.py --watch} comprueba automáticamente nuevos snapshots sin consultas por empresa. Valida hashes de publicación, deduplica identificadores y conserva el cursor temporal. Una revisión del mismo corte se etiqueta como revisión; un cambio de modelo reinicializa la referencia sin atribuirle un cambio financiero. Los cortes antiguos del time-machine no retroceden el cursor.

Se separan \texttt{alerts\_history.json} (análisis retrospectivo), \texttt{alerts\_feed.json} (avisos publicados) y \texttt{monitor\_state.json} (deduplicación y cursor). Son avisos locales; no se envían correos ni se ejecutan operaciones bancarias. Los drivers son diferencias exactas de contribuciones frente a tres meses antes. Se marca si aparece evidencia ERP o de caja nueva.

El estado \texttt{ESTABLE} describe trayectoria, no solvencia. El nivel, la disponibilidad de evidencia y el estado deben mostrarse por separado. La baja cobertura y los priors no se etiquetan como empresas sanas.''')
    parts.append(table(['Estado al último corte bancario', 'Sociedades'], [
        [label.replace('_', r'\_'), count] for label, count in core['trajectory_states']['endpoint_counts'].items()
    ]))
    parts.append(r'''\textbf{Pendiente externo:} validar acierto financiero y antelación empírica requiere la referencia o el evaluador oficial de Embat, y eventos de tesorería fechados independientemente. El código operativo, los controles sintéticos y las asociaciones descriptivas no sustituyen esa evaluación.''')
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
    behavior = []
    for name in ('synthetic_validation.json', 'real_holdout.json'):
        with (ROOT / 'algorythm' / 'behavior_results' / name).open(encoding='utf-8') as source:
            report = json.load(source)
        for filename, expected in report['source_sha256'].items():
            if sha256(ROOT / 'algorythm' / filename) != expected:
                raise ValueError('Trajectory results are stale; rerun their frozen evaluation.')
        behavior.append(report)
    trajectory = ROOT / 'algorythm' / 'formula' / 'trajectory_benchmark_results.tex'
    trajectory.write_text(render_trajectory(behavior[0], behavior[1], reports[0][0]), encoding='utf-8')
    print(f'Rendered {trajectory}')


if __name__ == '__main__':
    main()
