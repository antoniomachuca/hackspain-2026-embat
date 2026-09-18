# Investigación previa — Reto X Ray (Embat · HackSpain 2026)

Fecha: 18 sep 2026. Cuatro agentes de búsqueda web en paralelo: mercado, algoritmos, alerta temprana, fracasos y trampas.

---

## 1. ¿Se ha intentado antes?

No hay evidencia pública de este reto concreto ni de un datathon equivalente ligado a Embat o a ediciones previas de HackSpain. Es ausencia de evidencia, no prueba de ausencia.

Cosas parecidas pero distintas:
- `arunbhatg/finhealth-card` (GitHub): PoC de score 300–900 para MSME con datos alternativos.
- Hackathon de 48h patrocinado por NAB (banco australiano) con APIs de transacciones reales de pymes.

Ninguno usa datos sintéticos ni plantea el score bidireccional.

## 2. Embat: el hueco de producto es el reto

- Fintech de tesorería, Madrid, fundada 2021 (Antonio Berga, Carlos Serrano). +400 clientes corporativos.
- Series B de 30 M€ en 2026 liderada por Cathay Innovation; ~50 M€ levantados en total.
  https://www.finsmes.com/2026/05/embat-raises-eur30m-in-series-b-funding.html
- Ya tiene IA: previsión de caja adaptativa, predicción de fecha de pago de facturas, asistente TellMe (>90% de asientos automatizados).
  https://www.embat.io/en/blog/ai-in-treasury-cash-forecasting-and-payment-predictions-
- **No se le encuentra un score de salud financiera consolidado.** Hace forecasting, no riesgo. (Inferencia sobre fuentes públicas, no declaración de Embat.)

Consecuencia para el pitch: el comprador no hay que inventarlo. Es un módulo que le falta a su catálogo y cuyos datos ya tiene.

## 3. Competencia

| Empresa | Qué hace |
|---|---|
| Codat | API de datos de pymes (contabilidad + banca) para underwriting de bancos y fintechs |
| Validis (+ AccountScore) | Financial spreading para prestamistas, combinado con open banking |
| Wiserfunding | Monitorización de riesgo de pyme con datos financieros, no financieros y macro |
| Nova Credit (Cash Atlas) | Cash-flow underwriting sobre transacciones bancarias |
| Credolab | Score de comportamiento con metadata de dispositivo |
| FICO Marketplace | Scoring de "financial wellness" de pymes vendido a entidades financieras |

Seguro de crédito (comprador alternativo): Allianz Trade toma 20.000 decisiones diarias con IA; Coface expone API sobre 188 M de empresas. Prima típica: 1,00–1,50 $ por cada 1.000 $ asegurados.

## 4. Algoritmos: qué gana de verdad

### Clásicos
- **Altman Z''**: variante para empresas privadas, sin precio de mercado. Sirve como *feature*, no como modelo.
- **Merton / distance-to-default**: necesita cotización bursátil → **inservible** para pymes privadas.
- **Ohlson O-score**: logística, superado por modelos hazard posteriores.
- **Scorecard WoE + regresión logística**: sigue siendo el estándar regulatorio (Basel IRB) por auditabilidad. IV > 0.5 es sospechoso de leakage.

### Lo que ganó competiciones
- **AMEX Default Prediction (Kaggle 2022)**: ensembles LightGBM/XGBoost/CatBoost. 1.º = agregaciones (mean/std/last) + extracción de features de serie + ensemble LightGBM+GRU. Métrica: 0.5×Gini + 0.5×recall al top-4%.
  https://www.kaggle.com/competitions/amex-default-prediction
- **Home Credit Default Risk (2018)**: el ganador declaró que **el feature engineering superó al tuning y al stacking**. Ratios cruzados, medias móviles ponderadas, poda de 10.000 → 2.000 features.
- **Home Credit Credit Risk Model Stability (2024)** — el precedente más parecido a este reto: la métrica *gini stability* penaliza que el poder predictivo se degrade o sea volátil en el tiempo, no solo que sea alto de media. 18.000+ participantes.
  https://www.kaggle.com/competitions/home-credit-credit-risk-model-stability

### GBDT vs deep learning
Estudio sobre 300 datasets: CatBoost domina en tabular. TabR (2023) acorta la distancia pero no la cierra. Con 250 empresas, LSTM/Transformer es riesgo de sobreajuste sin retorno.

### Trayectoria: cómo se captura sin modelos secuenciales
Nivel + **pendiente de regresión lineal en ventanas de 3/6/12 meses** + rolling std (volatilidad) + deltas MoM/QoQ + **z-score de cada empresa contra su propio histórico** (crítico: 250 empresas de escalas muy distintas).

### Bache vs. caída estructural
Change-point detection sobre saldo de caja o flujo neto: `ruptures` (PELT) o BOCPD. Features derivadas:
- meses desde el último changepoint
- magnitud del salto
- **si el nuevo nivel se sostiene ≥N meses** → sostenido = estructural; revertido = bache

Eso alimenta al GBDT, no lo sustituye. Es la respuesta directa a la cuarta pregunta del reto.

## 5. Anticipación: cómo medirla sin que te la tumben

- **Lead time por caso**, con mediana y rango. No un único ejemplo bonito.
- **Curva retraso de detección vs. tasa de falsas alarmas** (ROC temporal), con 2-3 umbrales. Es el trade-off fundamental de CUSUM y de cualquier detector.
- Contra **baseline tonto**: alertar solo al ver el impago → anticipación = 0.
- **No prometer PSI ni Gini-en-el-tiempo** con un dataset de este tamaño: con pocos casos no son creíbles.

### Definición defendible de "deterioro significativo"
IFRS 9 / SICR ya la tiene estandarizada y se puede citar: 30 días de mora (backstop obligatorio), bajada de ≥2 escalones de rating interno, entrada en watchlist, incumplimiento de covenant sin waiver, reducción del límite por el banco, o PD a 12 meses que se triplica.
https://www.eba.europa.eu/sites/default/files/document_library/Publications/Guidelines/2020/Guidelines%20on%20loan%20origination%20and%20monitoring/884283/EBA%20GL%202020%2006%20Final%20Report%20on%20GL%20on%20loan%20origination%20and%20monitoring.pdf

Referencia comercial: Moody's EDF-X declara detectar deterioro hasta 12 meses antes.

### Señales confirmadas de deterioro
DSO alargándose, retrasos crecientes a proveedores, caída del colchón de caja en días, subida de uso de líneas y excedidos, reducción de límites por el banco, devoluciones de recibos, concentración creciente de ingresos.

### Señales de mejora — el hueco
La literatura de EWS está volcada casi por completo en el deterioro. **No se encontró trabajo dedicado a detectar recuperación.** Como el reto pide señal bidireccional explícitamente, esto es una contribución diferencial real.

Por simetría (inferencia, no fuente): reducción del DSO, desapalancamiento, crecimiento financiado con pasivo estable en vez de deuda cara, salida de watchlist, abandono del factoring/confirming.

Además: **ningún paper indexado reporta "N meses de anticipación"** con datos transaccionales; todos reportan AUC. La métrica bonus del reto es la que nadie publica.

## 6. Trampas técnicas

1. **Leakage temporal**: split aleatorio deja al modelo entrenar con t+k para predecir t. Usar validación cronológica (entrenar meses 1–18, validar 19–24).
2. **Leakage por grupo**: son 1.286 empresas en **250 grupos empresariales**. Las filiales del mismo grupo comparten patrones. Si un grupo cae partido entre train y validación, el modelo memoriza el grupo. **El split debe ser por `group_id`, no por `company_id`.** Esta es la trampa más probable del dataset.
3. **Artefactos del generador sintético**: los modelos aprenden correlaciones que no existen en datos reales. Detección: comparar importancia de features contra intuición de dominio, buscar separabilidad perfecta o casi perfecta que no tendría sentido, probar por subgrupos.
   https://arxiv.org/pdf/2509.00092
4. **IV > 0.5** en una variable = sospecha de leakage, no de buena señal.

## 7. Visiones contrarias

- **FinRegLab** (neutral): los cash-flow scores son al menos tan predictivos como los tradicionales.
- **Slope** (prestamista, parte interesada pero técnico): "el underwriting comercial por cash flow sigue sin resolverse". Las pymes mezclan ingresos personales y comerciales, tienen varias cuentas, y la diversidad sectorial es enorme (un restaurante no es una empresa de tejados). Errores de categorización temprana se propagan y explotan en ratios tipo DSCR.
  https://slopepay.com/blog/state-of-business-cashflow-lending
- Implicación: la fragilidad real está en la ingeniería de features sobre datos sucios — precisamente lo que un dataset sintético limpio **oculta**. Cuidado con extrapolar el resultado del leaderboard a una promesa de producto.
- **Fracasos**: Kabbage quebró en 2022 (Chapter 11 como K Servicing) tras señalamiento del Congreso por fraude en PPP; Amex compró la tecnología en 2020 **excluyendo la cartera de préstamos**. OnDeck vendida por ~122 M$, muy por debajo de su IPO. Upstart perdió >90% de capitalización hasta 2022. Fueron fracasos de negocio y fraude más que de modelo, pero el relato de "el ML supera a la banca tradicional" no quedó respaldado.
- **Sesgo**: ZestFinance lanzó ZAML Fair (2019) para corregir sesgo *después* de detectarlo en producción. La única cifra de mejora la da el propio fundador, sin auditoría externa.

## 8. Regulación (relevante si el pitch habla de producción)

- El AI Act clasifica el scoring de crédito como **alto riesgo** (Anexo III), incluido el lending a pymes.
- Tras la sentencia **SCHUFA** (2023), los derechos del art. 22 GDPR (revisión humana, explicación) aplican **en la fase de scoring**, no solo en la decisión final.
- Hay una fuente que afirma que SHAP post-hoc sobre caja negra no basta para CFPB / AI Act art. 26 en decisiones primarias de crédito. Fuente única, tratar con cautela — pero justifica mantener un scorecard WoE/LR interpretable en paralelo.

## 9. Receta accionable en 48h

1. **Modelo**: LightGBM o CatBoost por empresa-mes. Nada de LSTM/Transformer con N=250.
2. **Features**: nivel + slope 3/6/12m + rolling std + deltas + ratios tipo Altman Z'' + z-score intra-empresa + features de changepoint.
3. **Validación**: split temporal **y** por grupo empresarial. Las dos cosas a la vez.
4. **Explicabilidad**: SHAP para reason codes por empresa-mes + logística WoE como baseline auditable y respaldo narrativo. (Un estudio da mejor AUC a GBDT+SHAP (0.791) pero reason codes más estables a un EBM/GA2M.)
5. **Anticipación**: lead time por caso + curva retraso/falsas alarmas + baseline tonto.
6. **Diferenciador**: la detección de mejora, porque la literatura no la cubre.
