# X Ray — Guía del reto de Embat

HackSpain 2026 · 18–20 sep · ETSIT UPM · Equipo de 5

Todo lo recopilado sobre el reto: qué piden, cómo se construye, para quién es y cómo presentarlo.
Detalle ampliado en [investigacion.md](investigacion.md) (técnica) y [producto.md](producto.md) (diseño y demo).

---

## 1. El reto

Con el rastro financiero de 250 empresas durante 24 meses, construir un **score de salud financiera** y, encima del score, **un producto vendible**. El score es el motor; el producto es la entrega.

Seis preguntas que el sistema debe contestar, empresa por empresa y mes a mes:

1. Quién está sano — no solo quién está en problemas
2. Quién está mejorando
3. Quién empieza a torcerse
4. Bache puntual o caída estructural
5. Por qué ha cambiado el número
6. Cuántos meses antes se vio venir

**Obligatorio:** predicción sobre el test oculto (60–80 empresas, va al leaderboard), señal en las dos direcciones, trayectoria y no foto fija, explicación, producto encima del score, comprador identificado, demo navegable.
**Bonus:** anticipación medida y un monitor que avise solo.

> Un notebook que solo corre en vuestro portátil no cuenta como demo.

## 2. Cómo se reparte la nota

Tres bloques y **ninguno pesa más que otro**. El algoritmo es como mucho un tercio.

| Bloque | Qué se mira |
|---|---|
| Si acierta | Generalización al test oculto, trayectoria, las dos direcciones |
| Si llega a tiempo | Anticipación cuantificada, estabilidad, monitor automático |
| Si vale algo | Producto real, comprador claro, explicación, artesanía y demo |

Frase textual del reto: *un modelo sencillo con un producto claro encima nos interesa más que uno sofisticado que se queda en el número*.

**Si el domingo hay que elegir entre subir la precisión o que la demo se abra sin fallos, se elige la demo.**

---

## 3. El dataset

1.286 empresas sintéticas en **250 grupos empresariales**, 24 meses cada una (sep 2024 – sep 2026), nueve CSV. Clave de cruce: `company_id`.

| Fichero | Qué lleva |
|---|---|
| `groups.csv` | Un grupo por fila; de 1 a 24 empresas, mediana 2 |
| `companies.csv` | Grupo, país, moneda, ERP, fecha de alta |
| `banking_products.csv` | Cuentas: corriente, tarjeta, TPV, ahorro, inversión |
| `debt_products.csv` | Préstamos, leasing, líneas, factoring, confirming, avales |
| `debt_schedule_config.csv` | Cuota, frecuencia, plazos, tipo de interés |
| `transactions.csv` | Movimientos bancarios de los 24 meses |
| `invoices.csv` | Facturas emitidas y recibidas, con cobro y pago |
| `balances.csv` | Saldo de cada cuenta a 1 sep 2026 |
| `data_dictionary.md` | Todos los campos explicados |

**Lo primero que hay que mirar:** cuál es exactamente la variable a predecir. El leaderboard puntúa contra "el resultado" de las empresas ocultas, pero en la lista de ficheros no aparece ninguna columna de score. Está en el diccionario de datos.

### Las tres trampas

1. **Fuga por grupo empresarial.** Las filiales de un grupo comparten patrones. Si un grupo cae partido entre entrenamiento y validación, el modelo memoriza el grupo y la validación miente. **El split debe ser por grupo, no por empresa.** Es la trampa más probable de este dataset.
2. **Leakage temporal.** Un split aleatorio deja entrenar con datos posteriores al mes que se predice. Validación cronológica: entrenar meses 1–18, validar 19–24.
3. **Artefactos del generador sintético.** Los modelos aprenden correlaciones inexistentes en datos reales. Se detectan comparando importancia de variables contra intuición de dominio y buscando separabilidad sospechosamente perfecta. Una variable con **IV > 0,5 es sospecha de fuga**, no una joya.

---

## 4. El score

### Señales (una fila por empresa y mes)

- **Días de caja** — cuántos días aguanta pagando sin cobrar nada. La señal reina en pymes.
- **DSO** y **DPO** — días en cobrar y en pagar. Si suben los dos a la vez, está tapando un agujero.
- **% de facturas emitidas que se pagan tarde** — anticipa que sus clientes están mal.
- **Utilización de la línea de crédito** — del 30% al 78% es alarma clásica.
- **Concentración de clientes** — % de ingresos del cliente mayor.
- **Volatilidad de ingresos** y ruptura de estacionalidad.
- **Coste de la deuda** y uso creciente de factoring/confirming.
- Ratios tipo **Altman Z''** (la variante para empresas privadas) como features, no como modelo.

### Trayectoria

Para cada señal, no solo el valor del mes:

- media 3m vs. media 12m anteriores
- **pendiente de regresión lineal** en ventanas de 3/6/12 meses
- desviación típica móvil (volatilidad)
- deltas mes a mes y trimestre a trimestre
- **z-score de cada empresa contra su propio histórico** — crítico: comparar cada empresa consigo misma, no solo con las demás

### Bache o caída estructural

Change-point detection (`ruptures`/PELT o BOCPD) sobre saldo de caja o flujo neto. De ahí tres features:
meses desde el último cambio · magnitud del salto · **si el nuevo nivel se sostiene ≥N meses**.
Sostenido = estructural. Revertido = bache.

### Modelo

**LightGBM o CatBoost** por empresa-mes. Nada de LSTM ni Transformer: con 250 empresas es sobreajuste caro.

Evidencia: en el *AMEX Default Prediction* (Kaggle 2022) ganaron ensembles de GBDT; el ganador del *Home Credit* 2018 declaró que **el feature engineering superó al tuning y al stacking**; un estudio sobre 300 datasets da CatBoost como dominante en datos tabulares.

Descartado: **Merton / distance-to-default** necesita cotización bursátil, y son empresas privadas.

### Validación

Split **temporal y por grupo, las dos cosas a la vez**.

Precedente directo: *Home Credit Credit Risk Model Stability* (Kaggle 2024), cuya métrica penalizaba explícitamente que el poder predictivo se degradara o fuera volátil en el tiempo. Es el mismo problema que plantea el test oculto.

### Explicabilidad

SHAP sobre el GBDT para reason codes por empresa-mes, más una regresión logística con WoE como baseline auditable. Un estudio da mejor AUC a GBDT+SHAP (0,791) pero reason codes más estables a un EBM/GA2M.

---

## 5. Anticipación

### Cómo medirla sin que la tumben

- **Lead time por caso**, con mediana y rango. No un único ejemplo bonito.
- **Curva retraso de detección vs. tasa de falsas alarmas** (ROC temporal), con 2-3 umbrales.
- Contra un **baseline tonto**: alertar solo al ver el impago → anticipación = 0.
- **No prometer PSI ni Gini-en-el-tiempo**: con este tamaño de muestra no son creíbles.

### Definición defendible de deterioro (IFRS 9 / SICR)

30 días de mora (backstop obligatorio) · bajada de ≥2 escalones de rating interno · entrada en watchlist · incumplimiento de covenant sin waiver · reducción del límite por el banco · PD a 12 meses que se triplica.

Referencia comercial: Moody's EDF-X declara detectar deterioro **hasta 12 meses antes**.

### Los dos huecos que podéis reclamar

- **La literatura de alerta temprana casi no trata la mejora.** Todo es deterioro. El reto pide bidireccionalidad.
- **Ningún paper indexado reporta "N meses de anticipación"** con datos transaccionales; todos reportan AUC.

---

## 6. Quién compra

**Embat NO vende a bancos.** Sus testimonios públicos son de *Finance Director* en R2 Hotels, *Corporate Finance Director* en Molins y *Finance Director* en CPS Group; sus logos, Wallapop, Fever y Treatwell. Los bancos están en su *Connectivity Hub* (API, EBICS, SWIFT, 15.000+ instituciones): son la fontanería por donde entran los datos, no el cliente.

Eso descarta el marketplace de crédito y el seguro de prima dinámica: exigirían a Embat entrar en un mercado nuevo.

### Las visiones que quedan

| # | Producto | Quién paga | Pega |
|---|---|---|---|
| 1 | Radar de cartera — Embat vigila a sus clientes | Embat | Herramienta interna; ahorra, no ingresa |
| 2 | Módulo premium "Salud financiera" | La empresa, vía Embat | ¿Pagan por saber cómo están? El valor está en el "qué hacer" |
| 3 | **Vigilancia de clientes** | La empresa | Sin validar disposición a pagar |
| 4 | Agente de recomendaciones | La empresa | Fácil de enseñar, fácil de que suene a humo |

**Recomendación: 2 + 3 como un solo producto.** Un módulo dentro de Embat donde el director financiero ve dos cosas a la vez: cómo está su empresa, y cómo están los que le deben dinero.

Por qué:
- El comprador es Embat, que es lo que el propio reto señala.
- Usa las dos direcciones: la mejora es argumento para negociar; el deterioro del cliente es la alarma.
- **Ninguna reseña de Kyriba, Trovata, Agicap ni Embat menciona el riesgo de crédito de clientes.** Nadie lo hace.
- Se demuestra en una pantalla: una empresa, su score, su trayectoria, y debajo sus clientes con el que se tuerce marcado.

**Pendiente de validar:** que una empresa pague por vigilar a sus clientes. Preguntárselo a los ingenieros de Embat que estarán en el aula.

### Quién es el usuario

No es el autónomo con Excel. Es un **director financiero de empresa mediana**, con grupos de hasta 24 filiales. Eso significa **densidad alta** de información (patrón Ramp/Brex, no Mercury): tablas con muchas filas, cifras alineadas, varios KPIs a la vez.

Y encaja con lo que Embat presume: consolidar posiciones *across every entity, bank and currency*. Si el producto trata bien el caso multi-entidad — score del grupo y de cada filial — habláis su idioma.

### Huecos de la competencia (reseñas reales)

- **Kyriba**: *"difícil de implementar y muy difícil de personalizar"*, *"el diseño interno es rígido y confuso"*, *"no enlaza las transacciones de caja con los asientos contables"*.
- **Trovata**: *"el módulo de previsión todavía necesita trabajo"*.
- **Agicap** (4,4/5, 322 reseñas): elogian facilidad de uso; critican funcionalidades ausentes.
- **Embat** (4,3/5, 7 reseñas): su nota más baja es **soporte, 3,5**.

El dolor no es la falta de analítica: es la fiabilidad de la integración y la rigidez.

---

## 7. Diseño

### El sistema de Embat (extraído de su CSS)

**Tipografía: Haffer SQXH**, solo dos pesos (400 y 500). No usan Inter.
Alternativas gratuitas con el mismo aire: **General Sans** o **Switzer** (Fontshare).

| Token | Hex |
|---|---|
| Texto principal | `#050b2c` |
| Texto secundario | `#6e707c` |
| Fondo / superficie / sutil | `#ffffff` / `#f3f4f6` / `#fbfbfc` |
| Bordes | `#e8e8ed` / `#d2d2db` |
| Fondo oscuro | `#050b2c` → `#232845` → `#41465f` |
| Acento aguamarina | `#c5f8fc` · `#5ed3e5` · `#007b93` |

Marino profundo + aguamarina + blancos, dos pesos tipográficos.

### Patrones de dashboard

Sidebar de 240–280 px · tira de 4–6 tarjetas KPI · una métrica héroe grande arriba · variación con flecha + porcentaje junto a un sparkline · estados como etiqueta de texto, no solo color · **tabular figures** para que las cifras se alineen.

### Color

El rojo/verde puro falla para el **~8% de los hombres**. Usar gradiente continuo sobre un solo eje de color (ámbar → aguamarina) y **nunca codificar significado solo con color**: añadir flecha, signo o texto. Un único color de acento reservado a la acción primaria.

### Cómo se enseña un score en productos reales

Moody's EDF-X, D&B y Creditsafe hacen lo mismo: **número grande + banda de color + línea temporal de evolución**. Nunca un gauge solo. EDF-X además compara el histórico de la empresa contra un grupo de comparables en el mismo gráfico.

Explicaciones: lista de 3-5 factores con signo y barra de peso + waterfall simplificado + frase generada ("el score bajó 8 puntos por deterioro en días de cobro"). No SHAP crudo.

Alertas: empresa + severidad + **disparador concreto** ("caída de 12 puntos en 30 días") + fecha + acción sugerida, ordenadas por severidad × recencia. Más de 10 alertas al día y se ignoran todas; en tesorería el ritmo es semanal, no diario.

---

## 8. Construcción

**Next.js + shadcn/ui + Tremor en Vercel.** Mejor ratio "pinta de producto" / tiempo, y sale código React propio.

- **Tremor** para KPIs, gauges y tarjetas: preestilizado, combina con shadcn de fábrica, usa Recharts por debajo.
- **Streamlit** solo como red de seguridad si nadie toca React: su estética por defecto se lee como "notebook con botones".
- **Gradio** encaja mal con un dashboard multi-panel. **Retool** se percibe como herramienta interna.

**Datos de ejemplo:** Faker con locale `es_ES`. *"Suministros Hidráulicos del Ebro S.L."*, nunca *"Empresa 1"*. Que **todos** los estados tengan contenido, incluido uno de "datos insuficientes" — demuestra robustez y casi nadie lo hace.

---

## 9. La demo y el pitch

### Reparto de los 5 minutos

**1 min problema · 3 min demo en vivo · 1 min a quién se vende.**

El error más citado por jueces de Devpost: dedicar el 5% del tiempo al problema y el 95% a la solución, y luego puntuar bajo en impacto. La proporción recomendada es 30/70.

### Reglas de seguridad

- **Congelar el código 4 horas antes** de entregar.
- Ensayar el camino feliz **cinco veces**, buscando dónde se rompe.
- Datos precargados, sin depender de conexiones en vivo.
- Vídeo de respaldo grabado dos veces; capturas como último recurso.

> Los jueces puntúan lo que ven en pantalla, no lo que casi ocurrió por detrás.

### Storytelling

Una empresa ficticia **con nombre** recorriendo el flujo entero gana a un agregado de "10.000 empresas analizadas".

### Detalles que hacen que parezca producto

Dominio propio (que no se vea `localhost`), cero placeholders, estados vacíos cuidados, hover states, espaciado consistente, y al menos un error manejado ("empresa sin datos suficientes → scoring pendiente"). Los jueces usan *polish* como categoría explícita.

### Qué busca un sponsor

No evalúan como un VC. Usan su track para reclutar (**el 40% de las empresas usa hackathons como proceso de contratación**), validar roadmap y marca.

---

## 10. Munición para el pitch

| Dato | Fuente |
|---|---|
| **El 71% de los responsables financieros rechazaría un sistema de IA que no pueda explicar sus resultados**, por preciso que sea | [ERP Today](https://erp.today/finance-ai-trust-gap-critical-as-explainability-becomes-non-negotiable/) |
| Los equipos financieros pierden **12,9 h/semana** validando salidas de IA — el 26% del tiempo que ahorran | ERP Today |
| *"Si no puedes explicar un número, no puedes defenderlo, compartirlo ni confiar en él"* | [Planful](https://planful.com/blog/explainable-ai-in-finance/) |
| Control de caja es prioridad para el **43%** de CFOs; el **51%** se centra en precisión de la previsión | [Deloitte CFO Survey 2026](https://www.deloitte.com/uk/en/about/press-room/uk-finance-leaders-confidence-drops-as-geopolitical-risk-dominat-april-2026.html) |
| Moody's EDF-X detecta deterioro **hasta 12 meses antes** | [Moody's](https://dkf1ato8y5dsg.cloudfront.net/uploads/52/504/edfx-early-warning-system.pdf) |
| Creditsafe predice **hasta el 70% de las insolvencias con 12 meses de antelación** | [Ramp](https://ramp.com/blog/check-business-credit-scores) |
| Embat: **30 M€ Serie B en 2026**, ~50 M€ levantados, +400 clientes | [FinSMEs](https://www.finsmes.com/2026/05/embat-raises-eur30m-in-series-b-funding.html) |
| Allianz Trade: 20.000 decisiones de crédito al día. Prima típica: 1,00–1,50 $ por cada 1.000 $ asegurados | [Impello](https://www.impelloglobal.com/trade-credit-insurance-carriers-compared) |
| El **40%** de las empresas usa hackathons como proceso de contratación | [HackerEarth](https://www.hackerearth.com/blog/talent-assessment/hackathon-hiring-process/) |

### La frase de apertura

> El 71% de los responsables financieros rechazaría una IA que no se explica, por precisa que sea. Por eso no hemos construido un score. Hemos construido el porqué.
