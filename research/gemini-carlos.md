# Research: Gemini · Carlos

**Reto:** X-Ray (Embat) · HackSpain 2026 · 18–20 sep, ETSIT UPM
**Fuente:** Gemini (estado del arte + ideas de producto)
**Recopilado por:** Carlos León
**Fecha:** 2026-09-18

---

El sistema financiero actual evalúa el riesgo y la salud de las empresas basándose en fotografías estáticas del pasado: cuentas anuales, balances de situación y ratings de crédito que se actualizan cada varios meses o cuando ya ha ocurrido un impago. El problema fundamental que plantea este reto es que dos empresas con una "fotografía" idéntica hoy pueden tener perfiles de riesgo diametralmente opuestos debido a su trayectoria y comportamiento en tiempo real.

El gráfico del enunciado ilustra este fallo del sistema tradicional: muestra a Northbrook Foods mejorando su puntuación de 45 a 65 durante 24 meses, mientras que Velasco Industrial se deteriora cayendo de 82 a 68. En el mes 24, la diferencia entre ambas es de apenas tres puntos, haciendo que en una evaluación estática parezcan riesgos similares, a pesar de que sus trayectorias demuestran que una es mucho mejor riesgo que la otra.

A continuación, el estado del arte, la naturaleza del problema y cómo estructurar una estrategia ganadora para el hackathon.

## El Estado del Arte: ¿Qué existe ahora mismo?

El ecosistema actual de evaluación financiera y tesorería se divide en tres grandes bloques, cada uno con limitaciones que este reto busca superar:

* **Burós de Crédito y Modelos Tradicionales (Ej. Experian, Equifax, Altman Z-Score):** Se basan en datos históricos, cuentas depositadas en registros y ratios estáticos. Son sistemas lentos, altamente reactivos e incapaces de prever un bache de liquidez con meses de antelación. Solo ven el "choque", no la "frenada".
* **Open Banking y Agregadores (Ej. Plaid, Tink, Belvo):** Han democratizado el acceso a los movimientos bancarios en tiempo real. Sin embargo, la mayoría de las soluciones se quedan en la capa de agregación de datos o en métricas de liquidez muy básicas. No cruzan la información bancaria con el ERP (facturación) ni con las condiciones de deuda para crear un modelo predictivo completo.
* **Sistemas de Gestión de Tesorería o TMS (Ej. Embat, Kyriba):** Automatizan la conciliación bancaria, prevén flujos de caja y centralizan la información. Son herramientas operativas excelentes, pero el salto hacia la **inteligencia predictiva explicable** —decirle a un CFO "tu salud financiera se está deteriorando por estos tres factores específicos y tendrás problemas en 4 meses"— es la frontera tecnológica actual.

## Estrategia Técnica: Cómo atacar el "Motor" (El Score)

Para ganar en la parte predictiva y cumplir con la evaluación (generalización, anticipación, explicabilidad), el enfoque debe centrarse más en la ingeniería de variables (Feature Engineering) que en algoritmos extremadamente complejos.

* **Construcción de Variables (Features):**
  * *Velocidad y Comportamiento de Pago (`invoices.csv` + `transactions.csv`):* Calcula los Días Medios de Cobro (DSO) y Días Medios de Pago (DPO). ¿La empresa está retrasando pagos a proveedores últimamente? Esa es la primera señal de estrés.
  * *Estrés de Cobertura de Deuda (`debt_schedule_config.csv` + `balances.csv`):* Relaciona la caja disponible y las entradas proyectadas con las cuotas de préstamos inminentes.
  * *Volatilidad de Flujo de Caja:* Evalúa la varianza en los ingresos recurrentes frente a los costes fijos mensuales.
  * *Derivadas Temporales:* No uses solo los valores del mes actual. Introduce variables que midan la tasa de cambio (ej. "Delta del DSO en los últimos 3 meses"). Esto es lo que captará la **trayectoria**.

* **Modelado y Explicabilidad (White-Box AI):**
  * Huye de las redes neuronales densas. Si no puedes explicar por qué el score cambió, penalizarán la entrega.
  * Utiliza modelos basados en árboles de decisión (como **XGBoost** o **LightGBM**), que suelen ofrecer el mejor rendimiento con datos tabulares financieros.
  * Aplica **SHAP values** (Shapley Additive exPlanations) a la salida de tu modelo. SHAP permite cumplir el requisito de explicabilidad de forma literal: se puede mostrar un gráfico en la demo que diga "El score de esta empresa bajó 5 puntos este mes específicamente porque sus clientes han retrasado los pagos un 15% y ha agotado el 80% de su línea de crédito".

## Ideas de Producto: La Capa de Negocio (Qué construir encima)

El score no es el producto, es el habilitador. Hay que elegir un caso de uso donde la anticipación genere valor económico y el comprador esté claro.

### 1. El "CFO Copilot" Proactivo (Comprador: La propia empresa)

Un agente de IA integrado en el panel de tesorería que no espera a que el director financiero revise los datos. Monitoriza el score en silencio y levanta la mano: *"He detectado que tu ratio de salud ha bajado de 75 a 68 en los últimos dos meses debido a retrasos en cobros de tu cliente principal. Te sugiero activar la línea de crédito de factoring ahora, mientras tus condiciones de financiación (basadas en un score todavía aceptable) son favorables."*

*Por qué funciona:* Cumple el bonus de "monitor que avisa" y el comprador es directo (se vende como módulo premium de software de tesorería).

### 2. Póliza de Seguro de Impago Dinámica (Comprador: Aseguradoras B2B)

El seguro de crédito tradicional cobra una prima fija anual y muchas veces cancela coberturas de golpe cuando hay malas noticias. Se puede crear un motor de *pricing* dinámico para aseguradoras de crédito comercial. Si una empresa da acceso a su rastro de tesorería y su score mejora, la prima de su seguro baja mes a mes. Si se deteriora, la aseguradora puede mitigar su riesgo meses antes del impago.

*Por qué funciona:* Las aseguradoras pagan millones por mitigar riesgos y reducir la siniestralidad.

### 3. Supply Chain Finance / Confirming Inteligente (Comprador: Grandes Corporaciones)

Una herramienta para que una empresa grande gestione a sus proveedores. Si el sistema detecta (mediante el score de las filiales o proveedores) que un proveedor estratégico está empezando a "torcerse" y necesita liquidez, el sistema sugiere automáticamente ofrecerle un pago anticipado (confirming) a cambio de un descuento del 2%.

*Por qué funciona:* La empresa tractora salva a un proveedor clave de la quiebra y a la vez obtiene rentabilidad financiera por su exceso de caja.

---

Para la demo: preparar una interfaz limpia (por ejemplo en Streamlit o Vercel) que muestre la curva de dos empresas contrastadas, el desglose de motivos (SHAP values) del porqué de la puntuación en un mes concreto, y una simulación de cómo el producto final ejecuta una acción basada en ese cambio.
