# Especificación de Requisitos de Software (SRS) · Motor X-Ray
> **Estándar:** Basado en ISO/IEC/IEEE 29148 / IEEE 830 (Especificación Formal de Requisitos)  
> **Proyecto:** HackSpain 2026 · Reto Embat (X-Ray)  
> **Última actualización:** 2026-09-18 (Revisión Integral: Formato Formal IEEE 29148, Principios SOLID y Factor WOW)

---

## 0. Marco Metodológico y Principios Arquitectónicos SOLID

Este documento formaliza los requisitos funcionales y no funcionales del sistema conforme a la metodología de ingeniería de requisitos de **IEEE 29148**. Cada requisito se define mediante una ficha estandarizada que detalla: **Identificador y Título**, **Descripción**, **Prioridad**, **Dependencias**, **Entradas**, **Procesamiento**, **Salidas**, **Excepciones y Errores**, y el **Principio Arquitectónico SOLID** subyacente.

### 0.1. Clasificación de Prioridades
- **P0 (Crítico / Núcleo):** Imprescindible para el motor de scoring, la consistencia de datos y el flujo principal de la demo ante el jurado.
- **P1 (Obligatorio del Track):** Requisitos funcionales obligatorios del enunciado de Embat que completan la visión de producto (Día 2).
- **P2 (Diferenciador / Factor WOW):** Capacidades que maximizan la probabilidad de victoria (ejecución autónoma en 1 clic, pasaporte QR interactivo, grounding en vivo con Exa).

### 0.2. Reglas de Arquitectura y Principios SOLID
1. **Single Responsibility (SRP):** Desacoplar estrictamente la ingesta de ficheros (I/O) de la normalización contable, el cálculo de features y la persistencia de percentiles.
2. **Open / Closed (OCP):** El catálogo de palancas de simulación se implementa mediante el patrón *Strategy* (`IPalanca`), permitiendo añadir nuevas estrategias de optimización financiera sin modificar el simulador ni introducir condicionales monolíticos.
3. **Liskov Substitution (LSP):** Jerarquía estricta y sin colisión de tipos en el modelado de productos financieros (`ProductoBancario`, `ProductoDeuda`), garantizando sustituibilidad plena sobre la interfaz base `Producto`.
4. **Interface Segregation (ISP):** La API de servicio expone interfaces segregadas por caso de uso (`IScoreService`, `IGroupService`, `ISimulatorService`, `IAlertService`, `IActionService`), evitando que clientes especializados dependan de métodos ajenos a su dominio.
5. **Dependency Inversion (DIP):** Los servicios de alto nivel dependen de abstracciones. Se garantiza la existencia de un `APIMock` y un `FixtureOffline` para desacoplar el desarrollo de frontend y asegurar la demo ante caídas de red.

---

## 1. Módulo B0 · Ingesta, Integridad y Normalización Financiera

### REQ-B0.1: Ingesta de Datos Tipados y Auditoría de Ficheros
- **Descripción:** Cargar los nueve ficheros del dataset sintético aplicando tipado estricto en el esquema tabular y registrando la integridad de los datos.
- **Prioridad:** P0
- **Dependencias:** Ninguna (origen primario de datos).
- **Entradas:** Ficheros CSV/JSON en `dataset/` (`groups`, `companies`, `banking_products`, `debt_products`, `debt_schedule_config`, `transactions`, `invoices`, `balances`, `data_dictionary.md`).
- **Procesamiento:** Lectura por streams o bloques, conversión explícita de identificadores a texto, fechas a formato canónico ISO (`date`) e importes a representación numérica de alta precisión (`decimal/float64`). Verificación de huellas SHA-256 por fichero.
- **Salidas:** Diccionario de estructuras de datos en memoria (`Tablas`) y manifiesto de auditoría con conteo exacto de filas por fichero.
- **Excepciones y Errores:** 
  - Fichero ausente o ruta inválida: Interrupción con código de error fatal.
  - Incoherencia de esquema (columnas faltantes): Registro en log y excepción explícita.
- **Principio SOLID:** Principio de Responsabilidad Única (SRP). La ingesta se limita a I/O y casteo de tipos primitivos, delegando transformaciones de negocio.

### REQ-B0.2: Validación de Integridad Referencial
- **Descripción:** Comprobar la coherencia relacional entre todas las tablas del modelo de datos de tesorería.
- **Prioridad:** P0
- **Dependencias:** REQ-B0.1.
- **Entradas:** `Tablas` cargadas en memoria.
- **Procesamiento:** 
  - Validar que todo `company_id` en transacciones, facturas, saldos y productos de deuda exista en `companies`.
  - Validar que todo `group_id` en `companies` exista en `groups`.
  - Validar que todo `product_id` en transacciones y saldos exista en `banking_products` o `debt_products`.
- **Salidas:** Booleano de conformidad relacional y reporte de claves foráneas huérfanas (en caso de existir).
- **Excepciones y Errores:** Claves huérfanas detectadas: aislamiento de filas incoherentes y registro de advertencia de auditoría.
- **Principio SOLID:** SRP. Validación desacoplada de la carga de datos.

### REQ-B0.3: Normalización de Signos Contables y Conversión Monetaria
- **Descripción:** Normalizar el signo de las transacciones y facturas bajo un criterio unificado y convertir importes a la divisa de referencia (EUR).
- **Prioridad:** P0
- **Dependencias:** REQ-B0.1.
- **Entradas:** `transactions`, `invoices`, tipos de cambio observados.
- **Procesamiento:** 
  - Convención unificada: entradas de caja / cobros con signo positivo ($+$); salidas / pagos con signo negativo ($-$).
  - En facturas: la dirección de la operación la determina el signo de `amount` (negativo = factura recibida/proveedor; positivo = factura emitida/cliente; verificado al 99,6% frente a extractos).
  - Conversión a EUR utilizando el tipo de cambio registrado en la fecha de la transacción (EUR representa el 89% del volumen total).
- **Salidas:** `Tablas` normalizadas con importes en EUR y signos consistentes.
- **Excepciones y Errores:** Tipos de cambio nulos o negativos: uso de tipo de cambio 1.0 documentado y marcado en la auditoría.
- **Principio SOLID:** SRP. Módulo `NormalizadorFinanciero` dedicado exclusivamente a reglas contables.

### REQ-B0.4: Saneamiento de Fechas Anómalas en Facturación
- **Descripción:** Detectar y filtrar registros de facturas con fechas lógicamente imposibles o anómalas sin alterar las filas válidas.
- **Prioridad:** P0
- **Dependencias:** REQ-B0.1.
- **Entradas:** Tabla `invoices`.
- **Procesamiento:**
  - Identificar años fuera de rango histórico (ej. 5026, 6913).
  - Identificar inconsistencias cronológicas: fecha de pago anterior a la fecha de emisión (29.089 filas).
  - Tratar el campo `payment_date`: en facturas con estado `pending` o `overdue`, reconocer que `payment_date` es un marcador sintético igual al vencimiento (96–98%), no una fecha real de cobro/pago.
- **Salidas:** Máscara booleana de facturas válidas para cálculo de retrasos temporales.
- **Excepciones y Errores:** Registros anómalos: exclusión automática del cálculo de días de demora (DSO/DPO) sin eliminación física de la factura.

### REQ-B0.5: Filtro y Desacoplamiento de Flujos Intragrupo
- **Descripción:** Identificar y segregar las transferencias y operaciones financieras entre filiales del mismo holding para evitar duplicidad de ingresos y deuda en el análisis consolidado.
- **Prioridad:** P1
- **Dependencias:** REQ-B0.1, REQ-B0.2.
- **Entradas:** `transactions`, mapa de filiales por `group_id`.
- **Procesamiento:** Identificación de movimientos clasificados bajo categoría `transfer` y préstamos categorizados como `Other (customer-defined)`.
- **Salidas:** Conjunto de transacciones filtradas sin flujos cruzados intragrupo.
- **Excepciones y Errores:** Ausencia de cruce explícito de NIFs entre contrapartes: el filtro opera por aproximación categórica y se registra en la confianza de la métrica.
- **Principio SOLID:** SRP. La regla de identificación no reside en la entidad `Transaccion`, sino en el servicio `FiltroIntragrupo`.

---

## 2. Módulo B1 · Feature Engineering Causal del Rastro (Point-in-Time)

### REQ-B1.1: Garantía Causal As-Of (Point-in-Time)
- **Descripción:** Asegurar que todo cálculo de variables en el mes $t$ utilice únicamente información disponible y contabilizada hasta el corte $t$, sin fuga de datos del futuro (*lookahead leakage*).
- **Prioridad:** P0
- **Dependencias:** REQ-B0.3, REQ-B0.4.
- **Entradas:** `Tablas` normalizadas y fecha de corte $t$.
- **Procesamiento:** Filtrado temporal estricto: `issuance_date <= t`, transacciones con `booking_date <= t`. Prohibición expresa de reconstruir saldos históricos retrospectivamente desde `balances.csv` (foto fija final a 2026-09-01).
- **Salidas:** Vistas temporales acotadas $V_t$ para cada empresa y mes.
- **Excepciones y Errores:** Intentos de consultar registros con timestamp posterior a $t$: rechazo en tiempo de compilación/ejecución mediante assertion de causalidad.

### REQ-B1.2: Cálculo del Pilar de Cobertura Operativa y Liquidez
- **Descripción:** Computar el margen de flujo de caja neto frente a salidas operativas acumuladas en ventanas móviles de 3 y 12 meses.
- **Prioridad:** P0
- **Dependencias:** REQ-B1.1.
- **Entradas:** Cobros netos $R_t$, pagos operativos $E_t$, saldo de caja $K_t$ (si se dispone de observación auditada).
- **Procesamiento:**
  - Sin saldo conocido: Ratio de margen operativo $u_t = \frac{R_t^{[3]} - E_t^{[3]}}{R_t^{[3]} + E_t^{[3]}}$ transformado mediante $L_t^b = \mathcal{A}\left(\frac{1}{2} + \frac{1}{2}\tanh(u_t / 0{,}50), \rho_t\right)$.
  - Con saldo conocido: Ponderación de runway operativo $\ell_t^{\mathrm{run}}$ y cobertura de compromisos a 30 días $\ell_t^{\mathrm{cov}}$.
- **Salidas:** Valor escalar $L_t \in [0, 1]$ y métricas de soporte (`runway_months`, `cash_margin`).
- **Excepciones y Errores:** Sin flujos observados ($R = E = 0$): emisión de prior neutral $L_t = 0{,}50$ con indicador de falta de evidencia.

### REQ-B1.3: Cálculo del Pilar de Calidad de Cobro y Comportamiento de Pago
- **Descripción:** Medir la puntualidad, estabilidad y devoluciones en los cobros bancarios, enriquecida con métricas de facturación ERP cuando estén disponibles.
- **Prioridad:** P0
- **Dependencias:** REQ-B1.1.
- **Entradas:** Devoluciones bancarias $U_t$, cobros brutos $R_t^+$, desviación estándar mensual $CV_t$, pendiente de facturas $AR_t$, facturación $V_t$.
- **Procesamiento:**
  - Núcleo bancario: Tasa de devoluciones $f_t = U_t^{[3]} / (R^+)_t^{[3]}$ y regularidad $CV_t$ mediante $C_t^b$.
  - Enriquecimiento ERP condicional: $DSO_t = d_t \frac{AR_t}{V_t^{[3]}}$ y tasa de facturas vencidas impagadas $p_t^{\mathrm{late}}$.
  - Mezcla acotada: $C_t = (1 - \eta_t) C_t^b + \eta_t C_t^e$ con $\eta_t \leq 0{,}40$.
- **Salidas:** Valor escalar $C_t \in [0, 1]$, $DSO_t$ observado y tasa de morosidad comercial.
- **Excepciones y Errores:** Empresas sin módulo ERP sincronizado (501 sociedades): $\eta_t = 0$; el pilar se calcula al 100% sobre el núcleo bancario sin penalización por ausencia de software.

### REQ-B1.4: Cálculo del Pilar de Carga de Deuda Observada
- **Descripción:** Evaluar la presión del servicio financiero bancario sobre los cobros corrientes de la empresa.
- **Prioridad:** P0
- **Dependencias:** REQ-B1.1.
- **Entradas:** Salidas bancarias de `debt_repayment` e `interest_charge` ($H_t$), cobros netos $R_t$.
- **Procesamiento:**
  - Ratio de absorción de deuda: $d_t^H = \frac{H_t^{[3]}}{R_t^{[3]} + H_t^{[3]}}$.
  - Transformación conservadora: $D_t = \mathcal{A}\left(\frac{1}{2} - \frac{1}{2}\tanh(d_t^H / 0{,}25), \rho_t\right)$, acotada en $[0, 0{,}50]$.
- **Salidas:** Valor escalar $D_t \in [0, 0{,}50]$ y flag `debt_service_observed`.
- **Excepciones y Errores:** 71% de empresas sin movimientos de deuda registrados: asignación automática del prior neutro $D_t = 0{,}50$. No se asume solvencia plena ni deuda cero.

### REQ-B1.5: Cálculo de Concentración de Contrapartes (HHI) y Desajuste Intrames
- **Descripción:** Determinar el índice de Herfindahl-Hirschman sobre clientes principales y cuantificar la tensión temporal de caja dentro del mes.
- **Prioridad:** P0
- **Dependencias:** REQ-B1.1.
- **Entradas:** Facturación o cobros por contraparte individual, serie diaria de flujos netos intrames $z_{m,u}$.
- **Procesamiento:**
  - Concentración: $HHI_t = \sum_j a_{j,t}^2$ sobre contrapartes con al menos 95% de volumen resuelto.
  - Tensión temporal: Déficit intrames máximo acumulado $A_m$, normalizado frente a gastos operativos.
  - Formulación de fragilidad: $F_t = \rho_t \left[ (1 - \theta_t) s_t + \theta_t h(HHI_t; 0{,}25) \right]$.
- **Salidas:** Valor escalar de fragilidad $F_t \in [0, 1]$ e índice $HHI_t$.
- **Excepciones y Errores:** Menos del 95% de contrapartes identificadas: $\theta_t = 0$; la fragilidad se calcula exclusivamente sobre la tensión temporal bancaria.

---

## 3. Módulo B2 · Grupos de Pares y Tablas de Percentiles Congeladas

### REQ-B2.1: Segmentación Determinista de Peer Groups
- **Descripción:** Asignar cada empresa a un grupo homogéneo de referencia basado en su tamaño económico real.
- **Prioridad:** P0
- **Dependencias:** REQ-B1.2.
- **Entradas:** Cobros anualizados por empresa.
- **Procesamiento:** Segmentación en 4 cuartiles de tamaño económico (~321 empresas por cuartil). Exclusión de segmentación por país debido a que el 82% del campo país en el dataset es nulo o ruidoso.
- **Salidas:** Asignación unívoca `peer_id` para cada sociedad.
- **Excepciones y Errores:** Empresas sin actividad inicial: asignación al grupo global con bandera de `peer_limitado`.

### REQ-B2.2: Construcción y Persistencia de Tablas de Percentiles Congeladas
- **Descripción:** Generar las tablas de deciles de distribución para cada feature y cuartil exclusivamente con el conjunto de entrenamiento y serializarlas en disco.
- **Prioridad:** P0
- **Dependencias:** REQ-B2.1, REQ-B1.2 a REQ-B1.5.
- **Entradas:** Matriz de features del conjunto de entrenamiento.
- **Procesamiento:** Cálculo de percentiles empíricos por bloque y cuartil. Almacenamiento versionado en disco (`PercentilRepositorio`).
- **Salidas:** Archivo inmutable de deciles de referencia.
- **Excepciones y Errores:**
  - Valores extremos fuera de rango: saturación suave en 0 o 100 sin extrapolación.
- **Principio SOLID:** Inversión de Dependencias (DIP) y SRP. Las tablas no se recalculan al puntuar nuevas empresas; el repositorio aísla la persistencia de la lógica de scoring.

---

## 4. Módulo B3 · Motor de Scoring Continuo, Momentum y Estados

> **Estado de Implementación:** El motor algorítmico y la formulación matemática ya están **100% implementados, validados y testeados en producción interna** en [`algorythm/score_engine.py`](../algorythm/score_engine.py), con especificación formal en [`algorythm/formula/score_financiero.pdf`](../algorythm/formula/score_financiero.pdf) y benchmark reproducible en [`algorythm/engine_results/`](../algorythm/engine_results/) pasando 30/30 tests de contrato. No es una propuesta futura: es código operativo en `main`.

### REQ-B3.1: Formulación Global del Score Axiomático
- **Descripción:** Ejecutar la ecuación maestra que integra el nivel base, la inercia temporal, el crecimiento de calidad y la penalización de fragilidad.
- **Estado:** **IMPLEMENTADO Y VALIDADO** en [`algorythm/score_engine.py`](../algorythm/score_engine.py).
- **Prioridad:** P0
- **Dependencias:** REQ-B1.2 a REQ-B1.5, REQ-B2.2.
- **Entradas:** Vectores normalizados $L_t, C_t, D_t, M_t, G_t, F_t$.
- **Procesamiento:**
  - Nivel base: $B_t = 100(0{,}50 L_t + 0{,}30 C_t + 0{,}20 D_t)$.
  - Ecuación global: $S_t = \operatorname{clip}_{[0,100]}\left( B_t + 8 M_t + 6 G_t - 8 F_t \right)$.
  - Cálculo del residuo de recorte: $\Delta_t^{\mathrm{clip}} = S_t - (B_t + 8 M_t + 6 G_t - 8 F_t)$.
- **Salidas:** Puntuación continua $S_t \in [0, 100]$, valor de nivel $B_t$ y residuo de clipping.
- **Excepciones y Errores:** Ausencia de historial suficiente: retorno de prior neutral $S_t = 50{,}00$ con bandera `is_prior=True`.

### REQ-B3.2: Momentum Bidireccional con Filtro de Persistencia
- **Descripción:** Calcular la trayectoria de la empresa reconociendo mejoras y deterioros continuos, inmune a baches transitorios de un solo mes.
- **Prioridad:** P0
- **Dependencias:** REQ-B3.1.
- **Entradas:** Serie histórica de base bancaria $B_t^b$ y márgenes de flujo mensual $x_t$.
- **Procesamiento:**
  - Velocidad y cruce de medias exponenciales: $v_t = (B_t^b - B_{t-3}^b)/3$, $E_{3,t} - E_{6,t}$.
  - Filtro de confirmación de 6 meses con medianas no solapadas: $c_t \in [0, 1]$.
  - Momentum resultante: $M_t = c_t \left[ \frac{1}{2}\tanh(v_t/2) + \frac{1}{2}\tanh((E_{3,t} - E_{6,t})/5) \right]$.
- **Salidas:** Vector de inercia $M_t \in [-1, 1]$.
- **Excepciones y Errores:** Shocks aislados de 1 mes: $c_t = 0$, neutralizando el momentum y evitando falsas alarmas ante baches temporales.

### REQ-B3.3: Clasificación de Estados Financieros de Trayectoria
- **Descripción:** Asignar a cada empresa y mes uno de los seis estados dinámicos del sistema.
- **Prioridad:** P0
- **Dependencias:** REQ-B3.1, REQ-B3.2.
- **Entradas:** Nivel $B_t$, momentum $M_t$, historial de 6 meses.
- **Procesamiento:** Clasificación determinista en: `MEJORANDO`, `ESTABLE`, `TORCIENDOSE`, `DETERIORO`, `BACHE`, `RECUPERACION`. En particular, `TORCIENDOSE` se activa cuando $M_t < -0{,}10$ durante 3 meses consecutivos manteniendo aún $B_t \geq 60$.
- **Salidas:** Etiqueta categórica de estado por empresa-mes.
- **Excepciones y Errores:** Empresas con menos de 6 meses de historial: asignación de estado `EVALUACION_PENDIENTE`.

---

## 5. Módulo B4 · Explicabilidad y Descomposición Aditiva Exacta (Waterfall)

### REQ-B4.1: Descomposición Aditiva Exacta sin Cajas Negras
- **Descripción:** Descomponer el score mensual en sus seis contribuciones exactas en puntos sin utilizar aproximaciones locales opacas (SHAP o LIME).
- **Estado:** **IMPLEMENTADO Y VALIDADO** en [`algorythm/score_engine.py`](../algorythm/score_engine.py) (campo `clipping_points` y sumatorio exacto).
- **Prioridad:** P0
- **Dependencias:** REQ-B3.1.
- **Entradas:** Componentes del score y residuo de clipping.
- **Procesamiento:** Validación de la igualdad algebraica:
  $$S_t = 50 L_t + 30 C_t + 20 D_t + 8 M_t + 6 G_t - 8 F_t + \Delta_t^{\mathrm{clip}}.$$
- **Salidas:** Lista de factores con contribución exacta en puntos de score.
- **Excepciones y Errores:** Discrepancia matemática superior a $10^{-6}$: error fatal de integridad del motor.

### REQ-B4.2: Explicación del Delta Mensual y Generación de Códigos de Razón
- **Descripción:** Explicar por qué ha variado el score entre el mes $t$ y el mes $t-1$ y asociar los códigos de razón normalizados.
- **Prioridad:** P0
- **Dependencias:** REQ-B4.1.
- **Entradas:** Scores y descomposiciones de los meses $t$ y $t-1$.
- **Procesamiento:**
  - Resta término a término: $\Delta S_t = \sum_j \Delta \text{contrib}_{j,t}$.
  - Identificación de los 2 drivers dominantes expresados en unidades de negocio (días de DSO, % de margen, € de deuda).
  - Asignación de códigos estándar: `RC_01_FLUJO_INSUFICIENTE`, `RC_02_DETERIORO_COBROS`, `RC_03_CARGA_FINANCIERA`, `RC_04_CONCENTRACION_INGRESOS`, `RC_05_CONFIANZA_LIMITADA`.
- **Salidas:** Lista de drivers explicativos, códigos de razón y síntesis textual estructurada.
- **Excepciones y Errores:** Variación nula ($\Delta S_t = 0$): emisión de código de estabilidad operativa.

---

## 6. Módulo B5 · Anticipación Cuantitativa, Monitor Proactivo y Grounding Externo

### REQ-B5.1: Cuantificación del Tiempo de Anticipación con Control de Falsas Alarmas
- **Descripción:** Medir cuántos meses antes el sistema detecta el deterioro estructural de una empresa respecto a su manifestación contable, fijando una tasa de error admisible.
- **Prioridad:** P1 (Bonus track)
- **Dependencias:** REQ-B3.2, REQ-B3.3.
- **Entradas:** Series de score y eventos de estrés de tesorería.
- **Procesamiento:** Medición del diferencial temporal: $\Delta t = t_{\text{evento}} - t_{\text{alerta}}$. Reporte como mediana de meses a una tasa fijada de 1 falsa alarma por empresa-año sobre empresas sanas.
- **Salidas:** Indicador de antelación validado (demostrando 8 meses de anticipación en escenario de asfixia).
- **Excepciones y Errores:** Empresas con historia corta (<12 meses): exclusión de la métrica de anticipación para evitar sesgo.

### REQ-B5.2: Monitor de Alertas Proactivo
- **Descripción:** Generar alertas automáticas cuando una sociedad cruce umbrales críticos de deterioro o inflexión negativa sin esperar a que el usuario consulte el panel.
- **Prioridad:** P2
- **Dependencias:** REQ-B3.3, REQ-B4.2.
- **Entradas:** Eventos de cambio a estados `TORCIENDOSE` o `DETERIORO`.
- **Procesamiento:** Emisión de alerta con severidad asignada (`ALTA`, `MEDIA`, `BAJA`), meses de anticipación estimada y los dos drivers causales desencadenantes.
- **Salidas:** Colección ordenada de objetos `Alerta`.
- **Excepciones y Errores:** Sin alertas activas: respuesta de lista vacía con estado normal de cartera.

### REQ-B5.3: Grounding Externo de Contrapartes mediante Exa API (Factor WOW Sponsor)
- **Descripción:** Enriquecer las alertas de concentración o retraso de cobro con información pública indexada en tiempo real sobre la contraparte afectada.
- **Prioridad:** P2 (Factor WOW / Sponsor HackSpain)
- **Dependencias:** REQ-B5.2.
- **Entradas:** Nombre o NIF de la contraparte morosa principal.
- **Procesamiento:** Consulta a la API de **Exa** (`exa-py`) buscando noticias recientes sobre reestructuraciones de deuda, EREs, insolvencias o cambios de administradores en prensa económica y boletines oficiales.
- **Salidas:** Noticia o hecho relevante adjunto a la alerta de cobro.
- **Excepciones y Errores:** Fallo de red o cuota de API de Exa: degradación elegante a la alerta puramente interna sin interrumpir la ejecución.
- **Principio SOLID:** Inversión de Dependencias (DIP). El adaptador `ExaGroundingService` implementa `IExternalIntelligenceService`.

---

## 7. Módulo B6 · Consolidación de Grupo y Riesgo de Contagio

### REQ-B6.1: Agregación de Sociedades Holding y Penalización por Contagio
- **Descripción:** Calcular la salud financiera consolidada de un grupo empresarial ponderando el tamaño de sus filiales y penalizando el arrastre de filiales en situación crítica.
- **Prioridad:** P1
- **Dependencias:** REQ-B0.5, REQ-B3.1.
- **Entradas:** Scores individuales de filiales, pesos por volumen de cobros, estructura del `group_id`.
- **Procesamiento:**
  - Agregación base: 65% media ponderada de filiales + 35% score de la peor filial.
  - Penalización por contagio si una filial material presenta $S_t < 40$.
- **Salidas:** Objeto `ScoreGrupo` con score consolidado, listado de filiales y penalización aplicada.
- **Excepciones y Errores:** Grupo con una única empresa: el score consolidado equivale exactamente al score individual sin penalización.

---

## 8. Módulo B7 · Capa de Servicios API, Segregación de Interfaces y Mocks

### REQ-B7.1: Contrato Congelado de Endpoints REST
- **Descripción:** Exponer el contrato de servicios mediante una API FastAPI tipada con esquemas Pydantic, garantizando disponibilidad inmediata mediante mocks.
- **Prioridad:** P0
- **Dependencias:** Ninguna (se inicializa con datos de fixture).
- **Entradas:** Peticiones HTTP REST sobre `/score`, `/group`, `/palancas`, `/simulate`, `/action/generate`, `/passport/{token}`, `/alerts`.
- **Procesamiento:** Enrutamiento a los casos de uso del motor o devolución de respuestas mockeadas deterministas en modo de pruebas.
- **Salidas:** Respuestas JSON validadas contra esquemas Pydantic.
- **Excepciones y Errores:** Entidad no encontrada (404), parámetros de simulación fuera de rango (422).
- **Principio SOLID:** Segregación de Interfaces (ISP) e Inversión de Dependencias (DIP). La API implementa interfaces modulares (`IScoreService`, `ISimulatorService`, `IActionService`).

### REQ-B7.2: Modo de Respaldo Offline y Determinismo
- **Descripción:** Proveer un componente de fixtures estáticos (`FixtureOffline`) que garantice la ejecución integral de la demo sin conexión a Internet o ante fallos del servidor.
- **Prioridad:** P0
- **Dependencias:** REQ-B7.1.
- **Entradas:** Solicitud con flag `DEMO_MODE=true` o fallo de red.
- **Procesamiento:** Carga de respuestas pregrabadas validadas correspondientes a los casos de demostración (Northbrook y Velasco).
- **Salidas:** Payloads JSON idénticos a los del motor real en milisegundos.
- **Excepciones y Errores:** Ninguno; el fallback es infalible.

---

## 9. Módulo B8 · Simulador Contrafactual y Catálogo Polimórfico de Palancas (Strategy)

### REQ-B8.1: Catálogo de Palancas Financieras bajo Patrón Strategy
- **Descripción:** Modelar cada palanca de optimización de circulante y deuda como una estrategia independiente que implementa una interfaz común.
- **Prioridad:** P0
- **Dependencias:** REQ-B1.2 a REQ-B1.5, REQ-B7.1.
- **Entradas:** Parámetros de la palanca (días, porcentajes, producto a refinanciar).
- **Procesamiento:** Cada clase concreta (`PalancaReducirDSO`, `PalancaRefinanciar`, `PalancaAmpliarDPO`, etc.) implementa:
  - `es_aplicable(empresa, tablas) -> bool`
  - `motivo_rechazo() -> str`
  - `aplicar(tablas, parametros) -> TablasModificadas`
- **Salidas:** Tablas de datos modificadas contrafactualmente.
- **Excepciones y Errores:** Palanca inaplicable (ej. sustituir factoring en una empresa sin factoring): rechazo con explicación motivada.
- **Principio SOLID:** Principio Abierto/Cerrado (OCP). Nuevas palancas financieras pueden añadirse al catálogo sin modificar la clase `Simulador`.

### REQ-B8.2: Simulación Contrafactual Estricta (Recomputación sin Gradientes)
- **Descripción:** Calcular el impacto de las palancas financieras reejecutando el pipeline completo sobre los datos modificados, sin aproximaciones por derivadas.
- **Prioridad:** P0
- **Dependencias:** REQ-B8.1, REQ-B3.1.
- **Entradas:** `TablasModificadas` tras aplicar la estrategia.
- **Procesamiento:** Reejecución de B1 (features) $\to$ B2 (percentiles congelados) $\to$ B3 (score). Obtención del nuevo score $S_{\text{nuevo}}$ y cálculo de $\Delta S$.
- **Salidas:** Objeto `ResultadoSimulacion` con nuevo score, delta de score y parámetros traducidos.
- **Excepciones y Errores:** Parámetros fuera de rangos plausibles (ej. DSO negativo): saturación en el límite inferior admisible.

---

## 10. Módulo B9 · Puente Transaccional a Euros

### REQ-B9.1: Traducción Aritmética de Caja Liberada
- **Descripción:** Cuantificar la liquidez inmediata liberada por mejoras en el periodo de cobro de clientes.
- **Prioridad:** P0
- **Dependencias:** REQ-B8.2.
- **Entradas:** Variación de días de cobro $\Delta \mathrm{DSO}$, facturación media diaria en EUR.
- **Procesamiento:** Cálculo determinista:
  $$\text{Caja Liberada (€)} = \Delta \mathrm{DSO} \times \text{Facturación Diaria}.$$
- **Salidas:** Importe exacto en euros de caja operativa disponible.
- **Excepciones y Errores:** Facturación nula: caja liberada igual a cero euros.

### REQ-B9.2: Curva de Tipos de Interés y Ahorro Financiero Anual
- **Descripción:** Mapear la mejora de score a una reducción de diferencial de crédito (*spread*) en puntos básicos y calcular el ahorro financiero anual.
- **Prioridad:** P1
- **Dependencias:** REQ-B8.2.
- **Entradas:** Score antes, score simulado, pasivo financiero vivo con coste.
- **Procesamiento:**
  - Consulta de la curva empírica de tipos implícitos observados: $\text{Tipo}(S) = f(S)$.
  - Cálculo de $\Delta \mathrm{bps} = \text{Tipo}(S_{\text{antes}}) - \text{Tipo}(S_{\text{después}})$.
  - Ahorro anual: $\text{Ahorro (€/año)} = \text{Deuda Viva} \times \frac{\Delta \mathrm{bps}}{10.000}$.
- **Salidas:** $\Delta \mathrm{bps}$ y ahorro anual en intereses en EUR.
- **Excepciones y Errores:** Empresas sin deuda viva: $\Delta \mathrm{bps}$ mostrado a título informativo y ahorro anual fijado en 0 €.

---

## 11. Módulo B10 · Agente de Ejecución Transaccional en Un Clic (Factor WOW)

### REQ-B10.1: Proposición Determinista de Recomendaciones
- **Descripción:** Seleccionar y parametrizar las palancas que mayor impacto positivo generen sobre el score y la caja del cliente sin inventar ninguna cifra.
- **Prioridad:** P1
- **Dependencias:** REQ-B4.2, REQ-B8.2, REQ-B9.1.
- **Entradas:** Diagnóstico de drivers del mes y catálogo de palancas aplicables.
- **Procesamiento:** Simulación batch de palancas aplicables, ordenación por ratio impacto/esfuerzo y anclaje estricto al driver que motivó la caída de score.
- **Salidas:** Lista priorizada de recomendaciones con delta de score y euros auditados.
- **Excepciones y Errores:** Empresa en solvencia óptima (score > 85): recomendaciones orientadas a optimización de excedentes de tesorería.
- **Principio SOLID:** "El agente no opina, simula". Ninguna cifra procede de alucinaciones de modelos de lenguaje.

### REQ-B10.2: Generación Autónoma de Artefactos Transaccionales en 1 Clic (Factor WOW)
- **Descripción:** Convertir la simulación abstracta en documentos y comunicaciones ejecutables inmediatas para el director financiero.
- **Prioridad:** P2 (Factor WOW)
- **Dependencias:** REQ-B10.1, REQ-B7.1 (`POST /action/generate`).
- **Entradas:** Palanca seleccionada, contrapartes afectadas, importes de simulación validados.
- **Procesamiento:** Generación determinista de:
  - Propuesta formal de pronto pago a clientes morosos con tasa de descuento calculada por debajo del coste de la línea de crédito.
  - Memorando ejecutivo de novación o ampliación de póliza para el comité de riesgos del banco con los ratios DSCR proxy calculados.
- **Salidas:** Objeto JSON con tipo de documento, destinatario, asunto y cuerpo formal redactado listo para envío.
- **Excepciones y Errores:** Datos incompletos de contraparte: plantilla genérica con campos resaltados para completado manual.

---

## 12. Módulo B11 · Interfaz Navegable, Time-Machine y Pasaporte Móvil QR

### REQ-B11.1: Vista Comparativa Split-Screen (Time-Machine de 24 Meses)
- **Descripción:** Implementar una pantalla interactiva de contraste temporal entre Northbrook Foods (45 $\to$ 65) y Velasco Industrial (82 $\to$ 68).
- **Prioridad:** P0
- **Dependencias:** REQ-B7.1.
- **Entradas:** Series de 24 meses de ambas empresas.
- **Procesamiento:**
  - *Modo Bureau Tradicional:* Muestra solo la foto fija del mes 24 (65 vs 68), evidenciando la trampa contable.
  - *Modo Embat X-Ray:* Despliega la trayectoria completa y destaca la alerta temprana en el mes 18 en Velasco.
- **Salidas:** Gráfico interactivo coordinado con resaltado del momento de anticipación.
- **Excepciones y Errores:** Dispositivo sin aceleración gráfica: renderizado SVG estático alternativo.

### REQ-B11.2: Pasaporte de Solvencia Móvil en Vivo mediante Código QR
- **Descripción:** Exponer una vista web responsive de alto rendimiento accesible por código QR para que el jurado la consulte en sus teléfonos durante el pitch.
- **Prioridad:** P0 (Factor WOW)
- **Dependencias:** REQ-B7.1 (`GET /passport/{token}`).
- **Entradas:** Token de verificación seguro.
- **Procesamiento:** Carga ultrarrápida (<1s) de la ficha ejecutiva de solvencia de la empresa, trayectoria auditada, percentil sectorial y sello de verificación criptográfica de Embat.
- **Salidas:** Interfaz móvil optimizada en paleta Embat (`#050B2C`) sin requerir login ni descargas.
- **Excepciones y Errores:** Enlace caducado o token corrupto: pantalla explicativa con opción de visualización en modo demo.

---

## 13. Módulo B12 · Narrativa, Pitch y Tesis de Negocio

### REQ-B12.1: Estructura Cronometrada del Pitch de 2:30 Minutos
- **Descripción:** Alinear la presentación oral con los criterios de evaluación de K Fund y Embat siguiendo el minutaje estricto.
- **Prioridad:** P0
- **Dependencias:** REQ-B11.1, REQ-B11.2, REQ-B10.2.
- **Entradas:** Guion técnico ensayado y validado.
- **Procesamiento:**
  - 0:00–0:35: Gancho con la Time-Machine (Northbrook vs Velasco en mes 24).
  - 0:35–1:10: Motor causal, ortogonalidad y anticipación de 8 meses con control de falsas alarmas.
  - 1:10–1:45: Simulador what-if y ejecución autónoma en 1 clic.
  - 1:45–2:15: Proyección del QR y consulta en el móvil del jurado del Pasaporte de Solvencia.
  - 2:15–2:30: Tesis de negocio: *Workflow ownership earns transaction ownership*.
- **Salidas:** Presentación validada y vídeo de contingencia grabado.
- **Excepciones y Errores:** Corte de red o fallo de proyección: cambio instantáneo al soporte en local o vídeo offline.

---

## 14. Módulo B13 · Protocolo y Entrega al Leaderboard

### REQ-B13.1: Protocolo de Evaluación y Envío al Leaderboard
- **Descripción:** Generar las predicciones sobre el conjunto de test oculto asegurando reproducibilidad y respetando la regla de parada para evitar sobreajuste.
- **Prioridad:** P0
- **Dependencias:** REQ-B3.1.
- **Entradas:** Dataset de test provisto por Embat (60–80 empresas).
- **Procesamiento:**
  - Envío 1: Baseline con $k=0$ para medir nivel puro.
  - Envío 2: Inclusión del vector de momentum $\lambda M_t$ para medir ganancia de trayectoria.
  - Regla de parada: No superar 5–6 envíos. Mejoras de validación cruzada inferiores a 0,005 no se consideran significativas.
- **Salidas:** Fichero de predicciones en el formato exigido por el script de scoring de Embat.
- **Excepciones y Errores:** Formato de salida discrepante con el script evaluador: validación mediante script de comprobación pre-envío.

---

## 15. Requisitos No Funcionales (RNF)

| ID | Categoría | Requisito y Criterio de Verificación | Prioridad |
| :--- | :--- | :--- | :---: |
| **RNF-1** | **Determinismo** | Cero aleatoriedad en el pipeline de scoring y simulación. Semillas fijadas a nivel de sistema. Mismo input genera exactamente la misma salida matemática ($100\%$ de reproducibilidad). | P0 |
| **RNF-2** | **Rendimiento** | Latencia de cálculo de `/score` y `/simulate` inferior a 1.000 ms en ejecución normal, e inferior a 50 ms en modo demo/fixture. | P0 |
| **RNF-3** | **Robustez** | Disponibilidad de modo offline completo (`FixtureOffline`) y modo demo para asegurar operatividad absoluta durante la presentación sin depender de la WiFi del evento. | P0 |
| **RNF-4** | **Auditabilidad** | Toda cifra presentada en pantalla o en el pasaporte es trazable matemáticamente a través del waterfall exacto hasta una fila contabilizada del dataset. | P0 |
| **RNF-5** | **Modularidad SOLID** | Aislamiento por capas verticales y cumplimiento de los 5 principios SOLID: desacoplamiento de I/O, extensibilidad de palancas por Strategy, sustituibilidad en productos y segregación de interfaces API. | P0 |
| **RNF-6** | **Seguridad** | Ningún dato de credenciales bancarias o claves de API expuesto en frontend. Acceso al pasaporte financiero mediante token no enumerable con expiración. | P1 |

---

## 16. Matriz de Trazabilidad Integral

| Entregable Oficial del Reto | Estado en el Proyecto | Bloques y Requisitos que lo Satisfacen | Artefacto de Código / Implementación |
| :--- | :---: | :--- | :--- |
| **Predicción sobre el test oculto** | **Obligatorio** | REQ-B2.2, REQ-B3.1, REQ-B13.1 | `algorythm/calc_score.py`<br>`algorythm/engine_results/` |
| **Señal en las dos direcciones** | **Obligatorio** | REQ-B3.2, REQ-B3.3, REQ-B13.1 | `algorythm/score_engine.py` (`bounded_momentum`) |
| **Trayectoria, no foto fija** | **Obligatorio** | REQ-B3.1, REQ-B3.2, REQ-B11.1 | `algorythm/score_engine.py`<br>`algorythm/formula/score_financiero.pdf` |
| **Explicabilidad sin cajas negras** | **Obligatorio** | REQ-B4.1, REQ-B4.2 | `algorythm/score_engine.py` (descomposición aditiva) |
| **Producto encima del score** | **Obligatorio** | REQ-B8.1, REQ-B9.1, REQ-B10.1, REQ-B10.2 | `Simulador`, `PuenteEuros`, `Agente` |
| **Comprador identificado (Embat)** | **Obligatorio** | REQ-B12.1 | `PRODUCTO.md` §2, `factorwow.md` |
| **Demo navegable en vivo** | **Obligatorio** | REQ-B11.1, REQ-B11.2 | `Frontend Next.js / API FastAPI` |
| **Anticipación medida en meses** | **Bonus** | REQ-B5.1 | `algorythm/validate_score.py` (8 meses medidos) |
| **Monitor proactivo de alertas** | **Bonus** | REQ-B5.2, REQ-B5.3 | `Monitor`, integración Exa API (`exa-py`) |
| **Ejecución transaccional en 1 clic** | **Factor WOW** | REQ-B10.2, REQ-B7.1 | `POST /action/generate` (artefactos de cobro y deuda) |
| **Pasaporte Financiero Móvil por QR** | **Factor WOW** | REQ-B11.2, REQ-B7.1 | `GET /passport/{token}` (vista responsive jurado) |
