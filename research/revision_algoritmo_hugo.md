# Revisión del motor de scoring (`algorythm/`)

**Fecha:** 2026-09-19 · **Commit revisado:** `2d0a17e` · **Autor:** Hugo Oliva (con análisis asistido por Claude)
**Alcance:** `score_engine.py`, `score_data.py`, `calc_score.py`, `validate_score.py`, tests, whitepaper y resultados en `engine_results/` y `engine_results_erp/`.
**Método:** lectura del código, ejecución de los 30 tests (todos pasan), y análisis empírico propio sobre los paneles exportados y los CSV completos (2,5 M transacciones, 900 k facturas). Todas las cifras de este documento salen de esos análisis, no de los JSON de validación del motor.

---

## 1. Veredicto

**Nota global: 5,5 / 10.**

El motor está construido con un rigor de ingeniería muy por encima de lo habitual en un hackathon: reproducible, point-in-time, con tests y explicabilidad exacta. Pero la señal que produce es ruidosa, está sesgada por la cobertura del categorizador bancario y no muestra relación con ningún indicador externo de estrés. Es un excelente chasis con un motor que hoy mide más la calidad del dato que la salud de la empresa.

| Dimensión | Nota | Resumen |
|---|---|---|
| Ingeniería y reproducibilidad | 9 | 30 tests pasan, hashes de código y datos en el manifiesto, waterfall aditivo exacto, sin look-ahead. |
| Explicabilidad | 8 | Descomposición en seis contribuciones exacta y honesta con el recorte a 0–100. |
| Generalización al test oculto | 8 | No hay ajuste por empresa: puntúa empresas nuevas sin riesgo. Pero no hay peer groups. |
| Uso del dato disponible | 3 | Descarta el 58 % del volumen bancario y todo el histórico del ERP. |
| Validez de la señal | 3 | Sin correlación con caja terminal negativa ni con facturas vencidas. |
| Trayectoria (momentum) | 2,5 | Anti-predictivo tras controlar el nivel; cambia de signo uno de cada cuatro meses. |
| Estabilidad | 4 | Ruido mes a mes muy superior al que pedía el brief. |

---

## 2. Lo que está bien

- **Diseño point-in-time estricto.** El snapshot ERP no se retropropaga, la caja no se reconstruye desde `balances.csv`, y hay tests que lo garantizan (`test_future_bank_and_erp_values_do_not_change_prefix`, `test_cash_snapshot_does_not_fill_earlier_months`).
- **El "no sé" es explícito.** `is_prior` marca 116 empresas sin evidencia al último corte en lugar de emitir un número falso.
- **Explicabilidad sin caja negra.** `score = Σ contribuciones` con error cero, incluido `clipping_points`. Mejor que un SHAP para el jurado.
- **Gates de validación predefinidos**, umbrales fijados antes de ejecutar (0,65 y 2 %), y modo `--strict` que falla en vez de ocultar.
- **Contrato de entrada validado**: rangos, NaN, negativos, pesos; el motor rechaza entradas inválidas.
- **Invariante a la unidad monetaria** (test explícito).

---

## 3. Problemas, por gravedad

### 3.1 El motor descarta el 58 % del dinero

Distribución del volumen absoluto de `transactions.csv` por categoría:

| Categoría | % filas | % volumen absoluto | Uso en el motor |
|---|---|---|---|
| `-` (sin categoría) | 24,9 | 38,8 | Descartada |
| `transfer` | 6,0 | 18,9 | Descartada |
| `collection` | 22,2 | 16,4 | Cobros |
| `payment` | 14,2 | 16,2 | Pagos |
| `utility` | 10,2 | 3,4 | Pagos |
| resto | 22,5 | 6,3 | Parcial |

Dentro de `-` hay descripciones evidentes: "PAGO PROVEEDORES", "PROVEEDORES [NUM]", "ABONO [COMPANY]", "REMUNERACION". Por empresa, la mediana de volumen no clasificado es el 29 %; el cuartil superior supera el 62 %.

### 3.2 El descarte sesga la liquidez, que es el 68 % de la varianza del score

Cuota de la varianza transversal del score al último corte por contribución:

| Contribución | Desv. típica (pts) | Cuota de varianza |
|---|---|---|
| Liquidez | 8,9 | 68 % |
| Cobros | 3,7 | 15 % |
| Momentum | 1,8 | 9 % |
| Deuda | 2,0 | 4 % |
| Crecimiento | 1,1 | 4 % |
| Fragilidad | 1,0 | ~0 % |

Correlaciones de Spearman con el signo neto del volumen descartado (`-` + `transfer`, últimos 3 meses):

| Medida | ρ |
|---|---|
| Pilar L vs signo neto de lo descartado | **−0,56** |
| Score vs signo neto de lo descartado | −0,49 |
| Distancia a 50 vs calidad bancaria | +0,46 |

Lectura: una empresa cuyos pagos cayeron en `-` parece líquida porque el motor solo ve sus cobros. El score depende de qué lado del libro falló el categorizador.

### 3.3 El score no acierta contra señales externas

Cruce del score del último mes con dos indicadores que el motor bancario no usa:

| Prueba | Resultado |
|---|---|
| AUC para separar las 29 empresas con caja terminal negativa (cuentas checking+saving) | **0,46** (peor que azar) |
| Misma prueba seis meses antes (mes 17), con el score | 0,48 |
| Misma prueba seis meses antes, con el momentum | 0,46 |
| ρ(score, tasa de facturas emitidas vencidas), 548 empresas con ≥20 facturas | **0,02** |
| ρ(pilar C, tasa de facturas emitidas vencidas) | 0,00 |
| ρ(score, caja terminal / salidas mensuales) | 0,08 |

El pilar de cobros no tiene relación con cómo cobra la empresa. Su correlación con el coeficiente de variación a 6 meses de los ingresos es **−0,64**: es una penalización a la estacionalidad disfrazada de calidad de cobro. Las devoluciones, la otra mitad del pilar, son el 0,02 % del volumen y no discriminan.

### 3.4 El momentum es anti-predictivo

Correlación parcial (por rangos) del momentum con el margen de flujo de los tres meses siguientes, controlando el margen de los tres meses actuales:

| Mes | n | ρ parcial (momentum, margen futuro) | ρ parcial (score, margen futuro) |
|---|---|---|---|
| 10 | 480 | −0,11 | −0,07 |
| 13 | 561 | −0,17 | 0,00 |
| 16 | 580 | −0,19 | −0,04 |
| 19 | 634 | −0,08 | −0,01 |

Sin controlar el nivel, el margen crudo de los últimos 3 meses predice el futuro mejor (ρ≈0,50) que el score (ρ≈0,30). Es decir, las transformaciones pierden información.

Causa probable: `velocity = (B_t − B_{t−3})/3` es una velocidad a 3 meses de un estadístico móvil de 3 meses. Es reversión a la media pura. El momentum cambia de signo en el **24 %** de los pares de meses consecutivos en que está activo.

El "8 meses de anticipación" del whitepaper sale de una rampa sintética (`stress_control`), no del dato. El propio JSON lo declara (`observed_on_real_companies: false`), pero el resumen ejecutivo lo presenta como resultado.

### 3.5 Ruido muy superior al objetivo del brief

El brief pedía estabilidad de rangos mes a mes > 0,85.

| Serie | ρ mes a mes (meses 14–23) | ρ a 6 meses (17→23) |
|---|---|---|
| Score del motor | 0,74–0,78 | **0,33** |
| Margen de flujo crudo a 3 meses | 0,79–0,84 | – |
| Margen de flujo crudo a 12 meses | 0,91–0,97 | 0,67 |

El score es menos estable que su propio ingrediente principal sin transformar. Un 16 % de las empresas observadas se mueve más de 10 puntos de un mes al siguiente; el p95 del cambio absoluto mensual es ~18–20 puntos.

### 3.6 El ERP se autoexcluyó por una duda que el dato responde

El motor deshabilita las facturas por defecto por la "hipótesis de signo no verificada". El dato es concluyente:

| | Facturas con amount < 0 | Facturas con amount > 0 |
|---|---|---|
| Nº (tipo `invoice`) | 449.558 | 309.849 |
| Conceptos frecuentes | "FACTURA DE COMPRA", "PROVEEDOR" (4,5 %) | "CLIENTE" (3,3 %), "VENTA" |
| Retraso medio de pago sobre vencimiento | 1,0 días | 11,9 días |
| % en estado `overdue` | 17,6 % | 28,0 % |

Negativo = factura recibida (AP), positivo = factura emitida (AR). Además hay `payment_date` en 554.561 facturas pagadas, repartidas por los 24 meses, lo que permite una serie mensual de retraso de cobro (DSO real, % vencido) y de retraso de pago (DBT como pagador) totalmente point-in-time: al corte *t*, una factura está pagada si `payment_date ≤ t`, y vencida si `due_date < t` y no pagada a *t*. Es la señal que el brief llamaba "la más difícil de maquillar" y el motor no la usa nunca en la trayectoria. En modo ERP solo entra un snapshot al último mes para 466 empresas.

Nota de calidad del dato: hay `payment_date` fuera de rango (años 2006, 2062, 6913…). Hay que filtrar.

### 3.7 Pilares casi muertos

| Pilar | Situación al último corte |
|---|---|
| Deuda (D) | Vale exactamente 0,5 en el **58 %** de las empresas observadas; solo 493/1170 tienen servicio de deuda visto. Explica el 4 % de la varianza. Solo 378 empresas tienen producto de deuda; `debt_products.granted/outstanding` y `debt_schedule_config` no se usan. |
| Fragilidad (F) | Explica ~0 % de la varianza. HHI utilizable solo en **125 empresas** porque el 88,8 % de los `collection` no tienen `counterparty_id`. |
| Crecimiento (G) | Cero en el 50 % de las empresas (unilateral, `max(x,0)`). |

En la práctica es un score de un solo pilar (liquidez) más ruido.

### 3.8 Sin peer groups

Todas las transformaciones son `tanh` o Hill con escalas fijas a mano (`liquidity_scale=0.5`, `debt_scale=0.25`, `hhi_scale=0.25`…). Una constructora y una consultora se miden con la misma regla. El brief lo preveía (peer = país × cuartil de ingresos, tablas congeladas) y el mercado lo hace así (Central de Balances por CNAE, RMA por sector). Sin peer, tampoco hay forma de decir "excepcionalmente sólida" (pregunta 1 del enunciado) más que en absoluto.

### 3.9 Menores

- 97.401 transacciones excluidas por FX: una empresa GBP con cuenta EUR pierde toda esa cuenta.
- `history_ready` es `month ≥ 5` pero se exportan scores desde el mes 0 con prior 50; el front debe respetar la bandera.
- `country` está vacío en 1.056 de 1.286 empresas y con variantes ("ES", "ESPAÑA", "España"); el peer por país del brief no es viable, hay que usar tamaño.
- Los tests no se descubren con `unittest discover` desde raíz (sin `__init__.py`); hay que invocar módulos explícitamente.
- Requiere Python ≥ 3.11 (`X | None` en firmas, NUL en CSV); el `requirements.txt` no lo dice.

---

## 4. Cómo lo hace el sector (resumen de la investigación)

- **Nadie en cash management publica un score único y explicable** de la propia empresa. Embat, Agicap, Kyriba y Tesorio dan KPIs (CCC, liquidity coverage) y predicción de fecha de pago por factura. El hueco existe.
- **Los scores reales de PYME son supervisados con impago**: HighRadius (collections score 0–100, PD por tiers), Plaid LendScore (XGBoost monótono, 81 % del poder predictivo desde cash flow, 5 reason codes vía SHAP), Experian Intelliscore, Equifax, Moody's RiskCalc. Sin target, el enfoque de reglas es defendible, pero la validación debe hacerse contra eventos observables.
- **PAYDEX (D&B)** es exactamente "conducta de pago ponderada por importe": lo que las facturas permiten y el motor no explota.
- **Validación sin target** estándar: estabilidad (PSI < 0,10), monotonicidad por deciles, correlación con eventos futuros observables (descubiertos, saldos negativos). El motor solo cubre la primera, y parcialmente.
- **Peer groups**: SIC/NAICS o CNAE + tamaño; RMA Annual Statement Studies; Central de Balances del Banco de España.
- **Trayectoria**: EWMA, pendiente OLS, CUSUM, Bayesian changepoint. No se encontró aplicación documentada a cash flow de PYME: hueco.
- **Nadie documenta deltas mes a mes por factor.** El waterfall temporal es un diferenciador real del proyecto.

Fuentes: Plaid LendScore (plaid.com/blog/how-we-built-lendscore), HighRadius credit risk scoring, D&B PAYDEX factsheet, FinRegLab cash-flow underwriting, CFPB cash-flow data, Central de Balances BdE, GMT Research percentile scoring, Adams & MacKay BOCPD (arXiv 0710.3742).

---

## 5. Recomendaciones priorizadas

| # | Acción | Efecto esperado | Esfuerzo |
|---|---|---|---|
| 1 | Clasificar `-` por signo como cobro/pago genérico (y `transfer` por signo o excluir con marca) | Elimina el sesgo de §3.2, recupera un tercio del volumen | ~1 h |
| 2 | Activar AP/AR por signo y construir series mensuales point-in-time: DSO real, % vencido AR, DBT como pagador (`payment_date ≤ t`) | Convierte el pilar C en una señal real; da trayectoria al ERP | ~3 h |
| 3 | Nivel con ventana de 12 meses (mín. 6) y percentiles por peer (cuartil de ingresos, tablas congeladas con train) | Estabilidad de 0,75 → ~0,9; comparabilidad entre sectores | ~3 h |
| 4 | Momentum = pendiente OLS a 6 meses del nivel, mediana de las 3 últimas, con persistencia. Medir ρ parcial con margen futuro antes del pitch; si sigue negativa, peso ≤ 2 o quitar | Momentum que no reste | ~2 h |
| 5 | Validación externa con `balances.csv` como *evaluación*, no input: AUC vs saldo negativo, ρ vs runway terminal, y contra % vencido AR | Un "si acierta" medible ante el jurado | ~1 h |
| 6 | Usar `debt_products.outstanding` y `granted` para utilización de líneas y deuda/ingresos; rescatar el pilar D | Pilar D con varianza | ~2 h |
| 7 | Quitar del resumen ejecutivo del whitepaper los "8 meses de anticipación" o etiquetarlos como control sintético | Credibilidad ante el especialista de Embat | 10 min |

Orden sugerido si el tiempo aprieta: 1 → 2 → 5 → 3 → 4.

---

## 6. Reproducibilidad de esta revisión

- Tests: `python -m unittest algorythm.test_score_engine algorythm.test_score_data algorythm.test_score_outputs` (30 OK, Python 3.12.14, numpy 2.x).
- Análisis sobre `algorythm/engine_results/score_panels.npz` y los CSV de `dataset/`. Estabilidad y correlaciones con `scipy.stats.spearmanr`; AUC con `mannwhitneyu`; correlación parcial por residuo de regresión de rangos.
- Caja terminal: suma de `balances.csv` para productos `checking` y `saving`; salidas mensuales = media de `expenses + debt_service` de los últimos 3 meses del panel bancario del propio motor.
