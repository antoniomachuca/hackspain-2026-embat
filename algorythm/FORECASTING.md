# Previsión, datos adversarios y selección de modelos

Rama: `feat/forecast-stress-benchmarks`. Se conservan el score existente y el baseline exploratorio
de `research/arquitectura_carlos/experiments.py`. Este último predice margen operativo a tres meses;
aquí el **target es el score bancario en t+h**, necesario para extender la gráfica. Sus errores no
son directamente comparables por tener unidades y targets distintos.

## Ejecutar

Desde la raíz, con Python y las dependencias de `requirements.txt`:

```bash
python -m algorythm.forecast_benchmark --dataset data \
  --context algorythm/forecast_results/external_context.csv
python -m pytest algorythm/test_forecast.py backend/test_forecasts.py -q
```

El snapshot externo está versionado: el benchmark no necesita red. Para actualizar FX y Eurostat:

```bash
python -m algorythm.forecast_context
```

`forecast_policy_rates.json` transcribe decisiones oficiales fechadas y debe actualizarse cuando
haya nuevas decisiones. El descargador conserva fuentes, disponibilidad, hashes y errores.

Sensibilidad separada, permitiendo el supuesto de publicación de USD/EUR:

```bash
python -m algorythm.forecast_benchmark --dataset data \
  --context algorythm/forecast_results/external_context.csv \
  --allow-assumed-publication --output algorythm/forecast_sensitivity
```

Resultados principales: [forecast_results/REPORT.md](forecast_results/REPORT.md); detalle completo
en `benchmark.json`. `forecasts.json` y `synthetic/` se generan localmente y no se versionan.
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

bank = dict(np.load('algorythm/forecast_results/synthetic/compound_crisis.npz'))
erp = dict(np.load('algorythm/forecast_results/synthetic/compound_crisis_erp.npz'))
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
`forecast_results/EXTERNAL_COMPARISON.json`. No presentar el enriquecimiento como mejora hasta que
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

- Suite completa: **119 tests aprobados** (`pytest algorythm backend`).
- Front: lint y build con `npm run build -- --webpack` aprobados. Turbopack no pudo abrir
  su puerto auxiliar en este entorno; se verificó la compilación de producción con webpack.
- Navegador Chrome: cuatro curvas, botones 1/3/6, 30 filas de comparación y abstención por falta
  de datos, sin errores JavaScript. Vista móvil de 390 px sin desbordamiento horizontal.
- Los tres endpoints de previsión responden 200 con los artefactos generados.

Se añadió la dependencia `matplotlib` que ya importaba el backend y la detección de `data/`
en el constructor DuckDB, manteniendo compatibilidad con `dataset/`.
