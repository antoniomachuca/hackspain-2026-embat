# Research: Claude · Carlos

**Reto:** X-Ray (Embat) · HackSpain 2026 · 18–20 sep, ETSIT UPM
**Fuente:** Claude (panorama de mercado + estrategia técnica y de producto)
**Recopilado por:** Carlos León
**Fecha:** 2026-09-18

---

Buena base de research. Con esto ya hay suficiente para construir el marco. Faltaban dos cosas rápidas: qué existe ya de "financial health score" comercial (tipo Dun & Bradstreet, Creditsafe, iwoca Flow) y algo sobre Embat como referencia del comprador.

Al grano con lo que hay ahí fuera y por dónde atacar el problema.

## Qué existe ya (panorama)

**Bureaus tradicionales (foto fija, justo lo que Embat dice que sobra)**

D&B, Equifax, Creditsafe: scores actualizados mensual o trimestralmente a partir de cuentas depositadas + historial de pagos. Muy usados pero más de la mitad de las pymes ni siquiera revisan su score regularmente, y solo un 20% confía en que estas agencias reflejen bien su salud real. iwoca acaba de lanzar "Credit Compass" para dar visibilidad — pero sigue siendo un refresco mensual, no un flujo continuo. Ahí está exactamente el hueco que el reto os pide llenar.

**Cash-flow / open-banking underwriting (lo más cercano a lo que os piden)**

Es la categoría que más se parece a vuestro track. Plaid construyó **LendScore**: un modelo de riesgo que convierte datos de flujo de caja y de red en un score, entrenado sobre 1,44M de líneas de crédito combinando transacciones bancarias con etiquetas de mora. Técnicamente es XGBoost con restricciones monotónicas por feature (más saldo o entradas más regulares → siempre menor riesgo), lo que le da robustez e interpretabilidad a la vez. Codat, Ocrolus y Finexer hacen algo similar: ingieren transacciones + facturas y sacan atributos de riesgo listos para prestamistas.

Moody's, junto con Credit Data Research y CRIF, va un paso más allá: reconstruye estados financieros en tiempo real a partir de datos de open banking y los mete en un modelo de PD clásico tipo RiskCalc — es decir, usan el rastro para simular la "foto" que antes tardaba meses en llegar, no para leer directamente la trayectoria. Ese es justo el paso que el reto os pide saltar.

**Early Warning Systems (EWS) — la pieza que más encaja con las 6 preguntas**

Es un campo maduro en banca corporativa. Un EWS usa analítica predictiva para detectar deterioro de crédito antes de que sea evidente, permitiendo intervenir antes de que escale a impago, y suele combinar redes neuronales/deep learning para datos no estructurados con modelos de series temporales (LSTM, ARIMA) para detectar tendencias. Un reto real que se menciona en la literatura: los mejores predictores 3-6 meses antes del evento parecen "señales débiles", así que la interpretabilidad importa tanto como la puntería. Para el componente de "cuándo se vio venir", la técnica estándar fuera de finanzas (mantenimiento predictivo, EWS clínicos) es **detección de cambio de régimen** (change-point detection): detectar el momento en que las características de un sistema cambian de forma significativa, usando distancia estadística entre ventanas de tiempo.

**Explicabilidad**

SHAP es el estándar de facto en scoring crediticio ahora mismo. Trata cada feature como un "jugador" y reparte de forma justa la contribución de cada uno a la predicción, con garantías matemáticas de que la suma de contribuciones = output del modelo. Y hay literatura específica ya aplicada a scoring de pymes en plataformas P2P con Shapley values para explicar decisiones de préstamo a pymes que buscan financiación. Esto resuelve directamente la pregunta "por qué ha cambiado" del brief.

## Cómo atacar el problema técnico

**1. Features, no raw data.** Con 250 empresas (y solo 1.286 filas reales si cuentas grupo×filial), un LSTM sobre secuencias crudas va a sobreajustar. La jugada ganadora aquí es ingeniería de features mensuales agregadas por empresa, con ventanas rolling (3/6/12 meses) sobre las 5 tablas: DSO/DPO, % facturas vencidas, concentración de contrapartes, volatilidad de tesorería, ratio de utilización de deuda, coste medio de financiación, y sobre todo **la pendiente y la aceleración** de cada una de estas series (no solo su nivel).

**2. Modelo de score: gradient boosting, no deep learning.** LightGBM/XGBoost con restricciones monotónicas (como hace Plaid) — así garantizas que "más facturas vencidas → score no puede subir", cosa que un jurado va a valorar en la pregunta de "artesanía" y te evita explicaciones contraintuitivas. Cuidado con el split train/test: como hay holdings con varias filiales, hay que particionar por grupo empresarial para no filtrar información entre filiales del mismo dueño.

**3. Trayectoria y "bache vs. caída estructural": modelo de dos capas.**

- Capa 1: el score de nivel (el gradient boosting de arriba).
- Capa 2: sobre la *serie temporal del score suavizado*, aplicar detección de cambio de régimen (CUSUM o un HMM de 2-3 estados: sano / bache / deterioro estructural) para diferenciar ruido de tendencia real, y para poder decir "cuántos meses antes lo vimos" con un número, no una intuición.

**4. Explicabilidad: SHAP por mes + traducción a lenguaje natural.** Sacas los 3 features que más movieron el score ese mes y generas una frase tipo "DSO subió de 45 a 70 días en 2 meses, concentrado en 2 clientes" — esto es lo que un comité de riesgo (o el propio CFO) necesita ver, no un gráfico de barras SHAP crudo.

**5. Detección bidireccional sin desequilibrio de clases.** En vez de entrenar un clasificador binario "quiebra sí/no" (que en un dataset sintético probablemente tiene pocos eventos extremos), entrenar sobre la variación continua del score mes a mes — así "mejora" y "deterioro" son simétricos por construcción, y no hacen falta dos modelos separados.

## Sobre el producto — el comprador que ya tenéis delante

El brief lo dice explícito: el comprador obvio es quien os da los datos. Pero fijaos que **Embat mismo ya es la plataforma perfecta para vender esto**: tiene 400 clientes corporativos y un agente propio, TellMe, que ya analiza patrones de cash flow y da recomendaciones. Un producto que se venda literalmente como "módulo de salud financiera dentro de Embat" (o de cualquier tesorería tipo Embat) tiene un canal de distribución evidente y resuelve la pregunta de "quién lo paga" sin inventar nada: el propio cliente de tesorería que ya paga por ver su caja, ahora paga por saber hacia dónde va y por qué, con alertas proactivas — exactamente el bonus de "monitor que avisa" del brief.

Otra vía diferenciadora que nadie del dataset os obliga a usar pero que el propio archivo `groups.csv` os regala: la estructura de holding/filiales. Señal de contagio intra-grupo (si una filial se deteriora, ¿arrastra a las demás del mismo grupo antes de que se vea en sus propios números?) es un ángulo que ni Plaid ni Moody's explotan porque no suelen tener visibilidad de grupo — y encaja perfecto con "anticipación medida".

---

**Siguiente paso sugerido:** montar un esqueleto de notebook (feature engineering + LightGBM + SHAP) para arrancar en cuanto estén los CSV cargados, o primero cerrar con el equipo qué producto se construye encima.
