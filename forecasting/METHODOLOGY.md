# Metodología y reproducción

Guía rápida de colaboración: [README.md](README.md). Ranking común: [LEADERBOARD.md](benchmarks/LEADERBOARD.md).


Rama: `feat/forecast-stress-benchmarks`. Se conservan el score existente y el baseline exploratorio
de `research/arquitectura_carlos/experiments.py`. Este último predice margen operativo a tres meses;
aquí el **target es el score bancario en t+h**, necesario para extender la gráfica. Sus errores no
son directamente comparables por tener unidades y targets distintos.

## Ejecutar

Desde la raíz, con Python y las dependencias de `requirements.txt`:

```bash
python -m forecasting.benchmark --dataset data \
  --context forecasting/datasets/external/external_context.csv
python -m pytest forecasting/tests/test_forecast.py backend/test_forecasts.py -q
```

El snapshot externo está versionado: el benchmark no necesita red. Para actualizar FX y Eurostat:

```bash
python -m forecasting.context
```

`policy_rates.json` transcribe decisiones oficiales fechadas y debe actualizarse cuando
haya nuevas decisiones. El descargador conserva fuentes, disponibilidad, hashes y errores.

Sensibilidad separada, permitiendo el supuesto de publicación de USD/EUR:

```bash
python -m forecasting.benchmark --dataset data \
  --context forecasting/datasets/external/external_context.csv \
  --allow-assumed-publication --output forecasting/artifacts/sensitivity
```

Resultados principales: [benchmarks/baseline/REPORT.md](benchmarks/baseline/REPORT.md); detalle completo
en `benchmark.json`. `artifacts/forecasts.json` se genera localmente. Los datos sintéticos congelados están versionados en `datasets/synthetic/v1/`.
Semilla, protocolo, versiones, hashes y particiones quedan en el informe. Por defecto: **19 escenarios
× 36 empresas × 36 meses = 24.624 observaciones sintéticas**. `--stress-companies 200` aumenta la carga.

## Qué compara

Horizontes directos de **1, 3 y 6 meses**: persistencia, media reciente, tendencia amortiguada,
estacionalidad anual, Ridge, Ridge con contexto, random forest, boosting, boosting con contexto
y boosting por cuantiles. Los modelos supervisados predicen el cambio desde el score actual.
La estacionalidad vuelve a persistencia cuando falta un antecedente anual observado. No usamos
redes profundas con una única historia de 24 meses y pocos orígenes temporales.

El target usa la versión **solo banco**, con parámetros congelados. Ni saldo final ni estados
actuales de facturas entran en las features históricas. El motor también se prueba con ERP sintético.
La respuesta de previsión trae su propio histórico: no se mezcla con históricos ERP o fixtures.

Las features usan seis meses pasados: score, pendiente, variabilidad, componentes, margen de flujos,
volúmenes, deuda, concentración, calendario y calidad. Nunca entran nombre del cliente, identificador
del donante, etiqueta del shock ni oráculo de caja.

## Evitar resultados demasiado buenos

Separación determinista por **grupo empresarial**: 60/20/10/10% para entrenamiento, calibración,
validación y test. Todas las filiales permanecen juntas. Se aplica antes del filtro de calidad.

- Entrenamiento: targets conocidos hasta índice 11 (corte 2025-09-01).
- Calibración: origen 11, otros grupos; targets terminan como máximo en 17.
- Validación y test: orígenes desde 17 (2026-03-01), dos conjuntos de grupos distintos.
- Selección: menor MAE medio entre grupos en validación; dentro de un 2% se prefiere el orden
  de simplicidad fijado en `CANDIDATES`. Ni test ni estrés cambian la elección.
- Se exportan previsiones de **los mismos modelos congelados que se evaluaron**, sin reentrenar con el test.
  Las peticiones HTTP leen JSON, no entrenan ni deserializan modelos ejecutables.

Métricas: MAE, RMSE, MAE por grupo con bootstrap por grupo, dirección equilibrada, recall separado
de mejora/deterioro, falsas predicciones adversas sobre estabilidad, pinball, Brier, cobertura y
anchura. Hay desglose por país conocido/desconocido. El bootstrap por grupo trata la dependencia
entre filiales y ventanas solapadas, pero no resuelve la escasez de regímenes macro ni de tiempo.

**A seis meses solo hay un origen de entrenamiento y uno de test**; en la ejecución inicial el test
contiene 59 empresas de 15 grupos. Un MAE de seis meses menor que el de tres no demuestra que predecir
más lejos sea más fácil: cambian las empresas elegibles, periodos y número de observaciones.

## Datos adversarios

Bloques de tres meses de donantes de entrenamiento, usando únicamente sus primeros doce meses.
Se preservan relaciones entre cobros, pagos, deuda y escala; los perfiles introducen cobros más
regulares en restauración, hitos trimestrales en construcción y pagos más estables en servicios.
Las magnitudes son **hipótesis de simulación**, no estadísticas de clientes.

Inspiración en hechos públicos descritos por Embat:

- [VICIO](https://www.embat.io/es/casos-de-exito/vicio): restauración, expansión y cobros multicanal.
- [Grupo Construcía](https://www.embat.io/es/casos-de-exito/grupo-construcia): construcción y tesorería de grupo.
- [Grupo Viko](https://www.embat.io/es/casos-de-exito/viko): servicios con filiales en España y México.

No atribuimos cifras, deuda, impagos ni shocks reales a esas empresas. Los nombres documentan
la inspiración; las entidades son `SYN_*`, con euros como unidad de simulación. El shock FX es un
encarecimiento hipotético de compras importadas, no una conversión inferida a partir del país.

Casos: control, estacionalidad, bache recuperable, deterioro, mejora, cobros retrasados, intereses,
FX, expansión que consume caja, pérdida del cliente principal, refinanciación, shock de grupo,
devoluciones, interrupción de datos, arranque sin historia, crisis compuesta, actividad cero,
vencimiento extraordinario de deuda y recuperación.

Cada caso exporta banco `.npz`, control emparejado, ERP simulado, metadatos y oráculo de caja separado:

```python
import numpy as np
from algorythm.score_engine import calculate_scores

bank = dict(np.load('forecasting/datasets/synthetic/v1/compound_crisis.npz'))
erp = dict(np.load('forecasting/datasets/synthetic/v1/compound_crisis_erp.npz'))
scores = calculate_scores(bank, erp)
```

Prueba motor y predictores a nivel de panel mensual; no sustituye los tests del adaptador de
transacciones ni crea nueve CSV que aparenten ser datos originales. El contagio aplica un shock
compartido; no valida un grafo de contrapartes que el dataset no aporta.

Se mide score acotado/finito, identidad aditiva, dirección frente al control, falsas alertas en
controles, retraso de detección y anticipación frente a agotamiento de caja **solo sintético**, con
no detecciones y casos censurados. La caja-oráculo nunca es feature. Los tests verifican que cambiar
donantes reservados o futuro no cambia los datos generados.

## Contexto externo y disponibilidad

| Fuente | Variable | Tratamiento temporal |
|---|---|---|
| [BCE: tipos oficiales](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html) | Tipo de depósito, contexto monetario común | Fecha efectiva; vigente hasta siguiente decisión |
| [BCE: SDMX](https://www.ecb.europa.eu/stats/ecb_statistics/sdmx/html/index.en.html) | Cambio USD/EUR mensual | Lag supuesto de siete días desde fin de mes, solo sensibilidad |
| [Eurostat: API](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/) | Producción industrial, construcción, ventas minoristas de España | Series revisadas disponibles desde descarga, no retrodatadas |

Contrato CSV: `indicator,geo,sector,period,available_at,value,availability_basis,source_url,retrieved_at`.
Admite publicaciones históricas comprobadas con `availability_basis=verified_publication`.
El join elige la revisión más reciente disponible en el corte. Incluye ausencia y antigüedad;
descarta datos de más de 120 días salvo tipos oficiales vigentes.

Hay país informado en 230/1.286 empresas y **ningún sector**. No se infieren por nombre o moneda.
Las series sectoriales quedan preparadas para entidades con metadatos verificados; `feature_panel`
acepta `country` y `sector` en los registros de empresa. No se atribuyen sectores a empresas anónimas.

La comparación inicial no demuestra mejora consistente al añadir tipos; Ridge con contexto empeora
a un mes. La sensibilidad con FX tampoco cambia los ganadores. Resultados de ambas ejecuciones en
`benchmarks/baseline/EXTERNAL_COMPARISON.json`. No presentar el enriquecimiento como mejora hasta que
una evaluación reservada lo demuestre.

## Escenarios y explicación

P10 = pesimista, P50 = central/conservador, P90 = optimista. "Conservador" nombra la mediana;
no añade aversión al riesgo. Baselines y regresores usan cuantiles de residuales de calibración,
con igual peso total por grupo. Boosting por cuantiles ajusta bandas con no conformidad.
Cobertura del 80% **nominal y marginal**: no garantía condicional ni simultánea sobre una trayectoria.
Se enseña la cobertura realmente observada. Los límites se acotan a [0,100] y no se cruzan.

Probabilidades de subir/estabilizarse/caer: distribución empírica de residuales, banda neutra ±3
puntos, evaluadas con Brier. No son probabilidades certificadas de solvencia o quiebra.

Explicación = score actual + referencia + contribuciones + calibración + recorte. Ridge: lineal
exacta. Árboles: sustitución secuencial desde referencia de entrenamiento, **dependiente del orden,
no SHAP ni causalidad**. Top cinco y agregado de otros factores preservan la identidad.

## Demo y API

```bash
# Desde la raíz:
python -m uvicorn backend.main:app --port 8000
# Desde front/, en otra terminal:
npm ci
npm run dev
```

Abrir **`http://localhost:3000/prevision`**, accesible desde navegación y ficha. Funciona con
artefactos locales aunque el resto del front use fixtures. Para usar API desde Next:
`FORECAST_API_URL=http://localhost:8000`. Directorio alternativo en ambos procesos:
`XRAY_FORECAST_DIR=/ruta/absoluta`. Las caídas no se sustituyen por curvas inventadas.

- `GET /api/companies/{id}/forecast`: histórico, cuantiles, probabilidades y explicación.
- `GET /api/forecasts`: catálogo con disponibilidad.
- `GET /api/benchmarks/forecasts`: comparación, protocolo y versiones.

Se generan previsiones para 1.008 empresas y abstención para 278: se requieren seis meses
consecutivos con actividad y calidad suficiente. Los puntos son 1/3/6 meses; entre ellos hay
interpolación visual. API: 503 sin artefactos, 404 para identificador desconocido.

## Segunda tanda de modelos (v2)

Siete contribuciones nuevas en `experiments/`, registradas como ejecuciones independientes
(`carlos__*-v1`). Motivación: pérdidas robustas o por mediana alineadas con la métrica MAE,
reversión parcial a la media reciente, monotonía como hipótesis y combinación robusta.

**Selección de hiperparámetros solo dentro de train**: `GroupKFold(n_splits=5)` sobre los grupos
de entrenamiento, métrica = MAE macro por grupo (media entre grupos de la media de
|y − clip(actual+pred, 0, 100)| en el fold reservado), escalador ajustado por fold dentro de
pipelines sklearn. Rejillas congeladas:

- `ridge_groupcv`: alpha ∈ {1, 3, 10, 30, 100, 300, 1000, 3000}.
- `huber_linear` y `huber_cqr`: alpha ∈ {1e-3, 1e-2, 0.1, 1, 10, 30, 100} × epsilon ∈ {1.35, 2.0}.
- `median_linear`: alpha ∈ {0.001, 0.01, 0.05, 0.2, 1} (QuantileRegressor q=0.5, solver highs).
- `partial_mean_reversion`: delta = λ·(x_k − x_0), k ∈ {media_3m, media_6m}, λ ∈ {0, 0.1, …, 1.0}.
- `monotone_boosting`: sin tuning (test de hipótesis); monotonía −1 en score_actual, +1 en medias
  y márgenes 3m/6m.
- `robust_ensemble`: media de deltas de huber_linear + ridge_groupcv + media reciente; explicación
  = media de contribuciones aditivas de los miembros.

Una CV temporal dentro de train no es viable a 6M (un solo origen de entrenamiento) y queda muy
limitada a 1M/3M, por eso la selección interna es por grupos, no por tiempo.

**Bootstrap emparejado por grupo**: cada ejecución nueva reentrena los diez candidatos baseline y
compara el MAE por grupo en validación frente a cada uno (2.000 remuestreos de grupos, semilla 419).
El leaderboard muestra Δ frente al candidato baseline de cada horizonte: positivo = mejora; `✓`
cuando el IC 95% excluye 0. La regla del 2% sigue eligiendo; el IC solo dice si la diferencia se
distingue del ruido.

**Los IC no están ajustados por selección múltiple** ni por la mirada exploratoria previa a
validación: son **evidencia favorable en validación exploratoria**, no confirmación de
generalización (sesgo de selección en comparación de modelos: Cawley & Talbot, 2010, JMLR 11).
La confirmación necesita el nuevo holdout congelado.

**v1 → v2**: las ejecuciones v1 usaban la media de los MAE de los cinco folds, que daba más peso a
los grupos de folds pequeños. En v2 la métrica interna agrupa todas las predicciones out-of-fold
(cada grupo sale una vez en GroupKFold) y puntúa una sola vez con MAE macro por grupo: todos los
grupos pesan igual. Las ejecuciones v1 se conservan para el registro; la tabla de abajo usa v2.
Los parámetros seleccionados **no cambiaron** en ningún modelo ni horizonte, así que las métricas
de validación son idénticas entre v1 y v2.

**Divulgación**: el diagnóstico exploratorio inicial miró números de validación de ridge, huber y
media reciente antes de congelar las rejillas; validación no es un holdout fresco para estas
hipótesis y la confirmación necesita el nuevo holdout congelado que ya pide el protocolo.
Observación documentada, sin cambiar: el ajuste de mediana de calibración (origen 11) penaliza a
`trailing_mean` a 3M (6,79 sin calibrar frente a 7,20 calibrado).

**Resultados** (validación; Δ frente al candidato baseline con IC 95%):

| Horizonte | Modelo | MAE val | Δ [IC 95%] | Cobertura | MAE test* |
|---|---|---:|---|---:|---:|
| 1M | huber_linear | 4,17 | +0,38 [+0,10, +0,74] ✓ | 80,9% | 6,76 |
| 1M | huber_cqr | 4,17 | +0,38 [+0,10, +0,74] ✓ | 78,8% | 6,76 |
| 1M | median_linear | 4,17 | +0,38 [+0,03, +0,78] ✓ | 82,0% | 6,74 |
| 1M | ridge_groupcv | 4,34 | +0,21 [+0,06, +0,39] ✓ | 81,5% | 6,66 |
| 3M | robust_ensemble | 7,18 | +0,03 [−1,59, +1,57] | 75,5% | 11,81 |
| 3M | trailing_mean (baseline) | 7,20 | — | 82,4% | 14,90 |
| 6M | median_linear | 9,58 | +0,29 [−1,07, +1,67] | 58,7% | 8,09 |
| 6M | monotone_boosting | 9,56 | +0,30 [−1,80, +2,03] | 58,7% | 10,33 |

Recomendación con incertidumbre: a **1M** los lineales robustos (huber/median) muestran evidencia
favorable en validación exploratoria frente a ridge, con IC que excluye cero; `huber_linear` es el
candidato por la regla común — empata a 4,17 con `median_linear` y el desempate por orden de nombre
dentro de la regla lo favorece. La comparación de test a 1M (huber 6,76 frente a ridge 6,78) es una
diferencia observada pequeña sobre un test ya visto: no confirma nada nuevo. El experimento de
intervalos CQR es **inconcluyente**: no mejora la cobertura a 1M (78,8% frente a 80,9% del mismo
centro sin CQR) y solo marginalmente a 6M (69,6% frente a 65,2%). A **3M** nada supera a la media
reciente; `partial_mean_reversion` la reproduce exactamente (λ=1 sobre media_3m). A **6M** todos
los IC incluyen 0 y la cobertura es pobre (`median_linear` 58,7%, ridge 63,0%, lejos del 80%
nominal): no proclamamos ganador; `median_linear` es candidato por la regla, pendiente del nuevo
holdout.

**Candidato ≠ promoción**: la regla del ranking solo propone un candidato por horizonte; ningún
modelo de esta tanda está aprobado para promoción (quedan por revisar explicación, recalls,
cobertura y estrés) y los modelos de la demo no cambian. Idea descartada: boosting sobre residuos
se descartó por presupuesto de tiempo; es una idea distinta de promediar modelos entrenados
independientemente como hace `robust_ensemble`, y no debe leerse como equivalente.

## Criterios del reto

| Criterio | Evidencia |
|---|---|
| Generalización | Grupos reservados, corte temporal y límites de muestra explícitos |
| Dos direcciones | Score futuro, recalls separados, mejora y recuperación sintéticas |
| Bache frente a caída | Bache con devolución de caja, estacionalidad, tasas de alarma |
| Explicación | Descomposición aditiva por predicción |
| Anticipación | Horizontes 1/3/6 y lead time del monitor frente al oráculo sintético |
| Producto | Curvas, probabilidades, horizontes y comparación en `/prevision` |

No se cambian pesos del score ni umbrales del monitor al ver fallos: se registran para el siguiente
ciclo de desarrollo con un nuevo test reservado.

## Verificación de esta entrega

- Suite completa tras integrar `main`: **172 tests aprobados** (`pytest forecasting/tests algorythm backend`).
- Segunda tanda (v2): **37 tests** (`pytest forecasting/tests backend/test_forecasts.py -q`), incluidos
  los del bootstrap emparejado, la columna Δ del leaderboard, las siete factorías nuevas
  (fit → calibrate → predict, probabilidades y reconstrucción de explicaciones), la agregación OOF
  agrupada de `group_cv_select` y el registro de dependencias locales.
- Siete ejecuciones `carlos__*-v1` con `--final-test` y seis `carlos__*-v2` (CV corregida) registradas;
  `python -m forecasting.registry` regenera `LEADERBOARD.md`/`.json` sin excluir ninguna y conserva
  `equipo__extra-trees-v1`.
- Front: lint y build con `npm run build -- --webpack` aprobados. Turbopack no pudo abrir
  su puerto auxiliar en este entorno; se verificó la compilación de producción con webpack.
- Navegador Chrome: cuatro curvas, botones 1/3/6, 30 filas de comparación y abstención por falta
  de datos, sin errores JavaScript. Vista móvil de 390 px sin desbordamiento horizontal.
- Los tres endpoints de previsión responden 200 con los artefactos generados.

Se añadió la dependencia `matplotlib` que ya importaba el backend y la detección de `data/`
en el constructor DuckDB y los objetos de palancas, manteniendo compatibilidad con `dataset/`.
