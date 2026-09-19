# El momento en que las cosas se tuercen

**Para:** Pedro · **Fecha:** 2026-09-19  
**Qué es:** research de definición, no código. Cómo datar *cuándo* se tuercen las cosas **sin** partir de umbrales del motor.  
**Qué no es:** calibración de `momentum_threshold`, PD, ni un detector nuevo para esta noche.  
**Contexto:** X-Ray (score de salud 0–100, banco mensual, 24 meses, ERP y caja off en el núcleo). Monitor vivo: persistencia de momentum. Palancas: familia salud vs circulante.

---

## 0. Tres relojes (si mezclas estos, el punto del gráfico miente)

| Reloj | Pregunta | Ejemplo honesto | Ejemplo tramposo |
| :---: | :--- | :--- | :--- |
| **t_evento** | ¿Cuándo se materializó lo malo? | Caja ≤ 0 en el oráculo sintético; línea agotada; drawdown ya cerrado | El propio cruce que usas para alertar |
| **t_alerta** | ¿Cuándo el sistema lo confirma en lo ya observado? | Entrada a `TORCIENDOSE` / `DETERIORO` | Retrodatar al mes 1 de la racha |
| **t_anticipación** | ¿Desde qué corte *ya* se veía el camino feo? | Primer `t` en que el do-nothing a 6 meses es malo y `S_t` aún no grita | Pintar P10 como hecho; `lead_months` inventado en el feed vivo |

El pitch vende el tercero. El código emite el segundo. El laboratorio de estrés evalúa el primero (y solo en sintético). REQ-B5.1 pide `Δt = t_evento − t_alerta` a ≤1 falsa alarma por empresa-año. Eso **exige** un evento independiente del detector. Si el evento *es* el detector, la antelación es cero por construcción.

**Regla de oro:** una definición del momento elige **un** reloj. Lo demás es pie de foto, filtro o overlay.

---

## 1. Veredicto en una página

Las siete frases del brainstorming no son siete momentos. Casi todas son **funciones de la misma curva** (cómo se mueve el número). El motor ya combina pendiente + persistencia + nivel. Encima no hay que poner un octavo índice.

| Hipótesis | ¿Define el momento? | Reloj | Qué hacer con ella |
| :--- | :---: | :---: | :--- |
| La pendiente bajó mucho | **No** | trayectoria, no instante | Descartar como definición. Velasco es una rampa suave: no hay “bajón”. |
| La pendiente pasó de + a − | **No** (como alerta) | watch, si acaso | El cruce es el *máximo* (el mes menos grave). Velasco puede no cruzar nunca. |
| N decisiones negativas a la vez | **No** | coincidencia ≠ onset | Inferir intención es ficción. Coincidencia de *flujos* sí explica gravedad. |
| Circulante que se acumula / salud que cambiará el futuro | **Sí, como investigación** | **t_anticipación** | Dual del what-if: do-nothing a h=6. Es la línea fiel a “se torció antes de verse”. |
| La liquidez empezó a caer más rápido, o a 0/negativo | **Parcial** | dos instantes distintos | Gatillo privilegiado, no definición. 0 de saldo = evento (y hoy no existe en el núcleo). |
| Lo mismo sobre el factor que más empeoró el resultado | **No** | explicación | El score marca; el driver etiqueta. Si eliges el culpable mirando el daño, es post-hoc. |
| Combinación ponderada de lo anterior | **No** (como índice nuevo) | mezcla los tres relojes | AND de confirmación sobre **un** onset. No un `U = Σ w_i x_i`. |

**Recorte de producto (hackathon):**

1. **Punto rojo histórico** = primera entrada a `TORCIENDOSE` / `DETERIORO` (el monitor que ya existe).
2. **Pie de foto** = peor bloque del Δ a 3 meses (ya sale en la alerta). Si el #1 cambia y se queda 2–3 meses, sello de “cambió el diagnóstico”.
3. **Overlay de anticipación** (si da tiempo) = primer origen en que el camino estructural do-nothing a 6 meses cruza umbral y el estado aún no es deterioro. Hipótesis en pantalla, no PD.
4. **t_evento de lab** = caja-oráculo ≤ 0. Nunca feature, nunca UI.

**Lo que sí merecía estar fuera de las siete:** pérdida de opcionalidad (ya no puedes comprar tiempo), drawdown desde máximos propios (candidato a *label*), contagio de grupo (único lead con `group_id`), y dos filtros sin los cuales las siete mienten: rotura de estacionalidad y ceguera de dato.

---

## 2. Las siete hipótesis

### 2.1 La pendiente bajó mucho

**Definición operativa si se forzara:** pendiente de `base_health` (no del score: el score ya lleva momentum), OLS 6 meses o el `momentum` del motor, umbral absoluto (no “el mes más negativo de mis 24”), timestamp = **primer mes de racha confirmada**. El argmax de |pendiente| es el tramo más vertical: cerca de `t_evento`, tarde.

**Por qué no data un momento.** “Bajó mucho” describe un *estado de trayectoria*. Velasco 82→68 es **−0,61 pts/mes, constante**. No hay un mes especial. El umbral ±1 pt/mes del brief no dispara ese ejemplo. Si la empresa ya nace cayendo, el “momento” es el warmup.

**Relación con el motor.** `bounded_momentum` ya es pendiente acotada: velocidad 3 meses + EMA rápida/lenta + persistencia de flujos, `tanh`. El monitor exige `|M| > 0,10` tres meses. Reescribir “pendiente mucho” es momentum con otro nombre.

**Única variante nueva:** aceleración persistente de la base (`ΔT`), “se ha torcido *ahora*”. En 24 puntos mensuales es ruidosa. El momentum ya cambia de signo ~1 de cada 4 meses en que está activo. No la uses como definición; como mucho, auxilio de watch.

**Veredicto:** descartar como definición del momento.

---

### 2.2 La pendiente pasó de positiva a negativa

**Definición operativa:** primer mes elegible en que la serie (mejor `M_t`, no ΔS crudo) queda **≤ −ε** después de un tramo **≥ +ε**. Sin interpolar entre meses. Cero no es 0: hace falta deadband.

**Por qué pinta bien.** Es el máximo local. “Aquí se torció”. Simétrico con Northbrook (− → +). El jurado entiende un punto.

**Por qué mata la hipótesis como evento.**

- **Censura a izquierda.** Si Velasco ya cae en toda la ventana, **nunca** hay cruce +→−. El caso estrella no genera el evento.
- **El cruce es el mes menos grave.** Se “tuerce” cerca de 82, cuando mejor está, con |pendiente| minúscula.
- **Estación.** Una PYME cíclica cruza 2–4 veces al año. El monitor ya silencia eso (`annual_pattern_match`).
- Si `t_evento := t_cruce`, la antelación es cero.

**Relación con `TORCIENDOSE`.** El estado es *proceso* (tres meses bajo −0,10, base ≥ 60), no instante de signo. El opositor de 3 pts **rompe inercia** de un estado positivo; no dispara alerta. Orden realista: cruce (watch) → meses en banda → `TORCIENDOSE` si persiste sobre 60 → `DETERIORO` al perder la frontera.

**Si la pendiente ya es negativa al primer mes elegible:** `t_cruce = null`, `onset_censored = true`, el episodio está abierto. No es un miss del detector.

**Veredicto:** rechazar como “cuando se tuercen”. Como mucho, `WATCH_INFLEXION` informativo, copy “cambió el signo de la pendiente”, no “alerta temprana”.

---

### 2.3 N decisiones negativas a la vez

No hay log de CFO. Hay flujos. “Decisión” hay que reescribirla o no existe. Tres lecturas:

| Lectura | Qué cuenta | Veredicto |
| :--- | :--- | :--- |
| **A. Actos de gestión inferidos** | Disponer línea, alargar DPO, HHI↑, recortar opex, novar | **Descartar.** Inferir intención es ficción. |
| **B. Flujos coincidentes** | Cobros↓ Y gastos↑ Y deuda↑ (mismo mes o 3 m) | **Usar** como gravedad (`compound_crisis`), nunca como “decisiones”. |
| **C. Bloques del score a la vez** | Cuántos de los 7 tienen Δ < 0 vs t−3 | **Auxiliar.** N=2 es tautológico; útil si k≥3. |

**Contras letales de A.** DPO es negativo para el proveedor y positivo para caja; el motor puede premiarlo como liquidez (por eso es familia **circulante**). Recortar opex es palanca de *salud* hacia delante y “decisión mala” hacia atrás: el signo depende del tiempo verbal. HHI=0,8 en `customer_loss` es *consecuencia* de perder cliente, no “decidieron concentrar”. N=2 dispara en cualquier mes feo; N=4 solo en crisis compuesta.

**Contrato de lenguaje:** coincidencia de flujos, origen externo vs acto interno. Nunca “eligieron mal”. `rate_shock` / `fx_shock` = externo. Pérdida de cliente = contraparte. Expansión que ahoga = desfase de caja, aún no “mala decisión”. Las palancas miran **adelante** (“si adelantas cobros con descuento…”).

**Veredicto:** el monitor avisa por persistencia; la coincidencia explica por qué el golpe duele más. `t_concurrencia ≠ t_alerta`. Si coinciden, la anticipación de *esa* definición es cero.

---

### 2.4 Circulante que se acumula / salud que en el futuro pega cada vez más

Esta es la única de las siete que apunta al reloj correcto: **t_anticipación**.

`S_t = f(banco_t)` es casi una foto de flujos. Un DSO que sube hoy no tumba el score hasta que los cobros dejan de entrar. Una expansión (gastos ×1,6, cobros aún no) es squeeze con `growth_points` que a veces aún suman. El monitor entra cuando **ya** se movió la base: eso es `t_alerta`. El oráculo de caja que se agota es `t_evento`, y solo existe en sintético.

El laboratorio lo ilustra, no lo demuestra en Embat:

- `late_collections`: Δ emparejado −2,47, detección ≤6 m 56 %. El twist es el atraso; `f` casi no grita.
- `expansion_cash_squeeze`: −8,51 / 72 %. El daño se ve *después* de meses de opex alto.
- `debt_balloon`: +0,04 / 42 %. El vencimiento está en `change+3`; en el corte del shock el banco contemporáneo no se entera.

**Definición operativa (sin usar el futuro como feature).** Fotocopia del diario **hasta `t`**, proyectar, `calculate_scores` congelado. Prohibido: `banco_{t+h}` observado, caja-oráculo, etiqueta de shock.

Regla **asimétrica** (si no, la hipótesis se auto-cancela):

- **Salud** (cobros, opex, H, concentración, refunds): camino A = persistir el nuevo régimen. Camino B = como si no hubiera cambiado.
- **Circulante** (DPO/AP, confirming, dispuesto de línea): camino A = **deshacer el stock** (la AP vence; el dispuesto sigue costando). Camino B = no haber estirado. **Nunca** “seguir sin pagar para siempre”: persistir el maquillaje hace `Ŝ` *mejor*.

“Cada vez más negativo” = los tres, no uno:

1. el camino A empeora con h (1 → 3 → 6);
2. el salto a 6 meses es mucho mayor que el Δ observado en t;
3. A vs B a h=6 es material (el daño es del driver, no de la inercia).

Las bandas P10/P50/P90 del lab **no** sustituyen esto: son cuantiles de residuales, no caminos de cobros/pagos/deuda.

**Es el dual del what-if.** `/simulate` pregunta: *si tiro la palanca L, ¿cuánto mueve `S` ahora?* Esta hipótesis pregunta: *si **no** revierto lo que ya pasó, ¿`Ŝ_{t+6}` ya es malo aunque `S_t` no?* Misma maquinaria; distinta pregunta.

**Contras que matan un pitch de 24 h.** `f` no es dinámica de verdad (caja off, palancas mutan el último mes, no hay unwind de AP). Estirar DPO puede ser efecto del squeeze, no causa. Construcción e hostelería *deben* acumular circulante. Sin ground truth de impago, el lead vs oráculo es simulación. Un detector de “N factores circulantes” es fábrica de falsas alarmas (el control ya dispara 0,33/año).

**Recorte demo (1 día), si se hace:** una ficha (`expansion_cash_squeeze` o `late_collections`). Tres curvas: `S` observado; `Ŝ` si el run-rate de **salud** se mantiene; `Ŝ` si se **deshace** circulante. Marcador en el primer mes donde `Ŝ_6` cruza banda y el estado aún no es `DETERIORO`. Texto: hipótesis, no PD. Si no hay unwind de AP, **no** pintes momento “por acumulación de circulante”: pinta solo salud persistida. Lo otro, en el pitch, es una frase verdadera y un número mentiroso.

**Contrato de timestamp:**

- `t_anticipacion` = primer mes en la ventana del corte tal que `Ŝ^A_{h=6}` bajo umbral **y** gap vs B material **y** estado observado ∉ `DETERIORO`.
- `drivers[]` con `familia: salud|circulante` y `projector: persist|unwind`. Circulante **nunca** ordena por `ΔS`.
- `lead_months` en replay = `t_alerta − t_anticipacion` si el monitor acaba disparando; **en vivo `null`**.
- Warnings: `cartoon_dynamics`, `caja_off`, `causal: false`, `no_pd`.

**Veredicto:** sí como línea de investigación y, recortada, como overlay de `/prevision`. No sustituye el punto rojo del histórico.

---

### 2.5 La liquidez empezó a bajar más rápido, o se quedó en 0 / negativo

Hay **cinco magnitudes**. Mezclarlas es el error.

| Magnitud | Qué es en X-Ray | “Bajar más rápido” | “0 / negativo” |
| :--- | :--- | :--- | :--- |
| `liquidity_points` | 50·L; L de **flujos a 3 m**, no de saldo | t_alerta de componente | L=0 casi no ocurre (tanh; R=E=0 → prior 0,50 → 25 pts) |
| Margen mensual (R−E−H) | Alimenta momentum y BACHE | t_alerta débil; 1 mes = BACHE | Margen 0 = equilibrio, no quiebra |
| Saldo de caja | Oficialmente **apagado** (`cash_known=0`) | t_alerta de tesorería *si* existiera | `cash≤0` = **t_evento** de colapso (oráculo de lab) |
| Runway | Invisible sin caja | t_alerta | Evento de stock; canal off |
| `funding_gap` | Fragilidad, no L; ≥0 | t_alerta de timing | Gap=0 es **sano** |

El peso 50 % no es cosmética: L explica la mayor parte de la varianza del score. Para un tesorero, “se tuercen” = se acaba el aire. El escenario de asfixia B5 funciona **porque** L y el score se mueven *antes* de que el oráculo cruce ≤0. Como *primer driver a enseñar*, liquidez es la correcta. Como *definición del momento*, no.

**Contras.** Velasco puede torcerse por cobros o deuda con L decente. `late_collections` / `refund_wave` tuerzan C y F; `rate_shock` tuerce H. Un mes de flujo a 0 es bache (`pulse_margin_drop = 0,12`), y el sistema **clasifica eso como BACHE y no alerta**. Imputar 0 a un mes desconocido convierte `data_outage` (score ≈ 0) en `zero_activity` (score ≈ −12). Meter el oráculo en la UI es puntuar con la etiqueta que debías anticipar.

**Veredicto:** liquidez = gatillo privilegiado del waterfall. “Más rápido” ≠ el momento (es BACHE o el inicio del lead). “0/negativo” solo es evento sobre **saldo**, y hoy no existe en el núcleo.

---

### 2.6 El factor que más ha empeorado el resultado

**Cuatro definiciones de “peor”.** Solo las dos primeras son legales en una alerta viva:

| | Criterio | ¿Usa futuro? |
| :---: | :--- | :---: |
| A | Mayor Δ negativo a 3 meses (como el inbox) | No |
| B | Quién más bajó desde el máximo **ya observado** | No |
| C | Quién explica el drawdown del episodio, suelo declarado **al confirmar** DETERIORO | Frontera |
| D | Quién explica `S_24 − S_0` o el peor mes *futuro* | **Sí. Fuga.** |

“Resultado final” en un panel de 24 meses **es D**. No data una alerta.

**Dos productos distintos.**

1. El factor **define** el momento: el mes en que *ese* bloque cruza es `t_alerta`. El score puede seguir `ESTABLE`.
2. El score **define** el momento; el factor **etiqueta**. Es lo que ya hace `make_alert`.

El 1 mueve el marcador. El 2 pone el pie de foto. El 1 hereda todos los males: el ganador cambia de mes; momentum y clipping no son decisiones; L (techo 50 pts) gana casi siempre; el circulante puede maquillar L mientras cobros se hunden; elegir al culpable *después* de ver el daño es `t_evento` disfrazado.

**Variante que sí merece sitio:** no muevas `t_alerta`. Añade sello: el #1 (definición A, signo negativo, sin momentum ni clipping) **cambia** y se mantiene 2–3 meses. “Ya no es liquidez; ahora son cobros.” Las palancas rotan con el diagnóstico.

**Veredicto:** el score marca; el peor factor explica. No al revés.

---

### 2.7 Combinación ponderada de lo anterior

El SCORE ya es una combinación. El MONITOR ya es otra (momentum persistente × frontera 60 × gates × no-estación). Un meta-score `U = Σ w_i x_i` encima es **doble conteo inexplicable**.

Tres arquitecturas; no se mezclan:

| | `t*` | Pros | Contras |
| :---: | :--- | :--- | :--- |
| **OR** | el más temprano | interpretable, rápido | FA explota; el primero suele ser el más sucio; mezcla relojes |
| **AND / k-de-n** | cuando se completa el cupo | control de FA; el monitor *ya es esto* | retraso; si el cupo incluye caja≤0, llegas sin palanca |
| **Índice latente** | `U > θ` | “qué tan cerca” | pesos + θ = modelo nuevo; 24 meses → sobreajuste; “se torció porque U=0,61” |

Cadena causal típica: flujo feo → pendiente de confirmación → `M` cruza → `momentum_points` mueve S → ΔS se atribuye a L → el “peor factor” es L. **Cinco nombres, un fenómeno.** Meter pendiente, cruce, M, ΔS y L en la misma suma es contar la racha tres veces.

**Qué sí se combina sin triple conteo:** un solo onset de momentum; gates que no son la caída (calidad, historia, no-estación); confirmaciones **ortogonales** (n flujos coincidentes, si no salen del mismo margen); caja≤0 como evento; P50 como anticipación. Circulante con efecto futuro = simulación, no término de U.

Pesos **aprendidos** sobre 24 orígenes son retocar el test con otro nombre. Pesos **fijos declarados** (como el score) solo se justifican si el monitor no existiera. Existe.

Calibración: **una** curva falsas alarmas vs retraso (el protocolo ya: ≤1/año en estable/estacional, ≤5 % estructural en pulse, luego minimizar delay). Siete umbrales independientes son siete tentaciones.

**Veredicto:** confirmar (AND) sobre el onset que ya hay. La frase “combinación ponderada de cualquiera” es OR+índice. Aceptarla como producto es el bug de los tres relojes: el `min()` adelanta con P50 (anticipación colada como alerta) o el `max()` retrasa hasta caja=0 (evento colado como confirmación).

---

## 3. Otras definiciones (las que las siete no cubren)

Las siete miden *cómo se mueve el número*. Un EWS de tesorería también necesita *qué deja de ser posible*, *qué era el invierno*, *quién se torció primero en el holding* y *cuándo dejamos de ver*.

| Idea | Timestamp | Reloj | ¿Markdown / producto? |
| :--- | :--- | :---: | :--- |
| **Pérdida de opcionalidad** | Primer mes sin holgura de línea / confirming / DPO estirable | t_evento de tesorería (a veces *antes* de que S se entere) | **La más nativa Embat.** Gates ya existen. Circulante ni mueve S (caja off). |
| **Drawdown desde máximos propios** | Primer mes con `S < max_{τ<t} S − δ` (δ ~8–10, > MAE a 1 m) | t_evento / label; la entrada underwater es t_alerta | **Candidato serio a etiqueta** contra la que medir el lead de las siete. Sobrevive a rampas planas *15 pts bajo el pico*. |
| **Contagio de grupo** | Hermana material entra en deterioro y esta aún no | t_anticipación de la sana | Único mecanismo con `group_id` que no es recauchutado de `S_t`. |
| **Rotura de estacionalidad** | `seasonality_available` y no hay match YoY | filtro de t_alerta | **Higiene.** Sin esto, las siete mienten en hostelería/construcción. 24 m ⇒ un solo enero comparable. |
| **Ceguera de dato** | Calidad baja, `COBERTURA_LIMITADA`, outage | `t_ceguera`, reloj aparte | **Higiene.** Si no, cualquier detector de pendiente es un detector de ETL. `data_outage` mueve S ≈ 0. |
| **CUSUM calibrado** | Primera alarma con FA ≤1/año | t_alerta auxiliar | Cubre rampas que nunca cruzan ±1 pt/mes. Sin calibrar FA, es la pendiente con otro nombre. Bayes/HMM con 24 puntos: ruido. |
| **Palancas de salud no recuperan a h=6** | Máximo ΔS del catálogo salud no deja `Ŝ_6` sobre el listón | t_evento de irreversibilidad (tardío) | Producto (“el entrenador se quedó sin entrenamiento”), no label temprano. |
| **Salto de concentración / cliente ancla** | HHI salta o receipts↓ persistente + HHI alto | t_evento de mix | Vive en facturas; banco trae HHI pobre. ERP off. |
| Primera previsión “fuera de banda” | P50 cruza 60 (la banda 80 % tiene ~25 pts: no sale casi nada) | t_anticipación débil | Nota al pie. “El fan-chart se asustó” no es un momento económico. |
| Contrafactual “si no hubiera pasado X” | `|S − S_{do(no X)}| > δ` | explicación de un evento *ya* definido | Hueco en el *porqué*, no en el *cuándo*. Circular si X se pilla del peor Δ. |
| Exa / noticia de contraparte | — | — | **Ruido.** Dataset sintético; cruce contraparte↔empresa ~0; no hay NIF. |

Ninguna de estas desplaza **caja ≤ 0** como hard default de tesorería. Con caja off, “liquidez” es flujo (R−E−H), no checking: hay que decirlo.

---

## 4. Qué pintar, en tres capas

```
[ t_ceguera / estación ]     filtros: si no ves o es enero, no marques salud
            |
[ t_alerta ]                 punto rojo = entrada TORCIENDOSE / DETERIORO
            |                pie = peor bloque; sello si el #1 rota 2–3 meses
            |
[ overlays ]                 opcionalidad vacía · drawdown · hermana del grupo
            |
[ t_anticipación ]           Ŝ do-nothing a 6m (salud persistida / circulante unwind)
            |
[ t_evento, solo lab ]       caja-oráculo ≤ 0 · (o drawdown cerrado, si se etiqueta)
```

Copy en pantalla, por capa:

- histórico: “el monitor confirmó un giro persistente”;
- watch de signo: “la pendiente cambió de signo” (si se enseña);
- anticipación: “si esto sigue, a 6 meses el score proyectado cae”; nunca “quiebra en 6 meses”;
- evento: no existe en cartera real; no rellenar `lead_months` en el feed vivo.

---

## 5. Lo que no haríamos

- Un índice nuevo de “se torció” encima del score.
- Definir el momento como argmax de |pendiente|, cruce +→−, o N decisiones.
- Usar caja-oráculo, `S_{t+h}` observado o el mes 24 para elegir al culpable.
- Imputar 0 a un mes hueco.
- Persistir DPO/confirming en la proyección y vender el `ΔS` (maquillaje) como anticipación.
- Retrodatar la confirmación al mes 1 de la racha.
- Telegram de riesgo en un cruce de signo o en un BACHE.
- Exa como timestamp.

---

## 6. Preguntas abiertas (para decidir, no para implementar aún)

**P1.** En el gráfico de demo, ¿el punto rojo es solo `t_alerta` del monitor, o queréis un segundo punto de `t_anticipación` (camino a 6 m) aunque sea hipótesis?

**P2.** Como *label* de laboratorio para medir lead time, ¿caja-oráculo ≤ 0 (ya) o drawdown desde máximos (más usable cuando no hay caja)?

**P3.** ¿La pérdida de opcionalidad (línea/DPO agotados) entra en el pitch como “ya no puedes comprar tiempo”, aunque no mueva el score?

**P4.** ¿El sello “cambió el diagnóstico” (peor factor que rota 2–3 meses) os parece producto de esta noche o de después?

Si no hay respuesta, el default es: **P1 solo t_alerta** + overlay de anticipación si el estructural do-nothing está listo; **P2 caja-oráculo** (ya medido); **P3 frase de pitch, no punto**; **P4 después**.
