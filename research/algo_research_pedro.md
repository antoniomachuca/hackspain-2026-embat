# Brief del algoritmo: score de salud financiera con tesorería sintética

**Reto:** X Ray (Embat) · HackSpain 2026 · 18–20 sep, ETSIT UPM
**Alcance de este documento:** solo el algoritmo. El producto que se monta encima se decide después.
**Última actualización:** 2026-09-18

> **Cómo leer este documento.** Las secciones 1 a 3 explican el problema y la idea en lenguaje llano. Las secciones 4 a 9 son el algoritmo paso a paso. La 10 es el plan de trabajo. La 11 lista lo que sigue abierto y la 12 lo que se descartó. Los números marcados como **hipótesis** no salen de ningún dato: son apuestas razonables, y hay que decirlo así en el pitch.

---

## 1. El problema en 60 segundos

Una empresa deja un rastro: entra dinero, se emiten y se reciben facturas, se paga a proveedores, se cobra a clientes, se pide y se devuelve deuda. Casi nadie lee ese rastro; se miran fotos fijas (cuentas que llegan tarde, ratings que se actualizan de vez en cuando).

**Lo que hay que construir:** un sistema que lea ese rastro y, para cada empresa y cada mes, diga:

1. **Cómo de sana está** (nivel).
2. **Hacia dónde va** (tendencia).
3. **Por qué** tiene ese número y **qué lo movió** desde el mes pasado.
4. **Cuántos meses antes** vio venir un cambio.

El reto insiste en cuatro ideas que condicionan todo el diseño:

- **Dos caras.** Reconocer la mejora igual que el deterioro. Una empresa que pasa de 45 a 65 puede ser mejor apuesta que una que pasa de 82 a 68.
- **Trayectoria, no foto.** La salida refleja dirección, no solo el último mes.
- **Bache vs. caída.** Un mes malo de caja no es un deterioro estructural.
- **Test oculto.** Entre 60 y 80 empresas sin resultado que el sistema no ve nunca. Ahí se juega el leaderboard.

## 2. La restricción de fondo: no hay respuestas correctas

Tenemos los datos (el "examen") pero **no las respuestas** (quién acabó bien o mal). Consecuencias:

- No se puede entrenar un modelo para "adivinar impagos": no tiene contra qué aprender.
- Cualquier modelo que aprenda de una etiqueta construida con las mismas variables de entrada solo aprende **la regla que le pusimos** (circularidad).
- Por eso la base del sistema son **reglas claras y auditables**, no una caja negra. El propio reto lo premia: "un modelo sencillo con un producto claro encima interesa más que uno sofisticado".

**Hipótesis de trabajo sobre el leaderboard:** Embat nos comparará contra su propio score de salud, o contra una etiqueta plantada en el generador de datos. No lo sabemos. Por eso el objetivo es construir **el mejor score posible según cómo lo juzgaría un tesorero**, no optimizar a ciegas.

## 3. Vocabulario mínimo de tesorería

| Palabra | Qué es | Analogía |
|---|---|---|
| **Tesorería** | El dinero que entra y sale | Tu paga y tus gastos |
| **Factura emitida (AR)** | Yo vendí y me deben pagar | Prestaste 10 € a un amigo |
| **Factura recibida (AP)** | Compré y debo pagar | Un amigo te prestó 10 € |
| **Vencimiento** | Fecha límite de pago | "Me lo devuelves el viernes" |
| **Retraso / DBT** | Días de retraso sobre el vencimiento, ponderados por importe | Llegar 2 meses tarde en 50.000 € pesa más que en 100 € |
| **DSO / DPO** | Días que tarda en cobrar / en pagar | Tu velocidad para cobrar y para pagar |
| **Runway** | Meses que aguantaría sin ingresos con lo que tiene | Cuánto dura tu paga si no entra más |
| **Línea de crédito** | Tarjeta con límite | Tu tarjeta de crédito |
| **Utilización** | % del límite que ya has usado | Has gastado 800 de 1.000 € |
| **DSCR** | Veces que lo que gana cubre sus cuotas de deuda | Ganas 120 y pagas 100: 1,2 (justo) |
| **Factoring** | Vender facturas pendientes con descuento para cobrar ya | Vender un pagaré porque necesitas dinero hoy |
| **HHI** | Mide si las ventas están repartidas o concentradas | Si tu único cliente es un bar y cierra, cierras tú |
| **Peer group** | Empresas parecidas con las que comparar | Compañeros de tu clase |
| **Percentil** | Posición dentro del peer group (P90 = mejor que el 90 %) | "Estoy en el top 10 %" |

## 4. Visión general del algoritmo

```
CSV (companies, transactions, invoices, debt_*, balances)
                    │
                    ▼
     Features mensuales por empresa (ventana móvil de 12 meses)
       Liquidez │ Conducta de pago │ Deuda │ Concentración
                    │
                    ▼
     Percentil contra el peer group (tablas congeladas con train)
                    │
                    ▼
     NIVEL N(t) 0–100  ──►  TENDENCIA T(t)  ──►  ESTADO
                    │
                    ▼
     Score(t) = mezcla de nivel y trayectoria
                    │
        ┌───────────┼─────────────┐
        ▼           ▼             ▼
   Explicación   Validación   Anticipación medida
   (por qué)     propia       + monitor que avisa
```

**Analogía:** el score es como el boletín de un alumno a lo largo del curso. No solo importa la nota de hoy (nivel), sino si viene subiendo o bajando (tendencia), y por qué (qué asignatura ha cambiado).

## 5. Supuestos por defecto (mientras no haya respuesta de la organización)

| Duda | Supuesto de trabajo | Si resulta falso |
|---|---|---|
| Qué mide el leaderboard | Un score continuo de salud, comparado por correlación de rangos | Si es una banda o un evento, se binariza el score (una línea de código) |
| Qué formato de salida acepta | Serie mensual por empresa | Se exporta el último mes |
| Unidad de trabajo: 250 vs 1.286 | Se trabaja a nivel empresa (`company_id`) | Solo cambia el conteo. El reto habla de "250 empresas" pero el dataset describe 1.286 empresas en 250 grupos |
| Tamaño y unidad del test | 60–80 empresas | A confirmar (¿empresas o grupos?) |

**Preguntas para los ingenieros del aula (30 segundos cada una):**
1. ¿Qué compara exactamente el leaderboard: score continuo, ranking, dirección de cambio o evento?
2. ¿250 empresas o 1.286 empresas en 250 grupos? ¿El test son 60–80 empresas o grupos?
3. ¿El script de scoring recibe un número por empresa, una serie mensual, o ambas?

## 6. El algoritmo paso a paso

### 6.1 Exploración de datos (primera hora)

Un script corto que responda antes de programar nada:

- ¿Qué % de contrapartes de `transactions` e `invoices` cruza con algún `company_id`?
- ¿Cuántos países, monedas y ERPs hay?
- ¿Qué % de empresas tiene línea de crédito, factoring o avales?
- ¿Cuántos movimientos por empresa y semana (mediana y percentil 10)?
- ¿Hay empresas con menos de 12 meses de historia?

**Reglas de decisión ya fijadas:**

| Resultado | Decisión |
|---|---|
| Cruce contraparte↔empresa < 20 % | Sin grafo. Concentración solo con HHI de contrapartes |
| Menos de 5 países | Peer = país × tamaño |
| Más de 8 países | Peer = región × tamaño |
| Mediana de movimientos/semana < 5 | Serie mensual |
| < 30 % de empresas con línea | El bloque de deuda pesa menos en utilización |

### 6.2 La serie: ventana móvil de 12 meses

El score se calcula **cada mes t** con los 12 meses anteriores. Eso da unos 13 puntos por empresa (del mes 12 al 24). Para los meses 1–11 se usa una ventana creciente (mínimo 6 meses) marcada con menor confianza.

### 6.3 El nivel N(t): cuatro asignaturas

Cada asignatura es un promedio de percentiles. **Mayor = más sano.** Se invierten las variables donde "más = peor" (HHI, retraso, utilización).

**Liquidez (30 %)** ¿Le sobra dinero o va justo?

| Feature | Peso interno |
|---|---|
| Runway (saldo / salida neta media mensual) | 35 % |
| Flujo neto medio 12 m / ingresos medios | 30 % |
| Meses con flujo negativo (invertido) | 20 % |
| Volatilidad del flujo, normalizada por ingresos (invertida) | 15 % |

**Conducta de pago (30 %)** ¿Paga y cobra a tiempo? Es la señal más difícil de maquillar.

| Feature | Peso interno |
|---|---|
| DBT como pagador (facturas recibidas, ponderado por importe) | 30 % |
| % de emitidas vencidas y sin cobrar | 25 % |
| Retraso medio de cobro sobre vencimiento | 20 % |
| Gap DSO − DPO | 15 % |
| % de facturas pagadas tarde | 10 % |

Regla clave: facturas **recibidas** (la empresa paga) y **emitidas** (la empresa cobra) se puntúan por separado; nunca se mezclan en un solo número. Un DPO alto no se penaliza si paga a plazo: se penaliza el retraso real sobre el vencimiento.

**Deuda (25 %)** ¿Puede pagar sus cuotas con lo que gana?

| Feature | Peso interno |
|---|---|
| DSCR proxy | 40 % |
| Utilización de líneas (0 si no hay línea, sin penalizar) | 25 % |
| Deuda total / ingresos anualizados | 20 % |
| Factoring y confirming sobre ingresos | 15 % |

Cálculo del DSCR proxy, en simple:

1. Numerador: suma de 12 meses de cobros operativos menos pagos operativos. Se excluyen financiación, movimientos intragrupo e inyecciones de capital. No se restan las cuotas.
2. Denominador: lo que tiene que pagar al año por su deuda: la cuota del cuadro de amortización para préstamos, hipotecas y leasing; solo intereses sobre lo dispuesto para líneas de crédito; el coste (fee) del factoring; y cero para los avales (que cuentan como deuda ajustada, no como servicio).
3. DSCR = numerador / denominador. Referencia: ≥ 1,5 holgado; 1,25–1,5 correcto; 1,0–1,25 justo; < 1,0 no llega.

**Concentración (15 %)** ¿Depende de pocos clientes o proveedores?

| Feature | Peso interno |
|---|---|
| HHI de clientes (invertido) | 45 % |
| HHI de proveedores (invertido) | 30 % |
| % de ingresos de contrapartes recurrentes | 25 % |

Alarma: un solo cliente por encima del 35–40 % de los ingresos.

**Nivel final:** `N = 0,30·Liquidez + 0,30·Pago + 0,25·Deuda + 0,15·Concentración`, escalado a 0–100.

> **Hipótesis.** Los pesos 30/30/25/15 y los pesos internos son apuestas razonables, no resultados estimados. Se afinan con el leaderboard (ver 6.7).

### 6.4 Peer groups y generalización a empresas nuevas

**Por qué:** una peluquería y una constructora no son comparables. Se compara cada empresa con las de su país y tamaño.

**Receta:** peer = país × cuartil de ingresos anualizados.

| Empresas en el peer | Qué se hace |
|---|---|
| ≥ 30 | Percentil local |
| 15–29 | Mezcla de local y global (*shrinkage*) |
| 5–14 | Casi todo global y etiqueta "peer limitado" |
| < 5 | Solo global |

El *shrinkage* es `p = w·p_local + (1−w)·p_global`, con `w = n/(n+K)` y K la mediana del tamaño de los peers. Analogía: si solo preguntas a 3 personas quién cocina mejor del barrio, no te fías; miras también la fama de toda la ciudad.

**Clave para el test oculto: tablas congeladas.**
- Los percentiles se calculan **solo con las empresas de entrenamiento** y se guardan como tablas de deciles por peer y feature.
- Una empresa nueva se coloca contra esas tablas. **Nunca se recalculan** con ella dentro; si no, cada empresa nueva mueve las referencias de todas las demás.
- Sin sector inferido en la primera versión. Solo se añade si sobra tiempo y mejora el leaderboard.

### 6.5 La tendencia T(t) y los estados

**Método:** regresión lineal sobre N(t) de los últimos 6 meses. La pendiente es T(t), en puntos por mes. Se usa regresión en lugar de restar dos meses porque usa los 6 puntos y aguanta un mes atípico. Después se toma la **mediana de las tres últimas pendientes** para que un mes suelto no cambie el signo.

**Estados** (todos los umbrales son **hipótesis**):

| Estado | Condición |
|---|---|
| **Mejorando** | T > +1,0 pt/mes durante ≥ 3 meses seguidos |
| **Estable** | \|T\| ≤ 1,0 |
| **Torciéndose** | T < −1,0 durante ≥ 3 meses **y** N ≥ 60 (aún parece sana) |
| **Deterioro** | T < −1,0 durante ≥ 3 meses **y** N < 60 |
| **Bache** | Caída de N ≥ 8 puntos en un mes y recuperación ≥ 60 % en ≤ 2 meses |
| **Recuperación** | Salió de Deterioro y T > +1,0 durante ≥ 2 meses |

**Cómo separa bache y caída:** exige **persistencia**. Con 24 meses, tres meses seguidos es el mínimo defendible para distinguir ruido de tendencia. "Torciéndose" es la señal más vendible: es el caso 82→68 del reto, que nadie más ve.

### 6.6 El score final (60 % nivel, 40 % trayectoria)

```
N_trayectoria(t) = N(t) + k · T(t)          (k = 3: extrapola 3 meses)
Score(t)         = 0,6 · N(t) + 0,4 · N_trayectoria(t)
```

Ejemplos: una empresa en 82 cayendo 4 pts/mes queda cerca de 77; una en 45 subiendo 4 pts/mes sube cerca de 50. El nivel domina, pero la dirección desplaza el resultado. El reto dice que ningún bloque pesa más que otro, así que **N(t) y T(t) se exportan también por separado**.

### 6.7 Cómo se afina sin sobreajustar

- **Primer envío al leaderboard con k = 0** (solo nivel): da una línea base limpia. La tendencia entra como variante 2, y así se sabe cuánto aporta en vez de asumirlo.
- **Máximo 5–6 variantes** contra el test oculto. Más iteraciones y se acaba optimizando para esas 60–80 empresas.
- Cada variante debe tener una justificación, no ser una búsqueda a ciegas.

## 7. Explicación

**Por qué saca este número:** códigos de razón ordenados por `peso_bloque × (percentil − 50)`.

| Código | Condición | Mensaje |
|---|---|---|
| RC-01 | Runway P < 25 o racha ≥ 3 meses de flujo negativo | Flujo insuficiente |
| RC-02 | DSO P > 75 o % de vencidas alto | Deterioro de cobros frente a sus peers |
| RC-03 | DSCR P < 30 o línea P > 80 | Carga financiera o líneas al límite |
| RC-04 | HHI P > 80 o cliente principal > 35 % | Concentración de ingresos |
| RC-05 | Historia < 12 meses o conciliación < 80 % | Confianza limitada en el dato |

**Por qué ha cambiado desde el mes pasado:** como el score es una suma ponderada, la variación se descompone de forma exacta por bloque:

```
ΔS = Σ_b  w_b · (P_b(t) − P_b(t−1))
```

Después se baja un nivel: dentro del bloque que más movió, se muestran las 2 features con mayor contribución. Salida tipo:

> *"Score −6 frente al mes anterior: conducta de pago −5 (DBT de 4 a 19 días; 3 facturas recibidas pagadas con más de 30 días de retraso), liquidez −1."*

No se usa SHAP ni LIME: sobre un score aditivo, la explicación **es** el modelo.

## 8. Confianza del dato (separada del riesgo)

Son dos preguntas distintas: ¿está la empresa en apuros? y ¿me fío de los datos que tengo? Una empresa con 6 meses de historia parece arriesgada solo por falta de información. Por eso la confianza es una capa aparte y **no entra en el score**.

```
confianza = 0,30·%conciliado + 0,25·meses/24 + 0,20·cobertura_productos
          + 0,15·match_factura_banco + 0,10·(1 − sensibilidad)
```

Semáforo: **alta** (≥ 18 meses y ≥ 90 % conciliado), **media** (12–17 meses o 70–89 %), **baja** (< 12 meses o < 70 %). Los nulos se imputan con la mediana del peer y el marcador de "dato faltante" baja la confianza, no sube el riesgo.

## 9. Validación propia y anticipación

### Validación (además del leaderboard)

| # | Prueba | Cómo | Pasa si |
|---|---|---|---|
| 1 | Backtest temporal | Score en el mes 18 frente al evento de estrés (ELMS) de los meses 19–24 | Correlación de rangos positiva. Es un sanity check, no la métrica de éxito |
| 2 | Estabilidad | Correlación de rangos entre el score de un mes y el siguiente | > 0,85. Si baja, hay ruido en las features |
| 3 | Simetría | Las empresas que el dato muestra mejorando deben subir su N | Sí, y con la misma facilidad que las que caen |
| 4 | Sensibilidad | Mover cada peso ±10 puntos y recalcular el ranking | Correlación de rangos > 0,9 |

**ELMS (evento de estrés, solo para validar, nunca para entrenar).** Baseline = mediana de los meses 1–18. Se activa si se cumplen **al menos 2 de 3** pilares: caja (flujo operativo negativo ≥ 2 meses seguidos), cobros (el DSO sube ≥ 20 % durante ≥ 2 meses, o vencidas ≥ 15 % y +5 pp) y líneas (utilización ≥ 80 % durante ≥ 2 meses). Se define **antes** de mirar resultados.

### Anticipación medida (bonus)

No hay eventos etiquetados, así que se construyen con cambios de régimen en las series crudas: el mes en que el flujo neto o el retraso de cobro rompen su patrón (CUSUM sobre el residuo interanual).

```
Anticipación = mes del cambio en la serie cruda − mes en que el estado pasa a "Torciéndose" o "Deterioro"
```

Es una medida honesta de cuántos meses antes ve el sistema lo que las series confirman después.

### Monitor que avisa (bonus)

Una lista que se actualiza sola con las empresas cuyo estado cambia a "Torciéndose", "Deterioro" o "Mejorando" en el último mes, ordenada por tamaño del cambio.

## 10. Plan de trabajo

| Fase | Contenido | Tiempo | Bloquea demo |
|---|---|---|---|
| 1 | Exploración + reglas de decisión de 6.1 | 1 h | Sí |
| 2 | Features de los 4 bloques (mensuales, ventana móvil) | 5–6 h | Sí |
| 3 | Percentiles congelados por peer + nivel | 2–3 h | Sí |
| 4 | Tendencia + estados | 2 h | Sí |
| 5 | Explicación (códigos + delta) | 2 h | Sí |
| 6 | Validación propia + primer envío al leaderboard (k = 0) | 2 h | Sí |
| 7 | Iteración de pesos con feedback (máx. 5–6 variantes) | 3 h | No |
| 8 | Anticipación medida + monitor que avisa | 2 h | Bonus |
| 9 | ML de ajuste de pesos (solo si sobra) | 3 h | No |

**Reparto sugerido si el tiempo aprieta:** fases 1, 2, 3, 6 y 4 primero. Sin el motor de nivel, todo lo demás no sirve.

### ML opcional, con guardarraíl

**Base = reglas.** Son la entrega. El ML solo entra como mejora, para **reajustar los pesos internos**, no para sustituir las reglas.

- **Target sin circularidad:** predecir el flujo neto de caja de los meses t+1 a t+3 (relativo al ingreso), usando solo features de conducta de pago y deuda hasta t.
- **Modelo:** regresión ridge con validación cruzada agrupada por `group_id`.
- **Test de aceptación:** sustituye a las reglas solo si mejora la correlación de rangos con el flujo futuro en un corte temporal no visto **y** el resultado en el leaderboard. Si no pasa las dos, se queda la versión de reglas.

## 11. Riesgos y decisiones abiertas

| Riesgo | Mitigación |
|---|---|
| Pesos y umbrales son hipótesis | Máx. 5–6 variantes contra el test oculto; cada una justificada |
| El 60/40 es una apuesta sobre lo que mide Embat | Enviar antes la variante k = 0 y comparar |
| Ventana de 12 meses en 24 de historia deja pocos puntos de serie | Si la estabilidad sale baja, bajar a ventana de 9 |
| Circularidad del ML (el flujo futuro se parece a liquidez) | ML solo opcional y con test de aceptación |
| Dato sintético: si el generador plantó patrones simples, el score parecerá mejor de lo real | Decirlo en el pitch; no afirmar leyes de impago |
| Contrapartes que no cruzan con `company_id` | Reglas de 6.1; no fingir grafo |
| El score de Embat podría medir otra cosa (riesgo de crédito, liquidez, actividad) | Preguntar y mirar cómo responde el leaderboard a cada bloque |

**Decisiones abiertas:** las tres preguntas de la sección 5, y si el número principal del leaderboard es el nivel, la tendencia o la mezcla 60/40.

## 12. Fuera del núcleo (solo si sobra tiempo)

El reto no los pide; son diferenciadores potenciales, no obligaciones.

- **Módulo de grupo:** score del grupo = 65 % media ponderada + 35 % peor filial, con penalización por contagio si una filial material está en mala situación. Antes de agregar, se eliminan flujos y facturas intragrupo.
- **Grafo de contrapartes:** HHI, anclas, DebtRank lineal. Solo si el cruce contraparte↔empresa es alto.
- **Ajuste por moneda:** flujos a tipo medio mensual del BCE, saldos a tipo de cierre.
- **CUSUM y detección de cambios de régimen** más allá de la anticipación medida.
- **Sector inferido** desde categorías de `transactions`.

**Descartado con razón (no dedicar tiempo):**

| Técnica | Por qué no |
|---|---|
| ML supervisado sobre el proxy (XGBoost, etc.) | Circularidad: aprendería la propia regla |
| PU learning, Snorkel end-to-end | Inventan la probabilidad de la clase positiva |
| Altman Z, Merton, RiskCalc | Exigen balances contables o precios de mercado |
| Isolation Forest, LSTM, HMM como núcleo | 24 puntos por empresa son demasiado pocos |
| SHAP / LIME | El score es aditivo, la explicación ya es exacta |
| WOE / IV | Requieren etiqueta |
| PD calibrada y Gini "como precisión" | No hay etiqueta real |

---

## Apéndice A: mensaje de producto para el pitch (versión algoritmo)

> No estimamos probabilidad de impago: ordenamos **salud financiera** con cuatro bloques ponderados de forma explícita (liquidez, conducta de pago, deuda, concentración), comparados con empresas parecidas. Para cada empresa y mes damos **nivel, tendencia y estado**, y sabemos decir **por qué ha cambiado**. Separamos un bache de un deterioro exigiendo persistencia, y medimos **cuántos meses antes** ve el sistema un cambio. Los pesos son hipótesis declaradas y se han sometido a análisis de sensibilidad. El dato es sintético: el score mide coherencia interna, no leyes de impago del mundo real.

## Apéndice B: referencias principales

- D&B PAYDEX (conducta de pago ponderada por importe): https://www.dnb.com/content/dam/web/data-and-ai/cross/content/paydex-score-factsheet/DnB_Paydex_Score_Factsheet.pdf
- Petersen & Rajan (1997), crédito comercial: https://doi.org/10.1093/rfs/10.3.661
- Ma et al., retrasos de pago y quiebra (NBER w25553): https://doi.org/10.3386/w25553
- Jiménez et al. (2010), uso de líneas de crédito como señal temprana: https://ideas.repec.org/a/oup/rfinst/v23y2010i10p3665-3699.html
- Gelman & Hill, cap. 12 (partial pooling / *shrinkage*): https://spia.uga.edu/faculty_pages/tyler.scott/teaching/PADP8130_Spring2017/readings/gelman.hill.2007.ch12.pdf
- OECD, Handbook on Composite Indicators (pesos y sensibilidad): https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf
- Plaid y Codat (métricas de underwriting por cash-flow): https://plaid.com/docs/underwriting/ · https://docs.codat.io/lending/premium-products/credit-model-overview