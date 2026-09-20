# Guía de Defensa ante el Jurado · 20 Preguntas y Respuestas Verificadas
> **HackSpain 2026 · Track Embat (X-Ray)**  
> *18–20 de septiembre de 2026 · ETSIT UPM, Madrid*  
> Documento de preparación técnica y de negocio basado **estrictamente en el código fuente, la base de datos y la arquitectura real del repositorio**. Sin suposiciones ni datos inventados.

---

## Índice de Bloques

1. [Bloque I: Algoritmia de Scoring y Calidad del Dato (Preguntas 1 a 5)](#bloque-i-algoritmia-de-scoring-y-calidad-del-dato)
2. [Bloque II: Las 6 Preguntas del Enunciado y Dinámica Temporal (Preguntas 6 a 9)](#bloque-ii-las-6-preguntas-del-enunciado-y-dinámica-temporal)
3. [Bloque III: Explicabilidad, Consolidación de Grupo y Redes (Preguntas 10 a 13)](#bloque-iii-explicabilidad-consolidación-de-grupo-y-redes)
4. [Bloque IV: Producto, Modelo de Negocio y Simulación What-If (Preguntas 14 a 17)](#bloque-iv-producto-modelo-de-negocio-y-simulación-what-if)
5. [Bloque V: Laboratorio de Forecasting y Resiliencia Técnica (Preguntas 18 a 20)](#bloque-v-laboratorio-de-forecasting-y-resiliencia-técnica)

---

## Bloque I: Algoritmia de Scoring y Calidad del Dato

### 1. ¿Qué modelo de Machine Learning habéis entrenado para calcular el score base?
* **Intención del jurado:** Evaluar si habéis entendido la naturaleza del problema o si habéis forzado un modelo supervisado (GBDT, Random Forest) sobre un dataset sin etiquetas.
* **Respuesta exacta:**
  > "El score base **no es un modelo de Machine Learning supervisado**. El dataset no contiene ninguna etiqueta (*ground truth*) ni variable objetivo de impago o quiebra en los 24 meses; forzar un clasificador sin etiqueta habría sido inventar un target ficticio.  
  > Por ello, implementamos un **motor analítico continuo determinista** (`algorythm/score_engine.py`) basado en transformaciones continuas ($\tanh$ y saturaciones de Hill) calibradas sobre la física del circulante:
  > $$\text{Base} = 100 \cdot (0.50 \cdot L + 0.30 \cdot C + 0.20 \cdot D)$$
  > Donde $L$ es Liquidez, $C$ es Cobros y Eficiencia, y $D$ es Servicio de Deuda, modulado por tres factores dinámicos: **Momentum ($\pm 8$ pts), Crecimiento de Calidad ($+6$ pts) y Fragilidad ($-8$ pts)**.  
  > El Machine Learning (Huber, Ridge con GroupKFold y medianas lineales) lo reservamos exclusivamente para el módulo de **previsión de score a 1, 3 y 6 meses** (`forecasting/`), donde sí existe una serie temporal histórica medible para evaluar error absoluto (MAE)."

---

### 2. En el dataset había 9 ficheros, incluidos `invoices.csv` (ERP) y `balances.csv` (saldos). ¿Los habéis usado en el cálculo oficial del score mensual?
* **Intención del jurado:** Detectar si habéis cometido *lookahead bias* (sesgo de anticipación) o falseado datos longitudinales incompletos.
* **Respuesta exacta:**
  > "En la baseline oficial del motor (`algorythm/engine_results/score_manifest.json`), **ERP está desactivado y `cash_known=0`**.  
  > El motivo es metodológico: `balances.csv` es una **foto estática al 1 de septiembre de 2026** (mes 24); no existía un saldo de balance para cada uno de los meses anteriores. Utilizar el saldo del final para evaluar meses pasados habría introducido sesgo de anticipación.  
  > Por su parte, la sincronización de ERP en `invoices.csv` era parcial entre filiales. Decidimos basar el núcleo oficial en el rastro bancario directo (`transactions.csv`), que es **100% homogéneo, observable mes a mes y sin sesgos**, computando ingresos operativos, gastos y servicio de deuda exclusivamente a partir de las salidas reales de caja (`debt_repayment` + `interest_charge`). El ERP queda conectado en el backend como capa operativa opcional para el cálculo de ratios DSO/DPO en la ficha."

---

### 3. ¿Por qué en el pilar de deuda ($D$) sólo miráis el servicio de la deuda mensual y no el total de deuda viva de `debt_products.csv`?
* **Intención del jurado:** Poner a prueba vuestro conocimiento financiero sobre balances vs. flujos de caja.
* **Respuesta exacta:**
  > "En el análisis de solvencia dinámico mensual, lo que ahoga y precipita la insolvencia de una pyme no es el pasivo total concedido en balance, sino la **exigibilidad de la cuota mensual de amortización e intereses frente al flujo de ingresos operativos** ($r_{\text{deuda}} = \frac{H_3}{R_3 + H_3}$).  
  > Además, `debt_products.csv` representa una foto estática y límites concedidos, mientras que `transactions.csv` refleja el pago real de cuotas ejecutadas en caja. Extraer el servicio de deuda directamente de los movimientos bancarios garantiza que medimos salidas reales de tesorería sin distorsiones ni supuestos contables."

---

### 4. En el score bonificáis el crecimiento con hasta +6 puntos ($G$). ¿Qué pasa si una empresa crece mucho en ventas pero quema toda su caja y no cobra las facturas?
* **Intención del jurado:** Comprobar si premiáis crecimientos desordenados que acaban en quiebras de circulante.
* **Respuesta exacta:**
  > "Nuestra formulación matemática penaliza explícitamente el crecimiento descontrolado (`algorythm/score_engine.py`):
  > $$G = \tanh\left(\frac{\max(\Delta R, 0)}{0.20}\right) \cdot \left(0.5 \cdot (L_{\text{bank}} + C_{\text{bank}})\right) \cdot q_3$$
  > $G$ no premia el crecimiento bruto de ingresos de forma aislada. Si el incremento de ventas no viene acompañado de liquidez operativa ($L_{\text{bank}}$ alto) y disciplina de cobro ($C_{\text{bank}}$ alto), el multiplicador colapsa hacia cero y la bonificación se anula.  
  > Es más: el tensionamiento de liquidez resultante activa el factor de **Fragilidad Financiera ($F$)**, que resta hasta $-8$ puntos netos sobre el score."

---

### 5. ¿Cómo se comporta vuestro score en las 60–80 empresas del test oculto que nunca habéis visto? ¿Hay riesgo de overfitting?
* **Intención del jurado:** Evaluar el Criterio del Bloque 1 ("Generalización en empresas que no ha visto nunca").
* **Respuesta exacta:**
  > "Al no ser un modelo de Machine Learning con miles de hiperparámetros memorizados, **el riesgo de sobreajuste es prácticamente nulo**.  
  > El motor aplica transformaciones analíticas univariadas continuas calibradas sobre ratios estándar de tesorería. Dos empresas con idénticos patrones de caja en el test oculto recibirán matemáticamente el mismo score exacto sin degradación fuera de muestra.  
  > Además, incorporamos el **Índice de Confianza del Dato**, que modula el score si una empresa en el test oculto tiene menos de 6 meses de historial ($t < 6$), evitando emitir diagnósticos categóricos sin ventana de warmup suficiente."

---

## Bloque II: Las 6 Preguntas del Enunciado y Dinámica Temporal

### 6. ¿Cómo resuelve vuestro motor el caso de Northbrook Foods vs. Velasco Industrial (la paradoja de los tres puntos)?
* **Intención del jurado:** Evaluar la resolución del problema central del enunciado oficial (trayectoria, no foto fija).
* **Respuesta exacta:**
  > "En el mes 24, ambas empresas presentan notas estáticas parecidas (65 vs 68). Sin embargo, nuestro motor incorpora el componente de **Momentum ($M \in [-1, 1]$)** y el filtro de persistencia temporal:  
  > - **Northbrook Foods** asciende de 45 a 65 y se clasifica en `RECUPERACION` (o `MEJORANDO`): acumula tres meses consecutivos con momentum positivo ($M > +0.10$), lo que le otorga una bonificación de hasta $+8$ puntos sobre su base, consolidando la expansión de sus flujos netos trimestrales.  
  > - **Velasco Industrial** cae de 82 a 68 y se clasifica en `TORCIENDOSE`: a pesar de conservar un nivel aceptable ($\ge 60$), arrastra tres meses consecutivos de momentum negativo ($M < -0.10$) y tensión de circulante.  
  > En la pantalla de [Comparador (`/comparar`)](../front/app/comparar/page.tsx) se visualizan frente a frente: una foto fija no las distingue, pero nuestra curva temporal y anillo de estado evidencian que Northbrook es una oportunidad y Velasco un riesgo inminente."

---

### 7. ¿Cómo diferencia vuestro algoritmo un "Bache puntual" de un "Deterioro estructural"?
* **Intención del jurado:** Evaluar la Pregunta 4 del enunciado oficial (Criterio de estabilidad y filtro de ruido).
* **Respuesta exacta:**
  > "Mediante las reglas de transición de nuestra **máquina de 6 estados analíticos** (`algorythm/score_states.py`):  
  > - Asignamos `BACHE` cuando una empresa sufre una contracción puntual en su margen de flujo mensual ($> 0.12$), pero **sin arrastrar inercia negativa previa** ($M \ge -0.10$ en los 3 meses anteriores). Corresponde a una tensión aislada de tesorería (como un pago extraordinario o un retraso esporádico).  
  > - Asignamos `TORCIENDOSE` o `DETERIORO` únicamente cuando la degradación se confirma durante **al menos 3 meses consecutivos** en la ventana móvil y cruza las medias móviles rápida y lenta.  
  > De esta forma evitamos generar alarmas operativas por estacionalidad o picos no estructurales."

---

### 8. ¿Cómo gestionáis la estacionalidad para no confundir caídas típicas (ej. agosto o enero) con deterioro?
* **Intención del jurado:** Evaluar si el sistema penaliza injustamente a empresas con ciclos anuales marcados.
* **Respuesta exacta:**
  > "El motor exige que la dirección de cambio se confirme en la mediana de los márgenes mensuales de flujo de los últimos 6 meses, y no en un corte aislado.  
  > El clasificador evalúa la persistencia del momentum y el flag `annual_pattern_match`: si la bajada coincide con un ciclo anual y los flujos se recuperan al mes siguiente, el filtro de persistencia absorbe el impacto clasificándolo como `BACHE` o manteniéndolo en `ESTABLE`, sin transicionar a `TORCIENDOSE`."

---

### 9. ¿Cuándo se vio venir? ¿Cuántos meses antes avisa el sistema (Lead Time medido)?
* **Intención del jurado:** Evaluar la Pregunta 6 del enunciado y el Bonus de "Anticipación medida".
* **Respuesta exacta:**
  > "Hemos auditado cuantitativamente el comportamiento temporal de todo el dataset en `algorythm/engine_results/episodes_report.md`:  
  > - Evaluamos **837 episodios** en 479 empresas (373 de deterioro y 464 de mejora).  
  > - Con nuestro criterio de detección (que exige 3 meses de persistencia para garantizar cero falsas alarmas), la anticipación mediana respecto a la confirmación del cambio material definitivo ($\ge 10$ puntos de caída) se sitúa en **$-1.0$ meses** (el aviso salta exactamente al cumplirse el tercer mes de deterioro acumulado).  
  > - En un **10% a 13% de los episodios**, el aviso se anticipa entre **1 y 4 meses** al desplome material.  
  > - Para anticipación prospectiva a futuro, desacoplamos el monitor y construimos el laboratorio de **previsión predictiva a 1, 3 y 6 meses** (`forecasting/`), logrando un **MAE de 4.17 puntos a 1 mes** con el modelo Huber."

---

## Bloque III: Explicabilidad, Consolidación de Grupo y Redes

### 10. ¿Cómo explicáis el cambio en la puntuación? ¿Habéis usado valores SHAP?
* **Intención del jurado:** Evaluar la Pregunta 5 del enunciado ("Explicabilidad: nadie compra una caja negra").
* **Respuesta exacta:**
  > "No empleamos aproximaciones SHAP sobre el score base porque no tenemos una caja negra que aproximar. Nuestro score es una **descomposición aditiva exacta** (`algorythm/score_engine.py`):  
  > $$\Delta S = \Delta P_L + \Delta P_C + \Delta P_D + \Delta P_M + \Delta P_G + \Delta P_F + \Delta P_{\text{clip}}$$  
  > En la interfaz gráfica (`front/components/cascada.tsx`), esto se renderiza directamente en un **gráfico Waterfall**: cada punto ganado o perdido entre dos meses se desglosa con exactitud matemática en euros o ratios operativos (cuántos puntos se deben a contracción de liquidez, cuántos al retraso de cobro de clientes o a la carga de intereses). La suma de las barras coincide con el cambio en el score sin residuo alguno."

---

### 11. ¿Cómo calculáis el score de un grupo empresarial (holding) y el riesgo de contagio?
* **Intención del jurado:** Evaluar la consistencia en estructuras multi-entidad (clave en el negocio de Embat).
* **Respuesta exacta:**
  > "En `algorythm/build_duckdb.py` y `backend/routes/companies.py`, el score consolidado del grupo combina la media ponderada de las filiales con la situación del eslabón más vulnerable:  
  > $$S_{\text{grupo}} = 0.65 \cdot \bar{S}_{\text{filiales}} + 0.35 \cdot \min(S_{\text{filiales}})$$  
  > Si cualquier filial desciende a zona crítica ($S < 40$), el motor aplica una **penalización adicional por riesgo de contagio intragrupo**.  
  > Esto permite que en la [Ficha de Grupo (`/grupo/[id]`)](../front/app/grupo/%5Bid%5D/page.tsx) se distinga de inmediato si un holding sólido tiene una filial drenando recursos de las demás."

---

### 12. En el dataset las contrapartes están anonimizadas. ¿Cómo habéis sacado el grafo de flujos entre filiales del grupo?
* **Intención del jurado:** Comprobar si os habéis inventado conexiones entre empresas o si existe inferencia analítica verificable.
* **Respuesta exacta:**
  > "Las contrapartes en `transactions.csv` son hashes anonimizados que no cruzan directamente entre entidades ($0.0\%$ de cruce por ID).  
  > Por ello, en `backend/routes/graph.py` implementamos un **algoritmo de inferencia determinista por emparejamiento de tesorería**: detectamos transacciones donde una filial A presenta una salida de caja y una filial B del mismo holding registra una entrada exactamente el mismo día y por el mismo importe ($\ge 500$ €).  
  > Estadísticamente, este patrón ocurre **24 veces más frecuentemente dentro del mismo grupo que entre grupos no vinculados** (4,5 frente a 0,19 coincidencias por par). Un par con $\ge 2$ coincidencias tiene únicamente un **1,6% de probabilidad de ser ruido**. Con estas conexiones inferidas renderizamos el grafo interactivo D3 en la pantalla [`/grafo`](../front/app/grafo/page.tsx)."

---

### 13. ¿Disponéis de un monitor proactivo que avise solo sin esperar a que el usuario consulte la web?
* **Intención del jurado:** Evaluar el Bonus de "Monitor que avisa".
* **Respuesta exacta:**
  > "Sí, disponemos de un **monitor proactivo con doble canal** operativo:  
  > 1. **Bot de Telegram** (`algorythm/score_telegram_bot.py`): monitoriza el feed de alertas (`alerts_feed.json`) y emite notificaciones instantáneas cuando una sociedad cambia de régimen a `TORCIENDOSE` o `DETERIORO`, detallando la variación de puntos y los factores causales.  
  > 2. **Notificador de Email** (`algorythm/email_notifier.py`): genera correos con la gráfica histórica longitudinal de 24 meses incrustada (validado en local con Mailpit).  
  > El sistema no espera a que el usuario entre; avisa en el momento del cambio."

---

## Bloque IV: Producto, Modelo de Negocio y Simulación What-If

### 14. ¿Qué habéis construido encima del score y quién es el comprador concreto?
* **Intención del jurado:** Evaluar el Bloque 3 ("Si vale algo: producto y comprador identificado").
* **Respuesta exacta:**
  > "Hemos construido **X-Ray**, un módulo de Diagnóstico y Tesorería Predictiva integrado en el TMS de Embat, con dos audiencias claras sobre el mismo motor:  
  > 1. **Para Embat (vista de cartera en `/`):** Embat cuenta con más de 400 clientes mid-market (50–500 M€). Con nuestra vista de cartera segmenta en tres acciones inmediatas: **Apostar** (clientes con score alto y en crecimiento, candidatos a líneas de financiación o cross-selling), **Vigilar** (empresas que empiezan a torcerse, para retención antes de incurrir en impago o churn) y **Acompañar** (empresas en bache puntual de tesorería).  
  > 2. **Para la empresa cliente (vista en `/[id]`):** Acceso a su scorecard 360°, métricas de DSO/DPO y al **Simulador What-If**.  
  > El comprador directo es **Embat**, comercializándolo como módulo premium bajo su tesis de *workflow ownership*, y la empresa cliente que lo utiliza como dossier bancario vivo para negociar con sus bancos."

---

### 15. ¿Por qué una empresa o Embat pagarían por esto si ya existen bureaus como Informa D&B o ratings bancarios?
* **Intención del jurado:** Evaluar el encaje de mercado frente a alternativas consolidadas.
* **Respuesta exacta:**
  > "Los bureaus tradicionales (Informa D&B, Axesor, ratings bancarios) operan sobre cuentas depositadas en el Registro Mercantil. Entre el cierre del año contable (31-dic), la aprobación (30-jun) y el depósito oficial (30-jul), **sus balances arrastran un retraso de entre 8 y 15 meses**. En marzo de cualquier año, Informa te puntúa con un balance de hace 15 meses.  
  > X-Ray no sustituye al bureau tradicional: **le añade los 15 meses que le faltan**, puntuando con los movimientos bancarios de ayer por la tarde.  
  > Además, ningún bureau ofrece **simulación contrafactual**: un bureau te entrega una foto fija de tu pasado; X-Ray le dice a la empresa qué palancas mover hoy para mejorar su acceso a financiación."

---

### 16. ¿Cómo funciona el simulador What-If (`/api/simulate`)? ¿Aplica multiplicadores fijos o ejecuta el algoritmo real?
* **Intención del jurado:** Comprobar si la simulación es cosmética en frontend o una recomputación real.
* **Respuesta exacta:**
  > "Ejecuta el **algoritmo matemático completo en menos de 4 milisegundos**:  
  > Para evitar el coste de parsear los 2,55 millones de transacciones en cada petición HTTP, generamos `bank_inputs.npz` (~2,5 MB), que mantiene precargados en memoria los arrays de entrada de las 1.286 empresas.  
  > Cuando el usuario ajusta las palancas en la interfaz (`front/app/empresa/[id]/escenarios/page.tsx`) —como acelerar cobros de clientes, renegociar confirming con proveedores o inyectar liquidez—, el endpoint `POST /api/simulate` muta el corte bancario del mes 23 y vuelve a invocar `calculate_scores()`.  
  > Devuelve el score recalculado, el delta exacto de puntos y el volumen neto de euros liberados."

---

### 17. Si la empresa puede usar el Simulador What-If para 'probar' mejoras, ¿no existe el riesgo de que maquille su situación para engañar al banco?
* **Intención del jurado:** Comprobar si entendéis la diferencia entre simulación contrafactual y auditoría real.
* **Respuesta exacta:**
  > "El simulador What-If es un entorno de planificación interna, no un generador de certificados falsos. Para que el score oficial de una empresa suba en X-Ray, **la empresa tiene que ejecutar las acciones en su operativa real**: cobrar antes las facturas, ingresar los fondos en su cuenta o cancelar líneas de crédito.  
  > El pasaporte o ficha de exportación bancaria se alimenta exclusivamente del historial bancario verificado registrado en el extracto, no de los escenarios del simulador. El simulador le muestra el camino para mejorar; el banco valida la realidad de los movimientos."

---

## Bloque V: Laboratorio de Forecasting y Resiliencia Técnica

### 18. En el laboratorio de previsión de score a futuro (`forecasting/`), ¿qué modelos ganaron y con qué criterio?
* **Intención del jurado:** Evaluar el rigor metodológico en la selección de modelos predictivos.
* **Respuesta exacta:**
  > "Nos regimos por el principio de parsimonia definido en `forecasting/METHODOLOGY.md`: *'Dentro del 2% del mejor MAE por grupo, gana la menor complejidad declarada'*.  
  > Según nuestro leaderboard oficial (`forecasting/benchmarks/LEADERBOARD.md`):  
  > - **A 1 mes:** Seleccionamos `huber_linear` con **MAE de validación de 4.17 puntos**, superando al baseline de boosting en $+0.38$ puntos con un intervalo de confianza al 95% positivo ($[+0.10, +0.74]$).  
  > - **A 3 meses:** Seleccionamos `trailing_mean` (**MAE 7.20 puntos**), ya que modelos más complejos no superaron de forma estadísticamente significativa a la media móvil reciente.  
  > - **A 6 meses:** Seleccionamos `median_linear` (**MAE 9.58 puntos en validación y 8.09 en test**), logrando un 68.2% de precisión direccional equilibrada."

---

### 19. ¿Cómo habéis segmentado la cartera de clientes de Embat en la vista principal (`/`)?
* **Intención del jurado:** Evaluar si los filtros del dashboard tienen sentido comercial y operativo para Embat.
* **Respuesta exacta:**
  > "En `front/lib/cartera.ts` y `backend/routes/stats.py`, dividimos las 1.286 empresas en tres segmentos de acción para el equipo de Embat:  
  > 1. **Apostar:** Sociedades con score alto ($S \ge 65$) en estado `MEJORANDO` o `RECUPERACION`. Son candidatas directas para ampliación de servicios o recomendación de productos de financiación.  
  > 2. **Vigilar:** Sociedades en estado `TORCIENDOSE` o `DETERIORO`, o con caídas aceleradas en los últimos 3 meses ($\Delta 3m < -5$). Permite a Embat alertar al cliente antes de incurrir en impago o bajas por quiebra (*churn*).  
  > 3. **Acompañar:** Empresas en estado `BACHE` con solvencia estructural preservada. Requieren seguimiento de circulante puntual sin penalizar su relación comercial."

---

### 20. ¿Qué garantías tenemos de que vuestra demo en vivo no se caiga durante la presentación?
* **Intención del jurado:** Evaluar la robustez del stack y la preparación ante fallos técnicos.
* **Respuesta exacta:**
  > "La demo es **100% autocontenida y corre en local sin dependencias externas**:  
  > - **DuckDB (`xray.duckdb`):** 400 MB en local embebido; procesa las 30.000+ filas mensuales con consultas analíticas en **menos de 10 milisegundos**, sin requerir infraestructura cloud ni bases de datos remotas.  
  > - **FastAPI (`backend/`):** API REST con esquemas Pydantic v2 y **20/20 tests pasando** en `backend/test_backend.py`.  
  > - **Next.js 16 (`front/`):** Compilación estricta en TypeScript con cero errores de build.  
  > - **Cero APIs externas:** Durante la navegación en vivo no dependemos de llamadas a LLMs ni APIs de terceros que puedan sufrir cortes de red o límites de cuota."

---

## Tabla Resumen de Métricas Clave

| Dimensión / Indicador | Valor Exacto en el Repositorio | Ubicación en el Código |
| :--- | :--- | :--- |
| **Universo de Datos** | 1.286 empresas en 250 holdings / 24 meses históricos | `xray.duckdb` / `dataset/` |
| **Fórmula Score Base** | $100 \cdot (0.50 L + 0.30 C + 0.20 D)$ | `algorythm/score_engine.py` |
| **Ajustes Dinámicos** | Momentum ($\pm 8$), Crecimiento ($+6$), Fragilidad ($-8$) | `algorythm/score_engine.py` |
| **Estados Analíticos** | 6 estados (`ESTABLE`, `TORCIENDOSE`, `DETERIORO`, `MEJORANDO`, `RECUPERACION`, `BACHE`) | `algorythm/score_states.py` |
| **Consolidación Holding** | $0.65 \cdot \text{Media} + 0.35 \cdot \text{Mínimo}$ (penalización contagio si filial $< 40$) | `algorythm/build_duckdb.py` |
| **Inferencia Flujos Grupo** | Misma fecha, mismo importe $\ge 500$€ (24x más frecuente que ruido; 1.6% probabilidad de error) | `backend/routes/graph.py` |
| **Latencia What-If** | $< 4\text{ ms}$ por simulación de palancas | `algorythm/score_whatif.py` |
| **MAE Forecasting 1m** | 4.17 puntos en validación de grupos (modelo Huber) | `forecasting/benchmarks/LEADERBOARD.md` |
| **Tests Backend** | 20 / 20 tests unitarios y de integración pasando | `backend/test_backend.py` |
