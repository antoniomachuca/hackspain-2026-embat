# Requisitos del proyecto · por bloques de arquitectura

**Qué es esto:** la especificación ejecutable del sistema, bloque a bloque. Cada bloque
tiene dueño, contrato de entrada/salida, requisitos numerados y criterios de aceptación
comprobables.
**Qué NO es:** ni la investigación del algoritmo (vive en
[`research/algo_research_pedro.md`](research/algo_research_pedro.md)) ni la tesis de
producto (vive en [`PRODUCTO.md`](PRODUCTO.md)). Este documento los traduce a requisitos.

**Jerarquía ante conflicto:** `ENUNCIADOTRACK.md` → `PRODUCTO.md` (producto, comprador,
narrativa) → `algo_research_pedro.md` (algoritmo) → este documento (cómo se comprueba).
**Última actualización:** 2026-09-18

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
**Salida:** tablas cargadas y validadas + un `informe_exploracion.md` de una página con
las cinco respuestas de `algo_research_pedro.md` §6.1 y las decisiones que disparan.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B0.1** | Cargar los nueve ficheros con tipos explícitos (fechas como fecha, importes como decimal) y dejar constancia de filas leídas por fichero | P0 |
| **RF-B0.2** | Validar integridad referencial: todo `company_id` de `transactions`, `invoices`, `balances` y `debt_*` existe en `companies`; todo `group_id` existe en `groups` | P0 |
| **RF-B0.3** | Responder las cinco preguntas de exploración: % de contrapartes que cruzan con `company_id`, nº de países/monedas/ERPs, % de empresas con línea/factoring/aval, movimientos por empresa y semana (mediana y P10), empresas con < 12 meses de historia | P0 |
| **RF-B0.4** | Disparar y **registrar por escrito** las cinco reglas de decisión de §6.1 (grafo sí/no, definición de peer, granularidad mensual, peso del bloque de deuda) | P0 |
| **RF-B0.5** | Resolver la unidad de trabajo: `company_id` (1.286) frente a `group_id` (250), y confirmar contra los ingenieros del aula qué unidad evalúa el test oculto | P0 |
| **RF-B0.6** | Calendario canónico de 24 meses (sep-2024 → sep-2026) compartido por todos los bloques; los meses sin movimiento existen con valor cero, no desaparecen | P0 |
| **RF-B0.7** | Normalizar signo de importes (entrada positiva / salida negativa) y documentar la convención una sola vez | P0 |
| **RF-B0.8** | Conversión a EUR de flujos y saldos en divisa distinta, con tipo documentado | P2 |

**CA-B0:** un comando reproduce la carga de cero y emite el informe. Dos personas distintas
obtienen los mismos conteos. Las decisiones de §6.1 están escritas y fechadas, no en la
cabeza de nadie.

**Riesgo:** si el cruce contraparte↔`company_id` sale < 20 %, **no hay grafo** (B5 pierde
su diferenciador 3 y la concentración se queda en HHI). Se decide aquí y no se revisita.

---

## B1 · Features del rastro

**Dueño:** Carlos · **Prioridad:** P0 · **Depende de:** B0 · **Tiempo objetivo:** 5–6 h

**Entrada:** tablas de B0.
**Salida:** tabla `features[company_id, mes, feature] → valor` con las ~16 features de los
cuatro bloques, más `meses_historia` y los insumos de confianza.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B1.1** | Ventana móvil de 12 meses por empresa y mes; meses 1–11 con ventana creciente y mínimo de 6, marcados con menor confianza | P0 |
| **RF-B1.2** | **Liquidez:** runway, flujo neto medio / ingresos medios, nº de meses con flujo negativo, volatilidad del flujo normalizada por ingresos | P0 |
| **RF-B1.3** | **Conducta de pago:** DBT como pagador ponderado por importe, % de emitidas vencidas sin cobrar, retraso medio de cobro sobre vencimiento, gap DSO−DPO, % de facturas pagadas tarde | P0 |
| **RF-B1.4** | **Deuda:** DSCR proxy, utilización de líneas, deuda total / ingresos anualizados, factoring y confirming sobre ingresos | P0 |
| **RF-B1.5** | **Concentración:** HHI de clientes, HHI de proveedores, % de ingresos de contrapartes recurrentes | P0 |
| **RF-B1.6** | Facturas **emitidas** y **recibidas** se calculan por separado y nunca se agregan en un solo número | P0 |
| **RF-B1.7** | Un DPO alto no penaliza por sí mismo: solo penaliza el **retraso real sobre el vencimiento** | P0 |
| **RF-B1.8** | DSCR proxy según §6.3: numerador = cobros − pagos operativos de 12 m excluyendo financiación, intragrupo e inyecciones de capital, sin restar cuotas; denominador = cuota anual del cuadro de amortización + intereses sobre dispuesto en líneas + fee de factoring + 0 por avales | P0 |
| **RF-B1.9** | Empresa sin línea de crédito: utilización **neutra**, nunca penalizada | P0 |
| **RF-B1.10** | Nulos imputados con la mediana del peer, con marcador de dato faltante que alimenta B3-confianza y **no** el riesgo | P0 |
| **RF-B1.11** | Cada feature declara su dirección (mayor = mejor / mayor = peor) en un único sitio, y la inversión se aplica una sola vez en todo el pipeline | P0 |
| **RF-B1.12** | El pipeline es **recomputable sobre un input modificado** (requisito duro de B8: el contrafactual reejecuta features, no deriva) | P0 |
| **RF-B1.13** | Eliminación de flujos y facturas intragrupo antes de cualquier agregación de grupo | P1 |
| **RF-B1.14** | Insumos de confianza: % conciliado, meses de historia, cobertura de productos, match factura↔banco | P1 |

**CA-B1:** ninguna feature devuelve NaN o infinito para una empresa con ≥ 6 meses. Tres
empresas revisadas a mano cuadran con el cálculo. Recalcular sobre un input modificado en
un campo cambia solo las features afectadas.

---

## B2 · Peer groups y percentiles congelados

**Dueño:** Carlos · **Prioridad:** P0 · **Depende de:** B1 · **Tiempo objetivo:** 2–3 h

**Entrada:** `features`.
**Salida:** tablas de deciles por `(peer, feature)` **persistidas en disco**, y función
`percentil(feature, valor, peer) → [0,100]`.

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B2.1** | Peer = país × cuartil de ingresos anualizados (o región × tamaño si B0 encuentra > 8 países) | P0 |
| **RF-B2.2** | Las tablas se calculan **solo con empresas de entrenamiento**, se serializan y se versionan. Una empresa nueva se coloca contra ellas; **jamás** se recalculan incluyéndola | P0 |
| **RF-B2.3** | *Shrinkage* por tamaño del peer: ≥30 local · 15–29 mezcla `w=n/(n+K)` · 5–14 casi global con etiqueta "peer limitado" · <5 solo global | P0 |
| **RF-B2.4** | Valor fuera del rango de la tabla: se satura en 0 o 100, nunca extrapola ni falla | P0 |
| **RF-B2.5** | Empresa de peer desconocido (país nuevo en test): cae a global con etiqueta y baja de confianza | P0 |
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
| **RF-B3.10** | **Un solo algoritmo**: el score de reglas es el que se envía al leaderboard y el que consume el producto. Si aparece una variante mejor, se sustituye entera; no conviven dos motores | P0 |

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
| **RF-B4.5** | **Prohibido SHAP, LIME y beeswarm.** Sobre un score aditivo la explicación *es* el modelo, y el enunciado premia que se pueda contar | P0 |
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
| **RF-B5.7** | Grafo de contrapartes (ves que tu cliente paga tarde a terceros antes de fallarte a ti) **solo si** B0 confirmó cruce suficiente | P2 |

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
| **RF-B6.1** | Eliminar flujos y facturas intragrupo **antes** de agregar (RF-B1.13) | P1 |
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
| **RF-B9.2** | **Coste de financiación:** curva `score → tipo medio observado`, ajustada con los tipos **reales** de `debt_products.csv` y `debt_schedule_config.csv`. *"No es una suposición nuestra: es lo que pagan las empresas de este dataset a este nivel de score"* | P1 |
| **RF-B9.3** | La curva se enseña con su dispersión, no como una línea limpia: si el ajuste es débil, se dice | P1 |
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
| **RF-B11.5** | Datos precargados para los casos de demo: cero esperas y cero dependencia de red durante el pitch | P0 |
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

**CA-B12:** ensayado cronometrado al menos dos veces el domingo por la mañana, con la demo
abierta y en el proyector.

---

## B13 · Entrega al leaderboard

**Dueño:** Carlos (**dueño de la métrica**) · **Prioridad:** P0 · **Depende de:** B3

| ID | Requisito | Prio |
| :--- | :--- | :--- |
| **RF-B13.1** | Leer el script de scoring en la primera hora y resolver la tabla de `PRODUCTO.md` §6: ¿hay columna objetivo en train, o solo feedback del leaderboard? | P0 |
| **RF-B13.2** | Si **solo hay feedback**: reglas puras, ajuste de 5–6 variantes de pesos y nada más. Si **hay etiqueta**: sonda de Spearman feature a feature; si 2–3 features explican > 0,9, el target es una fórmula y se recupera. Si **no está claro**: reglas, y preguntar en el aula | P0 |
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
| Ventana de 12 meses sobre 24 deja pocos puntos de serie | Si la estabilidad (RF-B13.6) sale baja, bajar la ventana a 9 meses | Carlos |
| Las tablas de percentiles se recalculan por accidente con el test dentro | CA-B2 es el test que lo detecta: puntuar una empresa sola y acompañada debe dar lo mismo | Carlos |
| Optimizar el leaderboard a costa del producto | RF-B13.7. Dos tercios de la nota no son la métrica | Todos |
| Dato sintético tomado por realidad | RF-B12.6: lo decimos nosotros antes de que lo pregunten | Hugo |

---

## Primeros 30 minutos del viernes

1. **Traspaso del brief: Pedro → Carlos y Antonio, media hora.** A partir de ahí el brief
   es la especificación.
2. **El contrato de B7 en una pizarra** y mockeado, aunque devuelva datos falsos.
3. **Las tres preguntas del brief §5 a los ingenieros del aula** y la exploración B0 —
   sobre todo si las contrapartes cruzan con `company_id`, que decide el grafo (RF-B5.7).
4. **Leer el script de scoring** y resolver la tabla de RF-B13.1.
