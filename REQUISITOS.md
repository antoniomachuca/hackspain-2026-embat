# Requisitos del proyecto · por bloques de arquitectura

**Qué es esto:** la especificación ejecutable del sistema, bloque a bloque. Cada bloque
tiene dueño, contrato de entrada/salida, requisitos numerados y criterios de aceptación
comprobables.
**Qué NO es:** ni la investigación del algoritmo (vive en
[`research/algo_research_pedro.md`](research/algo_research_pedro.md)) ni la tesis de
producto (vive en [`PRODUCTO.md`](PRODUCTO.md)). Este documento los traduce a requisitos.

**Jerarquía ante conflicto:** `ENUNCIADOTRACK.md` → `PRODUCTO.md` (producto, comprador,
narrativa) → `algo_research_pedro.md` (algoritmo) → este documento (cómo se comprueba).
**Última actualización:** 2026-09-18 (rev. 2, tras la exploración del dataset — ver
[`research/informe_exploracion.md`](research/informe_exploracion.md))

---

## 0. Convenciones

**Identificadores.** `RF-Bn.m` requisito funcional del bloque n · `RNF-n` requisito no
funcional · `CA` criterio de aceptación.

**Prioridad.**

| Nivel | Significado | Regla de corte |
| :--- | :--- | :--- |
| **P0** | Sin esto no hay demo ni entrega | No se toca nada de P1 hasta que todo P0 esté verde |
| **P1** | Obligatorio del enunciado §6, pero la demo se sostiene sin ello unas horas | Se entrega sábado noche |
| **P2** | Bonus del enunciado o diferenciador de `PRODUCTO.md` §4 | Solo si P0 y P1 están cerrados |

**Estado de un requisito:** `pendiente` → `mockeado` (devuelve datos falsos contra el
contrato) → `hecho` (pasa su CA).

**Regla de desbloqueo (la más importante del fin de semana).** Todo bloque consumidor
arranca contra el **mock** del contrato congelado, nunca contra la implementación real.
Ningún bloque puede declararse bloqueado por otro: si su dependencia no está, mockea.

**Mapa de bloques.**

```
B0 Datos ──► B1 Features ──► B2 Peer/percentiles ──► B3 Score ──┬──► B4 Explicación
                                                                 ├──► B5 Anticipación+Monitor
                                                                 └──► B6 Grupo
                                                                        │
                       B7 API (contrato) ◄──────────────────────────────┘
                              │
                              ├──► B8 Simulador (palancas) ──► B9 Puente a euros
                              │            │
                              │            └──► B10 Agente
                              │                      │
                              └──────────────────────┴──► B11 Front/Demo ──► B12 Pitch
                                                          B13 Entrega leaderboard
```

**Dueños** (de `PRODUCTO.md` §5): Carlos B0–B2 y B13 · Antonio B3, B7, B9 · Pedro B5, B8,
B10 · Quirce B10–B11 · Hugo B11–B12. B4 y B6 son compartidos (Antonio fórmula, Carlos datos).

---

## B0 · Ingesta y exploración del dato

**Dueño:** Carlos · **Prioridad:** P0 · **Bloquea:** todo · **Tiempo objetivo:** 1 h

**Entrada:** los nueve CSV/JSON del dataset (`groups`, `companies`, `banking_products`,
`debt_products`, `debt_schedule_config`, `transactions`, `invoices`, `balances`,
`data_dictionary.md`).
**Salida:** tablas cargadas y validadas + `research/informe_exploracion.md` con las
respuestas de `algo_research_pedro.md` §6.1 y las decisiones que disparan.

> **Estado: exploración hecha (18-sep).** Las decisiones de §6.1 ya están tomadas y
> escritas en el informe. Resumen: **sin target en train → reglas** · **peer por país
> descartado** (82 % nulo) → cuartil de tamaño · **sin grafo** (cruce contraparte↔empresa
> 0,0 %) · serie **mensual** (12,6 mov./semana) · **16 % con línea** → utilización pesa menos
> · **32 % de empresas con < 12 meses** · cuadro de amortización cubre el **7 %** de préstamos.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B0.1** | Cargar los nueve ficheros con tipos explícitos (fechas como fecha, importes como decimal) y dejar constancia de filas leídas por fichero | P0 |
| **RF-B0.2** | Validar integridad referencial: todo `company_id` de `transactions`, `invoices`, `balances` y `debt_*` existe en `companies`; todo `group_id` existe en `groups` | P0 |
| **RF-B0.3** | Responder las cinco preguntas de exploración: % de contrapartes que cruzan con `company_id`, nº de países/monedas/ERPs, % de empresas con línea/factoring/aval, movimientos por empresa y semana (mediana y P10), empresas con < 12 meses de historia | P0 |
| **RF-B0.4** | Disparar y **registrar por escrito** las cinco reglas de decisión de §6.1 (grafo sí/no, definición de peer, granularidad mensual, peso del bloque de deuda). **Hecho**: ver informe §1 | P0 |
| **RF-B0.5** | Resolver la unidad de trabajo: `company_id` (1.286) frente a `group_id` (250), y confirmar contra los ingenieros del aula qué unidad evalúa el test oculto | P0 |
| **RF-B0.6** | Calendario canónico de 24 meses (sep-2024 → sep-2026) compartido por todos los bloques; los meses sin movimiento existen con valor cero, no desaparecen | P0 |
| **RF-B0.7** | Normalizar signo de importes (entrada positiva / salida negativa) y documentar la convención una sola vez | P0 |
| **RF-B0.8** | Conversión a EUR de flujos y saldos en divisa distinta, con tipo documentado (EUR es el 89 %) | P2 |
| **RF-B0.9** | **Limpieza de fechas anómalas** en `invoices`: años imposibles (6913, 5026), pago anterior a emisión (29.089 filas), `paid` con pago posterior al 1-sep-2026 (3 %). Se marcan y se excluyen del cálculo de retrasos, nunca se corrigen a mano | P0 |
| **RF-B0.10** | **Reconstrucción del saldo histórico** de cuentas corrientes: `saldo_t = saldo_final − Σ movimientos posteriores a t`. Validar por cuenta (el 20 % toca negativo en algún mes) y agregar por empresa con marcador de calidad | P0 |

**CA-B0:** un comando reproduce la carga de cero y emite el informe. Dos personas distintas
obtienen los mismos conteos. Las decisiones de §6.1 están escritas y fechadas, no en la
cabeza de nadie.

**Resuelto:** el cruce contraparte↔`company_id` es **0,0 %**. No hay grafo; la
concentración se calcula con HHI sobre `invoices` (98,7 % con contraparte; los movimientos
bancarios solo tienen contraparte en el 9,8 %). No se revisita.

---

## B1 · Features del rastro

**Dueño:** Carlos · **Prioridad:** P0 · **Depende de:** B0 · **Tiempo objetivo:** 5–6 h

**Entrada:** tablas de B0.
**Salida:** tabla `features[company_id, mes, feature] → valor` con las ~16 features de los
cuatro bloques, más `meses_historia` y los insumos de confianza.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B1.0** | **Point-in-time (as-of).** Toda feature del mes *t* usa solo lo que se sabía en *t*. En facturas: viva si `issuance ≤ t` y (`status ≠ paid` **o** `payment_date > t`); vencida si además `due < t`. `payment_date` solo cuenta si `status == paid` y `issuance ≤ payment ≤ 2026-09-01` — en `overdue`/`pending` es un **placeholder igual al vencimiento** (96–98 %), no una fecha de pago. Mismo criterio para saldo de deuda y estado de conciliación | P0 |
| **RF-B1.1** | Ventana móvil de 12 meses por empresa y mes; con ventana creciente y mínimo de 6 meses cuando no hay historia suficiente, marcada con menor confianza. **No es un caso raro: el 32 % de las empresas tiene < 12 meses** y solo el 29 % tiene los 24 | P0 |
| **RF-B1.2** | **Liquidez:** runway (sobre el saldo reconstruido de RF-B0.10, agregado por empresa), flujo neto medio / ingresos medios, nº de meses con flujo negativo, volatilidad del flujo normalizada por ingresos | P0 |
| **RF-B1.3** | **Conducta de pago:** DBT como pagador ponderado por importe, % de emitidas vencidas sin cobrar, retraso medio de cobro sobre vencimiento, gap DSO−DPO, % de facturas pagadas tarde | P0 |
| **RF-B1.4** | **Deuda:** DSCR proxy, utilización de líneas, deuda total / ingresos anualizados, factoring y confirming sobre ingresos | P0 |
| **RF-B1.5** | **Concentración:** HHI de clientes, HHI de proveedores, % de ingresos de contrapartes recurrentes — **calculados sobre `invoices`**, no sobre movimientos bancarios | P0 |
| **RF-B1.6** | Facturas **emitidas** y **recibidas** se calculan por separado y nunca se agregan en un solo número. **La dirección la da el signo de `amount`** (negativa = recibida/pago, positiva = emitida/cobro; verificado al 99,6 % contra el movimiento bancario). 67 empresas no tienen emitidas en el ERP: su cobro se mide solo por banco | P0 |
| **RF-B1.7** | Un DPO alto no penaliza por sí mismo: solo penaliza el **retraso real sobre el vencimiento** | P0 |
| **RF-B1.8** | DSCR proxy: numerador = cobros − pagos operativos de 12 m excluyendo financiación, intragrupo e inyecciones de capital, sin restar cuotas; **denominador = servicio de deuda observado en banco** (movimientos `debt_repayment` + `interest_charge`, presentes en el 56 % de empresas), **no** el cuadro de amortización (`debt_schedule_config` cubre el 7 % de los préstamos). Sin movimientos de deuda ni producto de deuda → DSCR neutro, no penalizado (71 % de empresas sin deuda registrada) | P0 |
| **RF-B1.9** | Empresa sin línea de crédito: utilización **neutra**, nunca penalizada | P0 |
| **RF-B1.10** | Nulos imputados con la mediana del peer, con marcador de dato faltante que alimenta B3-confianza y **no** el riesgo | P0 |
| **RF-B1.11** | Cada feature declara su dirección (mayor = mejor / mayor = peor) en un único sitio, y la inversión se aplica una sola vez en todo el pipeline | P0 |
| **RF-B1.12** | El pipeline es **recomputable sobre un input modificado** (requisito duro de B8: el contrafactual reejecuta features, no deriva) | P0 |
| **RF-B1.13** | Eliminación **aproximada** de flujos intragrupo antes de agregar por grupo: por categoría `transfer` (5,9 % de movimientos) y préstamos `Other (customer-defined)`. Sin cruce de contrapartes no puede ser exacta, y se declara así | P1 |
| **RF-B1.15** | Toda feature de actividad se normaliza por la propia empresa (sus ingresos, su historia). El volumen total del dataset crece ×4 por **onboarding** (439 empresas activas en sep-2024 → 1.223 en mar-2026), no por negocio; ninguna feature absoluta es comparable entre meses | P0 |
| **RF-B1.14** | Insumos de confianza: % conciliado, meses de historia, cobertura de productos, match factura↔banco | P1 |

**CA-B1:** ninguna feature devuelve NaN o infinito para una empresa con ≥ 6 meses. Tres
empresas revisadas a mano cuadran con el cálculo. Recalcular sobre un input modificado en
un campo cambia solo las features afectadas. **Prueba as-of:** el DSO de un mes calculado
con el fichero completo coincide con el calculado truncando el fichero a ese mes.

---

## B2 · Peer groups y percentiles congelados

**Dueño:** Carlos · **Prioridad:** P0 · **Depende de:** B1 · **Tiempo objetivo:** 2–3 h

**Entrada:** `features`.
**Salida:** tablas de deciles por `(peer, feature)` **persistidas en disco**, y función
`percentil(feature, valor, peer) → [0,100]`.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B2.1** | Peer = **cuartil de tamaño** por cobros anualizados (~321 empresas por cuartil; rango 54 k€ – 614 M€). País **descartado**: 82 % nulo y sucio. Opcional: × moneda (EUR / otra) si mejora la estabilidad | P0 |
| **RF-B2.2** | Las tablas se calculan **solo con empresas de entrenamiento**, se serializan y se versionan. Una empresa nueva se coloca contra ellas; **jamás** se recalculan incluyéndola | P0 |
| **RF-B2.3** | *Shrinkage* por tamaño del peer: ≥30 local · 15–29 mezcla `w=n/(n+K)` · 5–14 casi global con etiqueta "peer limitado" · <5 solo global | P0 |
| **RF-B2.4** | Valor fuera del rango de la tabla: se satura en 0 o 100, nunca extrapola ni falla | P0 |
| **RF-B2.5** | Empresa sin cobros categorizados (31 en train) o de tamaño fuera de rango: cae a global con etiqueta "peer limitado" y baja de confianza | P0 |
| **RF-B2.6** | La salida expone `p_peer` por feature para que B4 la pinte y B7 la sirva | P0 |
| **RF-B2.7** | El benchmark sectorial anónimo del acto 3 (`PRODUCTO.md` §4) se construye sobre estas mismas tablas, sin exponer empresas individuales | P1 |

**CA-B2:** puntuar una empresa de test dos veces, sola y junto a otras 50, da **idéntico**
resultado. Esto es la prueba de que las tablas están congeladas y es el CA más importante
de todo el motor.

---

## B3 · Motor de score: nivel, tendencia, estado y confianza

**Dueño:** Antonio (fórmula) + Carlos (nivel) · **Prioridad:** P0 · **Depende de:** B2 · **Tiempo objetivo:** 2 h sobre B2

**Entrada:** percentiles por feature y mes.
**Salida:** por `(company_id, mes)`: `nivel`, `tendencia`, `estado`, `score`, `confianza`,
y la serie `trayectoria[24]`.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B3.1** | Nivel `N = 0,30·Liquidez + 0,30·Pago + 0,25·Deuda + 0,15·Concentración`, escalado a 0–100, con los pesos internos del brief §6.3 | P0 |
| **RF-B3.2** | Los pesos viven en **un fichero de configuración**, no incrustados en el código: B13 itera variantes sin tocar la lógica | P0 |
| **RF-B3.3** | Tendencia `T(t)` = regresión lineal sobre `N` de los 6 últimos meses, y luego **mediana de las 3 últimas pendientes**, en puntos/mes | P0 |
| **RF-B3.4** | Los seis estados de §6.5 con sus umbrales: Mejorando, Estable, Torciéndose, Deterioro, Bache, Recuperación. **Torciéndose** (T<−1 tres meses **y** N≥60) es la señal vendible del caso 82→68 | P0 |
| **RF-B3.5** | `Score(t) = 0,6·N(t) + 0,4·(N(t) + k·T(t))`, con `k` configurable y **k = 0 en el primer envío** | P0 |
| **RF-B3.6** | `nivel`, `tendencia` y `estado` se exportan **por separado** además del score compuesto: el enunciado no prioriza ninguno | P0 |
| **RF-B3.7** | Señal simétrica: la fórmula no contiene ningún término que trate la subida distinto de la bajada; se comprueba en B13-CA | P0 |
| **RF-B3.8** | `confianza = 0,30·%conciliado + 0,25·meses/24 + 0,20·cobertura + 0,15·match + 0,10·(1−sensibilidad)`, con semáforo alta/media/baja, y **fuera del score** | P1 |
| **RF-B3.9** | Bache y deterioro se separan por **persistencia** (≥3 meses), no por magnitud del mes suelto | P0 |
| **RF-B3.10** | **Un solo algoritmo**: el score de reglas es el que se envía al leaderboard y el que consume el producto. Si aparece una variante mejor, se sustituye entera; no conviven dos motores. **Resuelto 18-sep: el dataset no trae target**, así que la rama de reglas es la activa; GBDT solo si el script de scoring revela una etiqueta (RF-B13.2) | P0 |
| **RF-B3.11** | Si la estabilidad mes a mes sale por debajo de 0,85 o hay pocos puntos de serie, la ventana baja a 9 meses (brief §11). Con 12 meses hay 13 puntos de score por empresa y el primer estado confirmable cae en el mes ~15 | P1 |

**CA-B3:** Northbrook (45→65) y Velasco (82→68) —o sus equivalentes reales del dataset—
salen con estados `Mejorando` y `Torciéndose` respectivamente, y el sistema los distingue
aunque su score del mes 24 difiera en pocos puntos. La estabilidad mes a mes (correlación
de rangos) supera 0,85; si no, hay ruido en B1.

---

## B4 · Explicabilidad

**Dueño:** Antonio · **Prioridad:** P0 · **Depende de:** B3 · **Tiempo objetivo:** 2 h

**Entrada:** percentiles y score del mes t y t−1.
**Salida:** `drivers[{feature, contribución, valor, p_peer}]` + `códigos_razón[]` + frase
de delta en lenguaje natural.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B4.1** | **Por qué este número:** códigos de razón ordenados por `peso_bloque × (percentil − 50)`, con los cinco códigos RC-01…RC-05 del brief §7 | P0 |
| **RF-B4.2** | **Por qué ha cambiado:** descomposición exacta `ΔS = Σ_b w_b·(P_b(t) − P_b(t−1))`, que por construcción suma el delta total | P0 |
| **RF-B4.3** | Segundo nivel: dentro del bloque que más movió, las 2 features de mayor contribución, con su valor crudo en unidades de negocio (días, %, €) | P0 |
| **RF-B4.4** | Frase generada legible por un tesorero: *"Score −6: conducta de pago −5 (DBT de 4 a 19 días; 3 facturas recibidas pagadas con +30 días de retraso), liquidez −1"* | P0 |
| **RF-B4.5** | **Nada de SHAP, LIME ni beeswarm en pantalla.** Sobre el score aditivo de reglas la explicación *es* el modelo y no hace falta nada por debajo; si RF-B13.2 activara la rama GBDT, SHAP agrupado por bloque sería el único uso admitido, y siempre traducido a la lista de factores + frase de RF-B4.3/B4.4. Todo el research coincide: no SHAP crudo | P0 |
| **RF-B4.6** | Toda cifra que aparezca en pantalla es trazable a una feature y a una fila del dataset | P1 |

**CA-B4:** para cualquier empresa y mes, las contribuciones de los bloques suman el delta
del score con error < 0,01. Un miembro del equipo que no escribió el código lee la frase y
explica el caso al jurado sin ayuda.

---

## B5 · Anticipación medida y monitor proactivo

**Dueño:** Pedro · **Prioridad:** P1 (anticipación) / P2 (monitor) · **Depende de:** B3 · **Tiempo objetivo:** 2 h

**Entrada:** series crudas de B1 y estados de B3.
**Salida:** `meses_anticipación` por empresa y evento + lista de alertas ordenada.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B5.1** | Detección de cambio de régimen (CUSUM sobre el residuo interanual) en flujo neto y retraso de cobro, definida **antes** de mirar resultados | P1 |
| **RF-B5.2** | `Anticipación = mes del cambio en la serie cruda − mes en que el estado pasa a Torciéndose o Deterioro`, reportada como **mediana en meses** | P1 |
| **RF-B5.3** | **Control de falsas alarmas:** el lead time se reporta *a una tasa fijada* — "mediana de N meses a 1 alerta por empresa-año en las sanas". Sin fijar la tasa el número se infla trivialmente y el especialista de datos de Embat lo va a preguntar (`PRODUCTO.md` §4) | P1 |
| **RF-B5.4** | ELMS del brief §9 (2 de 3 pilares: caja, cobros, líneas) **solo para validar, nunca para entrenar ni para puntuar** | P1 |
| **RF-B5.5** | Monitor: lista autoactualizada de empresas que cambian a Torciéndose, Deterioro o Mejorando en el último mes, ordenada por magnitud del cambio, con severidad y drivers movidos | P2 |
| **RF-B5.6** | El monitor es **proactivo**: la demo enseña la alerta sin que nadie la pida, y con la frase de B4 ya adjunta | P2 |
| **RF-B5.7** | ~~Grafo de contrapartes~~ **Eliminado**: cruce contraparte↔empresa 0,0 %. Sustituto realista: **cobros por cliente** — tendencia del retraso de cada cliente *hacia ti* sobre tus propias facturas emitidas (98,7 % con contraparte). No puntúa al cliente; enseña quién te está pagando cada vez más tarde | P2 |
| **RF-B5.8** | La anticipación se mide **solo sobre las 373 empresas con 24 meses de historia** (29 %); las demás no tienen serie suficiente para un cambio de régimen defendible. Se dice así en el pitch | P1 |

**CA-B5:** existe un número concreto y defendible —"mediana de N meses de anticipación a 1
falsa alarma por empresa-año"— y quien lo dice sabe explicar cómo se midió. Sin la tasa de
falsas alarmas el requisito **no está cumplido**, aunque haya número.

---

## B6 · Consolidación de grupo

**Dueño:** Carlos + Antonio · **Prioridad:** P1 · **Depende de:** B1, B3

Opcional para el leaderboard, **obligatorio para el producto**: multi-entidad es la razón
de ser de Embat (`PRODUCTO.md` §4).

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B6.1** | Eliminar flujos intragrupo **antes** de agregar, de forma aproximada (RF-B1.13) y declarándolo | P1 |
| **RF-B6.2** | Score de grupo = 65 % media ponderada de filiales + 35 % peor filial, con penalización por contagio si una filial material está en mala situación | P1 |
| **RF-B6.3** | La vista de grupo muestra siempre el desglose por filial: *"el grupo saca 71, pero la filial portuguesa saca 38 y arrastra al consolidado"* | P1 |
| **RF-B6.4** | Si B0 determina que el test evalúa grupos y no empresas, este bloque asciende a **P0** | — |

**CA-B6:** un grupo con filiales de score dispar no queda enmascarado por la media; la
peor filial es visible en la primera pantalla.

---

## B7 · API de servicio (el contrato)

**Dueño:** Antonio · **Prioridad:** P0 · **Se congela en las 2 primeras horas** · **Depende de:** nada (se mockea)

Es el requisito con más apalancamiento del fin de semana: **todos mockean contra esto y
nadie espera al núcleo**.

```
GET  /score/{entity_id}?month=   → { score, nivel, tendencia, estado, confianza,
                                     drivers[{feature, contribución, valor, p_peer}],
                                     trayectoria[24], códigos_razón[] }
GET  /group/{group_id}           → { consolidado, filiales[] }
POST /simulate {entity_id, palancas:[{id, magnitud}]}
                                 → { score_nuevo, delta_score, caja_liberada_eur,
                                     delta_bps, eur_año }
GET  /alerts?desde=              → [{ entity_id, severidad, mes_detección,
                                      meses_anticipación, drivers_movidos[] }]
```

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B7.1** | Los cuatro endpoints existen y responden **con datos falsos** antes de la hora 2. El contrato no cambia después sin avisar a los cuatro consumidores | P0 |
| **RF-B7.2** | El núcleo es **invocable como servicio**, no un notebook: *"un notebook que solo corre en vuestro portátil no cuenta"* (enunciado §9) | P0 |
| **RF-B7.3** | Desplegado y accesible por URL desde el viernes, con dos dueños de despliegue (Antonio API, Quirce front) | P0 |
| **RF-B7.4** | Respuestas **deterministas**: misma entrada, misma salida, siempre. La demo del domingo no puede depender de aleatoriedad | P0 |
| **RF-B7.5** | Latencia de `/score` y `/simulate` por debajo de 1 s en la demo (precomputar y cachear si hace falta) | P1 |
| **RF-B7.6** | Errores con forma útil: entidad inexistente, mes fuera de rango y peer desconocido devuelven código y mensaje, no una traza | P1 |
| **RF-B7.7** | Modo offline: un fixture de respuestas grabadas que permite correr la demo entera sin red | P1 |

**CA-B7:** Quirce construye una pantalla completa contra el mock sin hablar con Carlos.
El día que el núcleo real se enchufa, el front no cambia ni una línea.

---

## B8 · Simulador y catálogo de palancas

**Dueño:** Pedro · **Prioridad:** P1 · **Depende de:** B1 (recomputable), B7

Es el acto 2 y el diferenciador central: *Experian Boost para la tesorería*, que en B2B no
existe (`PRODUCTO.md` §3).

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B8.1** | Catálogo **cerrado y parametrizado** de ~8 palancas, sin texto libre: `reducir_dso(días, clientes[])`, `ampliar_dpo(días)`, `refinanciar(producto_id)`, `bajar_utilización_línea(%)`, `reducir_concentración(cliente_id)`, `sustituir_factoring_por_línea`, `recortar_opex(%)`, `descuento_pronto_pago(%)` | P1 |
| **RF-B8.2** | **Contrafactual real, no gradiente:** aplicar la palanca al input, **recomputar B1→B2→B3** y volver a puntuar. Extrapolar desde la derivada local miente en cuanto el movimiento cruza un decil de la tabla congelada | P1 |
| **RF-B8.3** | Toda propuesta que llegue a pantalla ha pasado por `/simulate`. El número lo pone siempre el motor | P1 |
| **RF-B8.4** | Las palancas componen: varias a la vez devuelven un único resultado coherente, no la suma de efectos individuales | P1 |
| **RF-B8.5** | Palanca inaplicable (sin factoring que sustituir, sin línea que bajar) se rechaza con motivo, no se simula en vacío | P1 |
| **RF-B8.6** | Magnitudes acotadas a rangos plausibles: no se simula un DSO de −40 días | P1 |

**CA-B8:** simular "cobrar 12 días antes a 5 clientes" devuelve un score nuevo que coincide
con recalcular el pipeline entero a mano sobre el input modificado.

---

## B9 · Puente a euros

**Dueño:** Antonio · **Prioridad:** P1 · **Depende de:** B8

Dos patas **separadas y presentadas en este orden**, porque la primera es indiscutible y la
segunda es la parte más atacable del producto convertida en la más sólida.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B9.1** | **Caja liberada** = Δ DSO × facturación diaria. Aritmética pura. Va primero y siempre | P1 |
| **RF-B9.2** | **Coste de financiación:** curva `score → tipo medio observado`. `debt_schedule_config` solo tiene **87 tipos (40 empresas)**, insuficiente para ajustar nada. Fuente principal: **tipo implícito** = `interest_charge` anual / `outstanding` medio, disponible en cientos de empresas. *"No es una suposición nuestra: es lo que pagan las empresas de este dataset a este nivel de score"* | P1 |
| **RF-B9.3** | La curva se enseña con su dispersión, no como una línea limpia: si el ajuste es débil, se dice. Si ni el tipo implícito da señal, la pata 2 se retira de la demo y queda solo la caja liberada | P1 |
| **RF-B9.4** | Salida completa de la cadena: *"cobra 12 días antes a estos 5 clientes → +6 pts → −35 bps → 14.000 €/año"* | P1 |
| **RF-B9.5** | Las dos patas se muestran etiquetadas y separables: nadie puede confundir aritmética con ajuste estadístico | P1 |

**CA-B9:** cualquiera del equipo sabe decir de dónde sale cada uno de los dos números y
cuál de los dos es una estimación.

---

## B10 · Agente y orquestación de mejoras

**Dueño:** Pedro (orquestación) + Quirce (traducción a producto) · **Prioridad:** P1 · **Depende de:** B4, B5, B8, B9

**El principio de arquitectura y la frase del pitch: el agente no opina, simula.**

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B10.1** | El agente **elige y parametriza** palancas del catálogo cerrado; **nunca** inventa una cifra de score, de caja o de bps | P1 |
| **RF-B10.2** | Cada recomendación llega con su delta de score **y** su delta de euros, ambos procedentes de `/simulate` | P1 |
| **RF-B10.3** | Recomendaciones priorizadas por impacto y esfuerzo, no un listado plano | P1 |
| **RF-B10.4** | Ancladas al diagnóstico de B4: la palanca propuesta ataca el driver que realmente movió el score | P1 |
| **RF-B10.5** | **Demo determinista:** el mismo caso produce la misma recomendación. El domingo por la mañana esto vale oro | P1 |
| **RF-B10.6** | El agente es **proactivo**: consume B5 y levanta la mano sin que se le pregunte | P2 |
| **RF-B10.7** | Fallback: si el agente falla en vivo, la pantalla enseña las recomendaciones precomputadas del caso de demo | P1 |

**CA-B10:** ninguna cifra de la pantalla del agente procede de texto generado. Se puede
demostrar señalando la llamada a `/simulate` que la produjo.

---

## B11 · Front y demo navegable

**Dueño:** Quirce (front) + Hugo (diseño de producto, manda sobre el alcance) · **Prioridad:** P0 · **Depende de:** B7 (mock basta)

*"La demo cuenta tanto como el producto"* (enunciado §9). Es obligatorio y se abre delante
del jurado.

**Vistas mínimas:**

| Vista | Qué enseña | Prio |
| :--- | :--- | :--- |
| **Cartera / monitor** | Lista de empresas con score, tendencia, estado y alertas del mes. Es lo primero que se ve | P0 |
| **Ficha de empresa** | Trayectoria de 24 meses, nivel vs tendencia, drivers de B4, códigos de razón y confianza | P0 |
| **Simulador** | Palancas manipulables → score nuevo, caja liberada, bps, €/año (acto 2) | P1 |
| **Vista de grupo** | Consolidado y filiales, con la peor filial visible (B6) | P1 |
| **Pack de negociación bancaria** | Score + trayectoria + drivers + benchmark sectorial, en un link con caducidad (acto 3, donde Embat monetiza) | P2 |

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B11.1** | Desplegado en una **URL pública** desde el viernes. No vale localhost | P0 |
| **RF-B11.2** | Navegable end-to-end: de la alerta de cartera a la ficha, de la ficha al simulador, sin callejones sin salida | P0 |
| **RF-B11.3** | Camino de demo de 5 minutos ensayado y marcado, con los dos casos del enunciado como protagonistas | P0 |
| **RF-B11.4** | El gráfico de trayectoria distingue **visualmente** nivel y tendencia: es la tesis del reto ("trayectoria, no foto") | P0 |
| **RF-B11.5** | Datos precargados para los casos de demo: cero esperas y cero dependencia de red durante el pitch. Los casos Northbrook/Velasco se eligen **entre las 373 empresas con 24 meses completos** | P0 |
| **RF-B11.8** | **Sistema visual de Embat** (research de Quirce, extraído de su CSS): marino `#050b2c` + aguamarina `#5ed3e5`/`#007b93` + blancos, dos pesos tipográficos (General Sans o Switzer como sustitutos de Haffer). Score como número grande + banda + línea temporal, nunca un gauge solo; estados como texto, no solo color | P1 |
| **RF-B11.9** | Un estado de "datos insuficientes → scoring pendiente" con contenido real: el 32 % de las empresas tiene < 12 meses y el jurado puede hacer clic en una | P1 |
| **RF-B11.6** | Funciona en la resolución de proyector del aula, probado en ese proyector antes del pitch | P1 |
| **RF-B11.7** | Quirce puede sostener el front en solitario desde el sábado por la noche: el domingo Hugo ensaya, no programa | P0 |

**CA-B11:** una persona ajena al equipo abre la URL y llega sola de la alerta al euro.

---

## B12 · Narrativa y pitch

**Dueño:** Hugo · **Prioridad:** P0 · **Depende de:** B11

2:30 min ante el jurado. Un tercio de la nota del enunciado (§7, bloque 3) se juega aquí.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B12.1** | El **comprador identificado es Embat**, con el porqué le sale a cuenta: workflow ownership → transaction ownership, hoy solo ejecutado en pagos | P0 |
| **RF-B12.2** | Usar **Northbrook Foods (45→65) y Velasco Industrial (82→68)**: los nombres de su propio enunciado. Ellos plantearon la historia, nosotros la cerramos | P0 |
| **RF-B12.3** | Las tres frases ancla: *"Informa te puntúa con un balance de hace 15 meses; nosotros con el movimiento de ayer"* · *"Vosotros ya tenéis el dato, lo que no tenéis es la nota"* · *"El agente no opina, simula"* | P0 |
| **RF-B12.4** | El efecto red: el benchmark contra el peer set anónimo de los 250 grupos **solo lo puede construir quien agrega a todos** — Embat ya lo tiene y no lo monetiza | P0 |
| **RF-B12.5** | **Decir nosotros primero los matices**, antes de que los pregunten: el cash-flow complementa al bureau y no lo sustituye (FinRegLab: 0,758 combinado vs 0,720 FICO solo; +3,0 pp de aprobaciones a igual riesgo) | P0 |
| **RF-B12.6** | **Dato sintético declarado**: el score mide coherencia interna, no leyes de impago del mundo real. Los pesos son hipótesis declaradas y sometidas a análisis de sensibilidad | P0 |
| **RF-B12.7** | Cerrar con el pack bancario: es donde se ve el dinero | P0 |
| **RF-B12.8** | **Vídeo de respaldo grabado** del recorrido completo, por si la demo en vivo falla | P1 |
| **RF-B12.9** | Viento de cola regulatorio de **derecho vigente**: Ley 5/2015 + Circular BdE 6/2016 (preaviso de 3 meses y derecho a tu calificación) y RD 238/2026 (estados de pago en 4 días). **No apoyar el pitch en FIDA**, que no está adoptada | P1 |
| **RF-B12.10** | Nombrar el riesgo estratégico nosotros: Tillful absorbida por Nav, Fluidly apagada en OakNorth. La decisión que lo evita: **el dueño del score es la empresa**, y por eso el acto 2 va antes que el acto 3 | P2 |
| **RF-B12.11** | **No afirmar ante Embat que Embat no tiene algo sin haberlo comprobado en embat.io.** Su producto ya calcula DSO/DPO, aging y exposición a contrapartes (research ChatGPT-Carlos §3). Lo que no tiene es el score unificado, la trayectoria y el what-if en euros: ese es el hueco que se nombra | P0 |
| **RF-B12.12** | Confirmar con la organización la **duración del pitch**: el enunciado §10 dice 2:30, el research de Quirce planifica 5 min. El guion se escribe para la duración confirmada | P0 |

**CA-B12:** código congelado 4 h antes de la entrega; camino feliz ensayado **cinco veces**
buscando dónde se rompe; pitch cronometrado al menos dos veces el domingo por la mañana con
la demo abierta y en el proyector.

---

## B13 · Entrega al leaderboard

**Dueño:** Carlos (**dueño de la métrica**) · **Prioridad:** P0 · **Depende de:** B3

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B13.1** | Leer el script de scoring en la primera hora y resolver la tabla de `PRODUCTO.md` §6: ¿hay columna objetivo en train, o solo feedback del leaderboard? | P0 |
| **RF-B13.2** | **Rama activa: reglas.** El dataset no trae ninguna columna objetivo (comprobado 18-sep en los nueve ficheros). Solo si el script de scoring revela una etiqueta: sonda de Spearman feature a feature; si 2–3 features explican > 0,9, el target es una fórmula y se recupera, y entonces —y solo entonces— entra GBDT con restricciones monotónicas y validación por `group_id` | P0 |
| **RF-B13.3** | **Primer envío con k = 0** (solo nivel): línea base limpia. La tendencia entra como variante 2, para medir cuánto aporta en vez de asumirlo | P0 |
| **RF-B13.4** | **Máximo 5–6 variantes** contra el test oculto, cada una con justificación escrita. Más iteraciones es sobreajustar a 60–80 empresas | P0 |
| **RF-B13.5** | Validación propia con `GroupKFold` por `group_id` + corte temporal. Mejoras de CV por debajo de **0,005 no correlacionan** con el leaderboard: es la regla de parada | P0 |
| **RF-B13.6** | Las cuatro pruebas del brief §9: backtest temporal contra ELMS, estabilidad (> 0,85), **simetría** (las que mejoran suben con la misma facilidad con que bajan las que caen) y sensibilidad (mover cada peso ±10 pts mantiene correlación de rangos > 0,9) | P1 |
| **RF-B13.7** | **No optimizar el leaderboard hasta el domingo.** Dos tercios de la nota no son la métrica. Basta estar en el tercio alto | P0 |
| **RF-B13.8** | Si aparece un **leak**: usarlo para el leaderboard, jamás para la narrativa, y decirlo en voz alta | P1 |

**CA-B13:** el envío se genera con un comando desde el score congelado en configuración, y
queda registrado qué variante produjo qué puntuación.

---

## Requisitos no funcionales (transversales)

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RNF-1** | **Determinismo total.** Semillas fijas, sin aleatoriedad en el camino de la demo. Misma entrada, misma salida | P0 |
| **RNF-2** | **Reproducibilidad.** Un comando reconstruye features, tablas de percentiles, scores y envío desde los CSV en crudo | P0 |
| **RNF-3** | **Todo desplegado desde el viernes**, con dos dueños: Antonio la API, Quirce el front | P0 |
| **RNF-4** | **Configuración separada del código**: pesos, umbrales de estado y `k` en fichero, versionados | P0 |
| **RNF-5** | **Mock primero**: todo consumidor arranca contra el contrato falso; nadie se declara bloqueado | P0 |
| **RNF-6** | **Idioma:** castellano en pantalla y documentación. Los nombres de campo del contrato, tal cual están en B7 | P1 |
| **RNF-7** | **Sin datos reales**: el dataset es sintético y así se declara en pantalla y en el pitch | P0 |
| **RNF-8** | **Trazabilidad:** toda cifra visible se puede seguir hasta una fila del dataset | P1 |

---

## Matriz de trazabilidad · entregables obligatorios del enunciado §6

| Entregable | Estado | Bloques que lo cubren |
| :--- | :--- | :--- |
| Predicción sobre el test oculto | Obligatorio | B2 (tablas congeladas), B3, **B13** |
| Señal en las dos direcciones | Obligatorio | RF-B3.4, RF-B3.7, RF-B13.6 |
| Trayectoria, no foto | Obligatorio | RF-B3.3, RF-B3.5, RF-B3.6, RF-B11.4 |
| Explicación | Obligatorio | **B4** completo |
| Producto encima del score | Obligatorio | B8, B9, B10, B11 (los tres actos) |
| Comprador identificado | Obligatorio | **B12** (RF-B12.1, RF-B12.4) |
| Demo navegable | Obligatorio | **B11** (RF-B11.1, RF-B11.2) |
| Anticipación medida | Bonus | B5 (RF-B5.2, **RF-B5.3**) |
| Monitor que avisa | Bonus | B5 (RF-B5.5, RF-B5.6), RF-B10.6 |

---

## Riesgos de ejecución y mitigación

| Riesgo | Mitigación | Dueño |
| :--- | :--- | :--- |
| **Pedro escribió el brief pero no implementa el núcleo** — el mayor riesgo de traspaso del fin de semana | Media hora el viernes, Pedro → Carlos y Antonio, recorriendo el brief entero. A partir de ahí el brief es la especificación y las dudas se resuelven contra el documento, no por chat | Pedro |
| **Pedro es cuello de botella**: depende del núcleo y bloquea a Quirce | Si el viernes de noche no hay `/score` real, `/simulate` se monta sobre un stub con reglas tontas y se sigue con el catálogo. El agente no descubre su integración el sábado por la tarde | Pedro |
| **Hugo está en front y narrativa a la vez** | Quirce sostiene el front en solitario desde el sábado noche. El domingo Hugo ensaya | Hugo |
| **El contrato cambia a mitad** | Congelado en 2 h (B7). Cualquier cambio posterior se anuncia a los cuatro consumidores a la vez | Antonio |
| Ventana de 12 meses sobre 24 deja pocos puntos de serie, y solo el 29 % de las empresas tiene los 24 | Ventana creciente desde el mes 6 (RF-B1.1); si la estabilidad (RF-B13.6) sale baja, bajar a 9 (RF-B3.11) | Carlos |
| **El feature engineering es más largo de lo previsto**: as-of de facturas, reconstrucción de saldos, dirección por signo y DSCR desde banco no estaban en el brief. Las 5–6 h de la fase 2 son 8–10 | Antonio entra en B1 el viernes por la noche; la curva score→tipo (RF-B9.2) se retrasa, con 87 tipos tampoco merecía prioridad | Carlos + Antonio |
| **Leakage por `payment_date`**: en facturas no pagadas es un placeholder igual al vencimiento | RF-B1.0 como P0 y la prueba as-of de CA-B1 | Carlos |
| Todo el research de Carlos y Quirce recomienda GBDT+SHAP, el brief y el dataset dicen reglas | Resuelto por el dato: sin target no hay GBDT. Se cierra en el traspaso del viernes con el informe delante, no por chat | Pedro |
| Las tablas de percentiles se recalculan por accidente con el test dentro | CA-B2 es el test que lo detecta: puntuar una empresa sola y acompañada debe dar lo mismo | Carlos |
| Optimizar el leaderboard a costa del producto | RF-B13.7. Dos tercios de la nota no son la métrica | Todos |
| Dato sintético tomado por realidad | RF-B12.6: lo decimos nosotros antes de que lo pregunten | Hugo |

---

## Primeros 30 minutos del viernes

1. **Traspaso del brief: Pedro → Carlos y Antonio, media hora.** A partir de ahí el brief
   es la especificación.
2. **El contrato de B7 en una pizarra** y mockeado, aunque devuelva datos falsos.
3. **Las preguntas al aula**, ya sin la del grafo (resuelta: no hay): qué compara el
   leaderboard, unidad del test (empresa o grupo), formato de salida, **si el script de
   scoring trae etiqueta** y **cuánto dura el pitch** (2:30 o 5 min).
4. **Leer el script de scoring** y resolver la tabla de RF-B13.1.
5. **El informe de exploración** (`research/informe_exploracion.md`) se lee en el traspaso:
   as-of, signo de factura, saldos reconstruidos y DSCR desde banco son las cuatro piezas
   que el brief no tenía y que B1 debe incorporar desde la primera línea.
