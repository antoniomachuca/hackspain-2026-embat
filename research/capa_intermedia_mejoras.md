# Capa intermedia de mejoras · Investigación completa

**Fecha:** 2026-09-19 · **Rama:** `feat/capa-intermedia-mejoras` · **Investigación + implementación en curso.**
**Dueño:** Pedro (catálogo, `/simulate`, orquestación, monitor). El núcleo es de Carlos/Antonio; este documento no lo retoca.
**Contrato motor:** ver `docs/respuestas_a_pedro.md` y `research/capa_intermedia_decisiones.md` §11.

**Criterio de cada veredicto:** ¿mejora la tesorería de forma defendible ante Embat? Subir el score no basta.

**Dataset usado:** ZIP de organizadores, copiado a `dataset/` (gitignored). 1.286 empresas, 250 grupos, 2.556.437 movimientos, 897.894 documentos ERP. Corte de extracción **2026-09-01**. Panel del motor: 24 meses de transacciones en `[2024-09-01, 2026-09-01)`.

**Motor usado:** `algorythm/score_engine.py` + `score_data.py` + paneles `algorythm/engine_results/` (ERP off, `cash_known=0`) y `engine_results_erp/` (snapshot opt-in, solo el último mes).

---

## 0. Cómo leer esto

El trabajo se hizo en cuatro oleadas: (1) motor y dataset en paralelo, (2) filtro de honestidad de palancas, (3) semántica / orquestación / euros / monitor en paralelo, (4) este documento.

Las **38 tareas** están respondidas por número. El resumen ejecutivo de abajo es la ley; el detalle está en las secciones.

Tres correcciones respecto a `PRODUCTO.md` / `REQUISITOS.md` que este research **congela**:

| Bit documentado | Realidad del código y del dato |
| :--- | :--- |
| «El gradiente miente al cruzar un decil de percentiles congelados» | El motor **no tiene** percentiles ni peers. Escala con Hill \(x/(x+a)\) y tanh. Sigue siendo **recomputación**, no gradiente, **por kinks y ventanas**, no por B2. |
| Catálogo de **8** palancas Strategy | El corte a 3 era un **MVP de demo**, no el producto. Post-§13: catálogo ancho + mutadores colapsados + dos pistas de ranking; cobertura baja ≠ muerte. |
| Curva score → tipo → `delta_bps` | **Retirada.** 87 tipos de 40 empresas; el implícito no es un tipo. |

---

## 1. Veredicto (lo que hay que construir, cuando toque)

**MVP de demo — tres palancas, no ocho:**

| # | `id` | Veredicto | Qué muta | Qué ve el motor hoy |
| ---: | :--- | :--- | :--- | :--- |
| 1 | `adelantar_cobros` (alias PRODUCTO `reducir_dso`) | **Entra con supuesto** | AR pendiente → `receipts` + `funding_gap` del **último mes** | Sin ese mapa, ΔS histórico = **0**. DSO de facturas solo pinta si ERP on, y solo el 2026-09-01. |
| 2 | `recortar_opex` | **Entra** | `expenses` de `salary` ∪ `utility` | El motor ya lee gastos. Whitelist obligatoria. |
| 3 | `refinanciar` | **Entra con supuesto** | Bajar `debt_service` **recurrente** con oferta explícita | El motor ve `H`. Amortizar un mes **empeora D**. El cuadro de 87 filas no sirve. |

**Orden de construcción (demo primero, catálogo después):** las tres de arriba son el acto WOW. El producto completo reincorpora el resto con gates — n=19 no es un no. Lo que queda fuera de verdad está en §12.3 (maquillaje o input inexistente sin adaptador).

**Contrato de simulación:** `contrafactual_de_corte`. Mutar **solo el mes 23** (agosto 2026). No hay cola futura. No reescribir jun–jul para fabricar momentum. En pantalla: *«si el último mes del extracto hubiera sido así»*, no *«proyección a 90 días»*. ΔM = 0 por construcción.

**Euros:** `caja_liberada` sí (liberación de circulante, no beneficio). `delta_bps` y `eur_año` = `null` salvo oferta de refinanciación escrita.

**Tres empresas para el acto:**

| Rol | `company_id` | Score bank 2026-09-01 | Qué enseña |
| :--- | :--- | ---: | :--- |
| Mejora | `COMP_0153` | 82,13 (+59 desde m6) | Trayectoria L. Sin palanca urgente. |
| Deterioro | `COMP_0176` | 5,17 (−69) | Colapso. No vender refi ni cobros (R=0, AR pendiente=0). |
| What-if en € | `COMP_0031` | 65,53 (ERP 52,32) | AR 2,09 M€, DSO ~194 d, caja 7/15/30 d ≈ 76k / 164k / 328k €. |

**116 empresas `is_prior` en el endpoint (score = 50 exacto):** cero palancas. Δ contra 50 es teatro.

---

## 2. Dataset visto como material de simulación (tareas 1–7)

### Tarea 1 · Objetos mutables

El contrafactual honesto muta la **foto al corte**, no el libro histórico.

| Objeto | Campos que existen | ¿El motor los lee? | Uso lícito |
| :--- | :--- | :--- | :--- |
| Facturas AR abiertas | `pending_amount`, `due_date`, `status` | ERP snapshot: pending → DSO/late/conversion. **AP (`amount<0`) se tira.** | Bajar pending **y** inyectar el euro en `receipts` |
| `payment_date` en pending/overdue | Sí, relleno | **No.** Es placeholder (= `due_date` en 96,3 % overdue / 98,3 % pending) | No usarlo para «adelantar cobro» |
| Transacciones `booked` | `amount`, `date`, `category` | Sí: se agregan a `receipts` / `expenses` / `debt_service` | Reescribir el pasado booked = falsear historia |
| Deuda catálogo | `granted`, `outstanding`, `liquidity` | **No.** El score de deuda es flujo bancario `H` | Mutar outstanding no mueve S |
| `balances.csv` | `balance` a ~2026-09-01; `available` **NULL 7.996/7.996** | **No** (`terminal_balances_used: false`) | Caja usable = checking, no la suma de balances |
| Cola futura post 2026-09-01 | **0 filas** | — | No hay escenario proyectado que copiar |

El 1-sep-2026 aporta 9.242 movimientos de **un solo día** y queda **fuera** del panel (el `end` es exclusivo para txs). No es mes 25.

### Tarea 2 · Cobertura por palanca (no por empresa media)

Universo 1.286. Cohorte 24 meses de tx en el panel: **370** (el informe de exploración decía 373; la diferencia es el filtro `date < 2026-09-01`).

| Señal | Empresas | % | En 24 m |
| :--- | ---: | ---: | ---: |
| AR viva (invoice, as-of canónico) | **669** | 52,0 | **234** |
| AP viva | **755** | 58,7 | **253** |
| AR y AP juntas | 660 | 51,3 | 234 |
| Sin ninguna factura | **501** | 39,0 | — |
| Solo recibidas (cero AR invoice) | **67** | 5,2 | — |
| Línea de crédito | **206** | 16,0 | **64** |
| Factoring | **19** | 1,5 | 2 con 24 m **y** línea |
| Confirming | 70 | 5,4 | — |
| Avales | 51 | 4,0 | — |
| Cualquier `debt_products` | 378 | 29,4 | — |
| **Ningún** producto de deuda | **908** | 70,6 | — |
| `interest_charge` booked | 470 | 36,5 | — |
| `debt_repayment` booked | 524 | 40,7 | — |
| Servicio de deuda banco (unión) | **716** | 55,7 | **252** |
| `debt_schedule_config` | 40 | 3,1 | **12** |
| Checking + fila de balance | 1.267 | 98,5 | no discrimina |
| `salary` ∪ `utility` booked | **1.157** | 90,0 | **356** |

Demo viable en cientos: cobros, DPO (como objeto, no como salud), opex. Línea: acto puntual (64 en 24 m). Factoring y cuadro: no.

### Tarea 3 · Calendario y as-of

Regla as-of **obligatoria** (ya en `informe_exploracion.md` §3, confirmada aquí):

- Viva en *t* si `issuance ≤ t` y (`status ≠ paid` **o** `payment_date > t`).
- `payment_date` solo si `status == paid` y `issuance ≤ payment ≤ 2026-09-01`.

Sin esa regla, el DSO de febrero mete cobros de marzo–agosto: **12.374** cobros posteriores (importe 1,37×10¹⁰) contaminarían el mes 18.

**Reducir DSO en el mes 18 con el motor actual es imposible:** ERP escribe **solo** `as_of=2026-09-01` (columna 23). Los 23 cortes anteriores tienen `erp quality = 0`.

### Tarea 4 · Identidad de cliente / proveedor

- Facturas: **98,7 %** con `counterparty_id` (124.030 IDs).
- Movimientos: **9,8 %**.
- Cruce `counterparty_id = company_id`: **0**. Prefijos `COUNTERPARTY_*` vs `COMP_*`.
- Una contraparte de factura **no** aparece en dos empresas.
- **409** empresas tienen ≥5 clientes con AR abierta: se puede targetear «estos N clientes» sin fingir que son empresas puntuadas.
- Las txs banco no sirven para elegir clientes (cobertura CP demasiado baja).

### Tarea 5 · Deuda real vs catálogo

El score **no** usa `outstanding`. Usa `debt_repayment` + `interest_charge` (`amount<0`) → `debt_service`.

| Conjunto | Empresas |
| :--- | ---: |
| Catálogo `debt_products` | 378 |
| Banco (repayment ∪ interest) | 716 |
| Solape | 327 |
| Solo banco | **389** |
| Solo catálogo | 51 |

Cuadro: 87 filas, 40 empresas, **81/87** `next_payment_date` ya pasadas. Refinanciar «la próxima cuota del schedule» solo es honesto en **5 empresas**.

Utilización de líneas (`abs(outstanding/granted)`, granted negativo en 464/536): mediana **0,45**, P75 **0,97**, P90 **1,00**, 25 líneas > 1. Señal fuerte **donde existe**, pero **no es input del motor**.

110 líneas con `outstanding > 0`: `abs()` no es automáticamente dispuesto.

### Tarea 6 · Caja usable

- `available` vacío en **todas** las filas de `balances`.
- Caja usable ≈ productos `checking` (saving: 10). Sumar todo `balance` mezcla préstamos, avales, tarjetas e inversión y **resta deuda**.
- Amortizar línea = `checking − X` **y** outstanding/flujo de deuda, no «sumar balances».
- Solo **34/206** empresas con línea cubren el dispuesto completo con corriente.
- Aval ≠ caja.
- El motor **no observa caja** (`cash_known=0` en 30.864 celdas). Liberar euros de circulante **no mueve L por saldo**.

### Tarea 7 · Categorías sucias

- `category = '-'` ≈ **24,9 %** de txs; `transfer` 5,95 % / 925 empresas.
- `EXPENSE_CATEGORIES` del motor: `payment`, `bulk_payment`, `salary`, `social_security`, `tax`, `utility`, `fee`.
- Recortar un % sobre las siete corta **tax / SS / fee** en 1.119 empresas y `payment` de proveedor en 1.200.
- Whitelist de palanca: **solo `salary` ∪ `utility`**. Mediana de esa share sobre gastos clasificados, 3 m: **17,5 %**.

---

## 3. Motor tal como está (tareas 8–14)

### Tarea 8 · Mapa feature → bloque

```text
receipts, expenses, quality          →  L (margen 3 m, tanh)     peso 50 pts
receipts CV 6 m, refunds             →  C banco                   peso 30 pts
debt_service / (receipts+H)          →  D                         peso 20 pts
base_bank + confirmación 6 m         →  M                         ×8
max(Δ receipts, 0)                   →  G                         ×6
funding_gap, HHI, saldo rojo         →  F (solo resta)            ×−8
clip[0,100]                          →  clipping_points
```

Caja observada, si existiera, **sustituye** L (no se mezcla). ERP mezcla C y G ≤ 40 % y **no crea momentum**.

En el panel real (1.170 observed, 2026-09-01): L explica el **84 %** de la varianza del score (Pearson 0,917). Collections 15 %, momentum 9 %, D ~4 %. El score **es liquidez de flujos a 3 meses**.

### Tarea 9 · Qué está apagado

| Canal | Estado en `engine_results/` | Efecto para palancas |
| :--- | :--- | :--- |
| ERP (DSO, late, HHI facturas, sales growth) | `erp_snapshot=False`. Motivo: `disabled_without_verified_direction_and_historical_states` | `reducir_dso` solo-factura → ΔS histórico **= 0** |
| ERP opt-in | Solo columna 23; **466** empresas usable; `dso_change_known=0` siempre (no hay DSO en t−3) | El 25 % tanh(ΔDSO) **nunca corre** |
| `cash_observations` | No se llama. `cash_known=0` | Amortizar-con-caja y runway **invisibles** |
| HHI banco | 125 empresas (cobertura CP trailing 3 m ≥ 95 %) | Diversificar no existe en el resto |

Con ERP on, 466 scores cambian en 2026-09-01 (mediana \|Δ\| = 2,50; **337 bajan**, 129 suben). C sí se mueve; el término de *cambio* de DSO no.

### Tarea 10 · No linealidades (por qué no hay gradiente)

Lista real de este motor, **no** el cuento del decil peer (B2 no está implementado):

- Deadband estricto 0,02 y conteo **entero** de persistencia → 1 mes ⇒ M=0.
- `t < 5` ⇒ M=0 (`history_ready`).
- `max(g, 0)` en crecimiento.
- Switches: `cash_used`, `erp_mix=0`, HHI solo si cobertura ≥ 95 %, `is_prior`.
- Hill y tanh saturan.
- `clip[0, 100]`.
- Ventanas 3 m / 6 m: un euro este mes vale 1/3 en L.

El jacobiano es 0 casi en todas partes y miente en los saltos. Catálogo discreto + **dos** llamadas a `calculate_scores`.

### Tarea 11 · Simetría y trampas

| Trampa | Qué hace el motor | Qué haría un tesorero |
| :--- | :--- | :--- |
| Retrasar `expenses` (DPO) | **Sube L**, confirmación y a menudo baja el gap | Estrés de proveedores, no salud |
| Más `debt_service` un mes (amortizar) | **Empeora D** (test `test_more_debt_never_improves_debt_pillar`) | Desapalancar es bueno |
| `debt_service=0` | D = **0,5** (neutro), no 1,0. Techo de D = 10 pts, no 20 | «Sin deuda» ≠ «deuda perfecta» |
| G = `max(x,0)` | Una contracción no resta crecimiento; un spike de cobros **inventa G** | — |
| F solo resta | Diversificar como mucho quita un punto de penalización | — |
| Factoring ≈ `collection` | Hincha receipts / L y esconde el coste | Liquidez cara |

### Tarea 12 · Momentum y horizonte

`bounded_momentum`: hace falta índice de mes ≥ 5 y **2 de 3** meses recientes sobre el deadband (o 3/3 si se exige persistencia plena), con `min(quality)` en 6 meses.

- Spike 1 mes: **ΔM = 0**. Nivel diluido ~1/3 en la ventana de 3 m.
- 2 meses: M empieza (~0,10 en la sonda +20 % cobros).
- 3 meses: M ~0,32, ΔS +7,74 en la sonda.

Palanca de trayectoria: **≥2 meses de acción**. El contrato MVP elige 1 mes a propósito (ver tarea 20): **no vender inercia**.

### Tarea 13 · `is_prior` y cobertura

`is_prior = ¬evidence` → score **exactamente 50**. Endpoint: **116** priors (9,0 %); con ERP, 111. Palancas **inaplicables** (`motivo_rechazo=sin_evidencia_score`).

`history_ready` es otro flag: falso hasta `as_of=2025-03-01`. En el endpoint las 1.286 lo tienen a true; el filtro útil es `~is_prior` (**1.170**).

Quality = `min(native_share, classified_share)`. 97.401 txs caen por FX/`exchange_rate ≠ 1`. Una palanca que mueva importes en otra moneda no entra al panel nativo.

### Tarea 14 · Sensibilidad cualitativa (sondas sintéticas)

Fixture estable 120/100/5 → score **67,91**.

| Sonda | Δscore | Lectura |
| :--- | ---: | :--- |
| Cobros +20 % × 3 meses | **+7,74** | M +0,32 |
| Cobros +20 % × 1 mes | **+1,35** | M = 0 |
| Gastos +20 % permanentes | **−4,50** | Solo L |
| Gastos +20 % × 3 meses recientes | **−7,87** | Simétrico feo de cobros |
| `debt_service` 5→50 | **−6,68** | Todo D |
| DSO drop, `quality=0` | **0** | Invisible |
| Cash=200 (no está en paneles reales) | **+11,63** | Palanca más fuerte y **apagada** |
| HHI 0,3 vs 0,9 | **−0,95** | Hill plana |
| Mutar t≥18 | prefijo t<18 **idéntico** | Causalidad puntual OK |

Clipping 100 con config default **no aparece** en empresas reales (máx 88,92; 0/30.864 celdas con clip ≠ 0). Clip 0 sí en colapso sintético irregular.

---

## 4. Palancas y filtro de honestidad (tareas 15–19)

### Tarea 15 · Lista candidata

Ocho de PRODUCTO + extras (§12, corregido en §13): `reducir_dso` (alias), `adelantar_cobros`, `descuento_pronto_pago` (**id propio**, superconjunto de cobros; nunca apilable con `#1` — §13.3), `ampliar_dpo`, `bajar_utilizacion_linea`, `amortizar_linea_con_caja`, `refinanciar`, `sustituir_factoring`, `reducir_concentracion`, `recortar_opex`, `usar_confirming`, `disponer_linea`, `vender_inversiones`, `renegociar_interes`, `leasing_a_cuota_menor`, `ofrecer_pronto_pago_proveedor`, `bajar_devoluciones`. `inyectar_caja_observada` y `alisar_calendario`: **fuera** (§13.1 / §13.5). Avales: fuera (sin feature).

### Tarea 16 · Salud vs maquillaje

El test que pedías (refinanciar que «mejora el crédito» sin mejorar la empresa) se aplica así. **«Fuera» aquí = no vender como *salud* / no fingir ΔS**, no = borrar del catálogo. Cobertura (n) no decide.

| Palanca | ¿Cambia flujos/fechas/stock de verdad? | ¿El motor lo premia de forma tramposa? | Veredicto |
| :--- | :--- | :--- | :--- |
| Adelantar cobros (mapa a receipts) | Sí, cobra AR | No, si no se reescribe W3 entero | **Entra con supuesto** |
| DSO solo-factura | Circulante sí; S histórico no | Invisible en default | No como acto de score |
| Descuento pronto pago | Sí, con coste | Sin campo en el dato: supuesto puro | **Id propio** = adelanto + tasa>0; excluyente con `#1` (§13.3) |
| Ampliar DPO | Retrasar pagos | **Sí: sube L.** AP invisible si solo `due_date` | **Circulante, no salud.** Catálogo sí. Sort de salud no (§13.2) |
| Bajar utilización | Tesorería sí (desponer línea) | Motor no tiene el campo; caja apagada (§13.1) | **Entra con gate A.** Euros no-score hoy; n=206 no es cementerio |
| Amortizar con caja | Sí | Caja apagada; one-shot H empeora D | **Entra con gate.** `delta_score=null` mientras `cash_known=0` |
| Refinanciar (bajar H recurrente) | Sí, si hay oferta | El mes de amortización extra es la trampa | **Entra con supuesto** |
| Factoring → línea | En 19 empresas | Factoring hincha `collection` | **Entra.** n=19 = filtro A. Coste visible o no se vende |
| Bajar HHI sin sustituir ventas | No | Gaming del escalar | **Fuera** el float. Mix de clientes **sí** (`reducir_concentracion`) |
| Recortar opex `salary`/`utility` | Sí | Cortar tax/cuotas sería trampa → whitelist | **Entra** |
| Confirming | Acreedor cambia (banco paga) | Bajar/desplazar E = trampa (§13.7) | **Entra** como circulante; expenses intocados |

### Tarea 17 · Aplicabilidad (`es_aplicable`)

Falso si cualquiera de:

- `is_prior`
- se pide ΔS y falta el **adaptador** (filtro B): mapa AR→`receipts`, timing de `payment`, etc. El id **sigue** en el catálogo; **no** hay bit «cementerio»
- sin el **objeto** de *esta* palanca: sin AR / sin AP / sin salary∪utility / sin H material / sin línea / sin factoring / sin confirming / sin HHI usable — predicado por id (§12.1–12.2)
- refinanciar cosmético (ΔH≈0, o D ya = 0,5 con H=0)
- mutación caería en FX excluido
- exige `cash_known` para ΔS (hoy siempre falso — §13.1); la palanca puede seguir siendo aplicable a **euros no-score**

**No** es motivo de `es_aplicable=false`: n pequeño; «no es MVP de demo»; lista de ids «cementerio»; DPO con AP viva (sí aplicable a circulante).

`motivo_rechazo` nunca vacío cuando `es_aplicable=false`.

**682 / 1.170** observed ya tienen D=0,5: refinanciar es no-op de D. Umbral práctico: D ≥ 0,49 (848 empresas) ≈ techo.

### Tarea 18 · Efectos cruzados

Adelantar cobros (1 mes, contrato MVP): L↑, C puede **bajar** (el CV de 6 m ve el spike), D sube un poco vía \(H/(R+H)\), **M=0**, G puede subir (agujero cosmético: **no anclar el acto a G**), F-gap baja si el calendario diario se alisa.

Recortar opex: L↑, resto poco. No tocar `payment` (proveedor) ni tax/SS/fee.

Refinanciar: D↑ solo si H baja **y** R>0. Si R≈0 (`COMP_0176`, H 3 m = 51 €), bajar H hasta 0 es **carencia premiada**, no tesorería.

### Tarea 19 · MVP de demo vs catálogo de producto

El acto WOW (Carlos paso 6, §1) sigue siendo **tres** palancas: `adelantar_cobros`, `recortar_opex`, `refinanciar`. Eso es orden de **construcción / demo**, no el catálogo.

`GET /palancas` lista el catálogo **ancho** (§12 + §13). Cada id lleva `es_aplicable` por empresa. El agente no «descubre» palancas: recorre las aplicables en **dos listas** (salud / circulante — §13.2). Que factoring solo salga en 19 fichas es **correcto**, no un fallo.

**Cementerio** no es una segunda lista de ids muertos. Es honestidad y visibilidad (§12.3 / §13): no vender DPO/confirming/disponer como salud; no fingir ΔS sin adaptador ni con caja inventada; no mutar el float HHI; no encender caja/ERP solo en `/simulate`; `alisar_calendario` fuera (ΔS &lt;1 pt + rewrite ledger).

---

## 5. Semántica de la simulación (tareas 20–25)

### Tarea 20 · Proyectado vs retrospectivo

Carlos: *cobrar antes a partir de hoy no debe reescribir el pasado.* El motor **no tiene cola** después de 2026-09-01. Carlos-estricto ⇒ **ΔS = 0**.

Tres salidas al último cutoff:

| Opción | Qué hace | Decisión |
| :--- | :--- | :--- |
| (a) Reasignar AR a jun–ago (W3) | Reescribe extractos booked; fabrica M (+7,74 en sonda) | **Prohibida como default** |
| (b) Inventar meses oct–dic | Otro panel, otro algoritmo | **Vetada** |
| (c) Meter en **agosto** lo que habría llegado después | Reescribe un mes; ΔM=0; ΔS visible y pequeño | **Contrato MVP** |

Nombre honesto: **`contrafactual_de_corte`**. Copy de pantalla: *«Esto no es una proyección a 90 días. Es el score si el último mes del extracto hubiera cobrado / gastado / pagado así.»*

`as_of` de `/simulate` fijo a **2026-09-01** en el MVP. No hay `/simulate?month=2026-03-01`: ERP no existe ahí y reconstruir AR as-of es trabajo de B1.

### Tarea 21 · Qué se recompute y qué se congela

- Se recompute: `calculate_scores(bank', erp?, config)` con **el mismo** `ScoreConfig` que `/score`.
- No hay percentiles peer que congelar.
- Prefijo `score[:, :23]` **idéntico** (ya testeado: `test_future_bank_and_erp_values_do_not_change_prefix`).
- `quality` / `classified_share` / `native_share`: **congelados**. Una palanca no mejora el score «clasificando mejor».
- Encender caja o ERP **solo** en `/simulate` y no en `/score` rompe «un solo algoritmo».

### Tarea 22 · Unidad de intervención

FactorWOW quiere clientes. El dato lo permite en facturas (`counterparty_id`). El motor ve **`receipts`**, no facturas, salvo ERP on.

Unidad: **facturas AR concretas** (opcionalmente filtradas por `clientes[]`) → suma de pending adelantado → inyección en `receipts[t=23]` y recálculo de `funding_gap` diario de agosto. El atajo `ΔDSO × ventas diarias` es **solo** la pata de euros, no el canal del score.

### Tarea 23 · Horizonte y doble conteo

- Horizonte de **score:** el endpoint (un mes mutado, ventana L de 3 m diluye).
- Horizonte de **caja:** el euro adelantado deja de ser ventaja cuando llega el `due_date` original, salvo recurrente. Reportar caja como stock liberado **hoy**, no como €/año.
- En (c) no hay mes posterior del que restar el cobro: el doble conteo se evita **en la narrativa**, no en una columna futura.

### Tarea 24 · Composición

Una copia del panel, mutaciones **colapsadas por mutador** (§13.4), una recomputación. No sumar ΔS de palancas sueltas. El combo es del **catálogo ancho**, no del MVP de tres.

**422 `doble_conteo` / `mutuamente_excluyentes` si:**

- opex y «liberar caja» gastando el mismo euro dos veces
- cualquier pareja de facades del mutador **M3** (`refinanciar` / `renegociar_interes` / `leasing_a_cuota_menor`) sobre el mismo servicio
- cualquier pareja **M5** (`bajar_utilizacion` / `amortizar` / `disponer`) sobre la misma línea
- refinanciar + amortizar el mismo servicio
- opex + `ampliar_dpo` sobre el mismo `payment`/`bulk_payment`
- `usar_confirming` + `ampliar_dpo` (o pronto-pago proveedor) sobre las mismas AP
- `adelantar_cobros` + `descuento_pronto_pago` en el mismo request → **422 `mutuamente_excluyentes`** (no `doble_conteo`: son variantes, no hermanas apilables — §13.3)

`ampliar_dpo` **sí entra apilada** en familia **circulante** si hay AP y no hay doble `payment`. **No** entra en el ranking de salud ni se vende el ΔS de L como solidez.

### Tarea 25 · Por qué no gradiente *en este* motor

El argumento del decil está **muerto**. El argumento vivo: kinks, deadband entero, switches, ventanas, clip. Búsqueda = {7, 15, 30} días × {0, 5, 10} % opex × {0, 20, 40} % H, recompute batch.

---

## 6. Cómo sugerir (tareas 26–30)

### Tarea 26 · Driver → palanca

El agente **no maximiza S**. Parte del waterfall. Allowlist de **salud** (`sugerencias[]`); circulante nunca es remedio de L/D (§13.2).

| Driver | Allowlist `sugerencias[]` | Veto duro (nunca remedio de este driver) |
| :--- | :--- | :--- |
| L cae o tiene slack (1.137 / 1.170) | `#1` / `descuento_pronto_pago` si AR; si no `recortar_opex`; opcional `bajar_devoluciones` | `ampliar_dpo`, `usar_confirming`, `disponer_linea`, `vender_inversiones`, inventar caja |
| C ERP (solo si snapshot on y DSO alto) | colateral de `#1` / dto | Alisar cobros para bajar CV |
| D < 0,49 y H material (493; **3** D-primarias) | `refinanciar` / `renegociar_interes` / `leasing_a_cuota_menor`; `bajar_utilizacion`/`amortizar` solo euros si caja off | `disponer_linea`; 682 con D=0,5; H→0 cuando R≈0 |
| M | la de L, **≥2 m** — el contrato a 1 m **no** vende M | Palanca de momentum (no existe) |
| G / F-HHI / prior / score>85 | ninguna de salud | — |

Si la trayectoria **sube** y L ya está al techo (`COMP_0153`): no inventar palanca. Circulante puede listarse aparte si el tesorero lo pide.

### Tarea 27 · Magnitudes discretas (hipótesis ancladas)

`dso_days` **no está** en `scores_monthly.csv` ni en el npz. Mediana reconstruida en 466 `erp_used`: **70,9 d**.

| Palanca | Rejilla | Anclaje |
| :--- | :--- | :--- |
| Cobros | **7 / 15 / 30** días | 30 d ≈ 42 % del DSO típico usable |
| Opex | **5 / 10 %** de `salary`∪`utility` 3 m | Share mediana 17,5 % |
| Refi | **20 / 40 %** de H 3 m | Mediana H 3 m (n=495): 12.879 € |

30 días en un solo mes ⇒ M=0. No presentar 30 d como «cambio de régimen».

### Tarea 28 · Ranking

Lexicográfico, no un ratio esfuerzo. **Dos pistas** (§13.2). Una etiqueta de UI **no** neutraliza el número: el sort codifica la honestidad.

**Salud** (`sugerencias[]` — anclado al driver):

1. `es_aplicable` (A: objeto; B: visibilidad si se pide ΔS)
2. Allowlist del driver (T26) — si no está, fuera de esta pista
3. `familia_efectiva=salud` — DPO / confirming / disponer / vender_inversiones **no**
4. Honesta (C: no HHI float, no factoring sin coste, no amortización one-shot como D+, no reescribir W3)
5. `delta_score` de **recompute**
6. `caja_liberada_eur` si hay AR (desempate; no caja de DPO)
7. Coste supuesto — desempate; `id` para determinismo

**Circulante** (`opciones_circulante[]`):

1. `es_aplicable`
2. `familia_efectiva=circulante`
3. Orden **solo** por `caja_liberada_eur` — `delta_score=null` en esta lista (el recompute, si se muestra, va en `efecto_score_informativo` con `prohibido_ordenar: true`)
4. Coste / prima — desempate

Veto post-sim por mutación (`origen_delta_L ∈ {retraso_gastos, confirming_desplaza_ap, caja_inyectada}` ⇒ circulante). `recortar_opex` no dispara el veto.

Esto **no mata DPO**: la aparta del sort de salud. Mata vender L↑ de retrasar pagos como solidez. Refi cosmética muere en el paso 1.

### Tarea 29 · Empresas sanas (score > 85)

| Umbral | Observed endpoint |
| ---: | ---: |
| > 85 | **3** (`COMP_0194` 88,92, `COMP_0791` 87,36, `COMP_0184`) |
| > 80 | 9 |
| > 75 | 24 |

La rama B10.1 «optimizar excedentes de tesorería» es **académica**: no hay `cash_known`. Copy: *no hay nada que simular*, no un producto de cash pooling.

### Tarea 30 · Casos de demo

No están Northbrook/Velasco por nombre. Candidatos de trayectoria del panel:

- **Mejora:** `COMP_0153` — 23,03 → **82,13**. L 0,018→0,973. 24 m tx. Sin AR, D=0,5. No usar `COMP_0791` (87,36, rama >85).
- **Deterioro:** `COMP_0176` — 74,66 → **5,17** (mínimo del universo). Receipts 3 m = 0. AR pending = 0. H 3 m = 51 €. Opex real irrisorio. `COMP_1120` es clon de grupo; no.
- **Palanca con euros:** `COMP_0031` — bank 65,53 / ERP 52,32 (−13,20 al conectar ERP). AR nativa **2.085.554 €**, DSO reconstruido **194 d**. Caja 7/15/30 = **76.071 / 163.010 / 328.019 €**. Opex 5/10 % = 34k / 67k; refi 20/40 % = 19k / 39k (D=0,427). Caveat: **10 meses** de tx, m6 era prior. Entra porque `history_ready ∧ ~is_prior`, no porque esté en las 370 completas.

`COMP_0037` (ERP +8 pts) tiene DSO ≈ 0,46 d: no hay cobros que adelantar. No.

---

## 7. Puente a euros (tareas 31–33)

### Tarea 31 · Caja liberada

Fórmula PRODUCTO `ΔDSO × facturación diaria` es **liberación de circulante** bajo ventas estables, no cobro ni beneficio anual (Carlos §11.3). Permitir `null` + motivo.

| Universo | n |
| :--- | ---: |
| AR viva **y** ventas diarias (factura 90 d o cobros) | **635** |
| …exigiendo factura emitida (alineado DSO ERP) | **576** |
| …en cohorte 24 m | 229 / 195 |
| 67 solo-recibidas y 501 sin ERP | **null** |

En `COMP_0031` los 7/15/30 días sobre stock AR son contables. Moneda demo palancas ~**90 % EUR** (94 % en 24 m). No sumar GBP+EUR.

### Tarea 32 · Coste de la palanca

- Pronto pago: **no hay campo** en facturas ni movimientos. Tasa = supuesto. Con tasa>0 se llama al id `descuento_pronto_pago` (no un campo en `#1` — §13.3).
- Refinanciar: comisiones y tipo de la **oferta**, no del CSV.
- Alargar DPO (familia circulante, no cementerio): pierde descuentos de pronto pago de proveedor. Eso es **coste supuesto** en pantalla, no un motivo para borrar el id.

El delta bruto sin coste miente. `caja_liberada` neta = bruta − descuento − comisiones, o se muestran **separadas**.

### Tarea 33 · Pata bps / € año

| Fuente | Qué hay | Por qué no es curva |
| :--- | :--- | :--- |
| `debt_schedule_config` | 87 tipos, 40 empresas, mediana 3 %, rango 0–11 %. 58 fijos / 29 variables / 6 empresas con ambos. 81/87 next ya pasadas | Mezcla spread y tipo; n minúscula; fechas muertas |
| Implícito `interest_charge / outstanding` TTM | 196 empresas | Mediana **0,33 %**; 112 < 50 bps; 8 > 100 %. Stock snapshot × flujo trailing. 236 pagan interés **sin** ficha de deuda |

**Retirar** `f(S)`. `delta_bps` y `eur_año` = `null` con `motivo=curva_score_tipo_retirada`, salvo que la palanca #3 traiga `tipo_escenario` explícito. Entonces:

```text
ahorro_intereses = principal_afectado × (tipo_base − tipo_escenario) × días/base
ahorro_neto = ahorro_intereses − comisiones − descuentos
```

Eso es escenario, no causalidad del dataset.

---

## 8. Monitor (tareas 34–35)

### Tarea 34 · Qué alerta merece palanca

No hay clase `Monitor` ni estados `TORCIENDOSE` / `BACHE` en Python. `GET /alerts` es contrato, no código. `real_world_anticipation_validated=false`. Los **8 meses** de `stress_control` son un fixture sintético (recibos 120→suelo 5); el TeX ya avisa que no son anticipación general. El recomendador pone `meses_anticipacion: null`.

Orquestar what-if de **salud** solo si el driver es persistente y honesto. DPO no se dispara desde una alerta de L (§13.2); eso no es «nunca simular DPO».

| Alerta | Palanca | Nunca |
| :--- | :--- | :--- |
| Deterioro de cobros (R↓ / DSO alto si ERP) | `adelantar_cobros` / `descuento_pronto_pago` | Spike 1 m |
| Quema de liquidez (gastos `salary`/`utility`) | `recortar_opex` | Recortar tax/cuotas |
| Spike de `debt_service` observado | `refinanciar` / `renegociar_interes` | R≈0, D ya 0,5 |
| Bache 1 mes | **silencio** | El motor ya pone M=0; ~50 % revierte al mes siguiente |
| HHI / caja / prior / S>85 | alerta o silencio | what-if de **salud** |
| Plazo proveedor / DPO | no se orquesta desde alerta de L | venderlo como solidez; el what-if de **circulante** sí, si el tesorero lo pide |

### Tarea 35 · Falsas alarmas vs sugerencias

Sugerir palanca solo si:

```text
history_ready  ∧  ¬is_prior  ∧  ( M_t < 0  ∨  ΔL_{t, t−3} ≤ −0,23 )
```

`X = −0,23` en L es el **p10 empírico** de ΔL a 3 meses (14.490 celdas observed) ≈ **−11,7 puntos** de liquidez. `M < 0` ya implica 2–3 meses sobre deadband 0,02.

Para el inbox de alertas (más estricto que el what-if): recortar a `M < −0,10` (umbral de `stress_control`).

---

## 9. Contrato congelado (tareas 36–38)

### Tarea 36 · `GET /palancas` y `POST /simulate`

Rutas de PRODUCTO se conservan. La semántica manda sobre el path.

**`GET /palancas?entity_id=`** → catálogo **ancho** (ids §12 + §13; `alisar_calendario` no emite). «Cerrado» = vocabulario conocido, **no** MVP+cementerio. Cada fila: `familia` (`salud`|`circulante`), `es_aplicable`, `excluido_con`, `mutator_id` interno. 404 solo si la entidad no existe. Todo inaplicable = 200 con `es_aplicable=false` (filtro A). n=19 no es 404.

**`POST /simulate`** → dos `calculate_scores` (referencia y escenario), mismo `config`, si la familia es salud y hay adaptador. Palanca inaplicable → **422** + `motivo_rechazo`, no un ΔS fingido. Entidad desconocida → 404. Determinismo: misma entrada ⇒ misma salida (RNF-1).

`ampliar_dpo` / `usar_confirming` / `disponer_linea` con objeto vivo **no** son 422 de cementerio: simulan familia circulante (`delta_score=null` en la lista de opciones; euros sí). `adelantar_cobros` + `descuento_pronto_pago` juntos → 422 `mutuamente_excluyentes` (§13.3).

Cinco claves de PRODUCTO, con nulos honestos. Sin descuento → id `#1` (sin `tasa_descuento`). Con descuento → id propio:

```json
{
  "entity_id": "COMP_0031",
  "as_of": "2026-09-01",
  "modo": "contrafactual_de_corte",
  "model_version": "<hash de score_engine.py + score_data.py>",
  "palancas": [
    {
      "id": "descuento_pronto_pago",
      "magnitud": { "dias": 15, "clientes": ["COUNTERPARTY_…"], "tasa_descuento": 0.02 }
    }
  ],
  "familia": "salud",
  "score_nuevo": "<salida de calculate_scores>",
  "delta_score": "<escenario − referencia en t=23>",
  "caja_liberada_eur": "<pending adelantado × (1 − tasa); bruta y coste separados>",
  "delta_bps": null,
  "eur_año": null,
  "warnings": [
    "retrospectivo_un_mes",
    "momentum_no_activado",
    "caja_es_circulante_no_beneficio",
    "curva_score_tipo_retirada",
    "descuento_supuesto"
  ],
  "assumptions": {
    "mapear_a_receipts": true,
    "tasa_descuento": 0.02,
    "no_reescribe_prefijo": true
  }
}
```

Si se exige Carlos-estricto («solo fechas ≥ corte»): `delta_score=null` + `motivo=sin_cola_futura_en_el_motor`. El MVP **no** elige eso porque el producto pide un número; el número es (c) y se etiqueta.

### Tarea 37 · Supuestos visibles en pantalla

Obligatorios según palanca:

1. Esto **no** es proyección a 90 días; es contrafactual del último mes del extracto.
2. No se reescribe el libro 2024-09…2026-07.
3. Δ momentum = 0 (un mes).
4. Caja liberada = circulante, no cobro ni beneficio anual.
5. ERP off ⇒ DSO-only no mueve el score; el número sale de `receipts`.
6. Descuento pronto pago = supuesto (no hay campo); si tasa&gt;0, id `descuento_pronto_pago` (no campo en `#1`).
7. Refinanciar = oferta (tipo, plazo, comisiones, fecha), no el cuadro de 87 filas.
8. Dataset sintético: no se afirma impago real (RF-B12.6).
9. `delta_bps` ausente salvo oferta explícita.
10. Circulante (DPO/confirming/disponer): *caja, no salud*; no ordenar por ΔS.
11. Caja observada apagada: palancas M5/M9 sin ΔS fingido.

### Tarea 38 · Dependencias con el núcleo

**Congelar (Pedro necesita que no cambie el significado):**

- Firma `calculate_scores(bank, erp=None, config=None)` y nombres de bloques (`liquidity_points`, … `is_prior`, `cash_known`, `erp_used`, `debt_service_observed`).
- Default ERP off y cash off. Encenderlos en `/simulate` y no en `/score` está prohibido.
- `debt_service` = categorías `debt_repayment` ∪ `interest_charge`, no `outstanding`.
- Ventana txs `[start, end)` con `end` exclusivo.
- Causalidad: mutar t no cambia el prefijo.

**Pedro puede mockear:** HTTP, catálogo, euros con nulls, `GET /palancas`, fixtures offline de `COMP_0153` / `COMP_0176` / `COMP_0031`, un stub de `calculate_scores` rotulado como stub.

**Hay que pactar con Carlos/Antonio:**

1. El adaptador `adelantar_cobros` → `receipts` + `funding_gap` (sin eso #1 no mueve S).
2. No implementar B2 (percentiles) a mitad de `/simulate` sin avisar: cambiaría la coartada, no el método (sigue siendo recompute).
3. **Caja (§13.1):** `/score` y `/simulate` siguen con `cash_known=0`. `amortizar_linea_con_caja` / utilización / disponer / vender_inversiones **ya** están en el catálogo ancho (gate A); con caja apagada → `delta_score=null` / euros no-score, **no** «cementerio por cobertura». Encender `cash_balance` en ambos endpoints = **bump de `model_version`** y reabrir honestidad (amortizar un mes de H empeora D) — no un desbloqueo silencioso.
4. Si construyen ERP histórico as-of (B1), entonces sí existiría «DSO en mes 18». Hoy no.

---

## 10. Las 38, una línea cada una

| # | Conclusión |
| ---: | :--- |
| 1 | Mutar foto de corte (AR pending, expenses, H), no el ledger booked ni balances sumados. |
| 2 | Cobros/opex en cientos de empresas; línea 206; factoring 19; cuadro 40. |
| 3 | `payment_date` pending/overdue es placeholder; DSO mes 18 imposible con el motor actual. |
| 4 | Clientes por `counterparty_id` de factura (409 empresas con ≥5); cruce con `company_id` = 0. |
| 5 | Deuda del score = banco (716), no catálogo (378) ni schedule (40, 81/87 next muertas). |
| 6 | Caja = checking; `available` vacío; motor `cash_known=0`; 34/206 cubren la línea con corriente. |
| 7 | 25 % txs sin categoría; opex solo `salary`∪`utility`. |
| 8 | L 50 / C 30 / D 20 pts + M/G/F; L es el 84 % de la varianza real. |
| 9 | ERP y caja apagados; DSO no mueve el histórico. |
| 10 | Hill, tanh, deadband, switches, clip: no gradiente. |
| 11 | DPO sube L; amortizar empeora D; G unilateral; factoring hincha cobros. |
| 12 | M pide ≥2 meses y t≥5; 1 mes ⇒ ΔM=0. |
| 13 | 116 priors (S=50): palancas inaplicables. |
| 14 | Persistencia +20 % cobros = +7,74; spike = +1,35; caja hipotética = +11,63. |
| 15 | Candidatas = catálogo ancho (§12+§13); alisar/inyectar fuera; descuento = id propio excluyente. |
| 16 | Maquillaje: DPO/confirming ≠ salud (sí circulante); HHI float fuera (mix sí); factoring n=19 entra con coste; utilización/amortizar = euros no-score mientras caja off. |
| 17 | `es_aplicable` = objeto + visibilidad; **no** bit «cementerio». 682 D=0,5 ⇒ refi no-op. |
| 18 | Cobros 1 m: L↑, C puede bajar (CV), G cosmético, M=0. |
| 19 | MVP **demo** = cobros + opex + refi. Catálogo producto = ancho + `es_aplicable`. |
| 20 | Contrato = contrafactual de corte (mes 23). Proyección pura ⇒ ΔS=0. |
| 21 | Recompute `calculate_scores`; quality congelada; un solo algoritmo. |
| 22 | Facturas AR → receipts; euros pueden usar ΔDSO×ventas. |
| 23 | Score en endpoint; caja como stock; ventaja se apaga al vencimiento original. |
| 24 | Una copia, mutadores colapsados (§13.4); 422 si doble conteo / mutuamente excluyentes. DPO apilable en circulante. |
| 25 | Jacobiano 0 c.t.p.; el decil peer es un argumento caducado. |
| 26 | Anclar al driver; L→cobros/opex; D→refi; veto DPO/confirming/disponer como remedio de L. |
| 27 | Rejilla 7/15/30 d, 5/10 % opex, 20/40 % H. |
| 28 | Dos pistas: salud (ΔS) y circulante (caja); DPO no ordena por ΔS. |
| 29 | Score>85: 3 empresas. Rama excedentes académica. |
| 30 | Demo: `COMP_0153`, `COMP_0176`, `COMP_0031`. |
| 31 | Caja liberada sí (635 empresas); null si no hay AR/ventas. |
| 32 | Descuento = id propio con tasa; DPO pierde dto proveedor = coste de circulante. |
| 33 | Curva score→tipo **retirada**; bps solo con oferta. |
| 34 | What-if **salud** = cobros/opex/H; DPO no desde alerta L; circulante aparte. |
| 35 | Umbral: M<0 o ΔL 3 m ≤ −0,23; `meses_anticipacion=null`. |
| 36 | `/palancas` catálogo **ancho**; 422 si inaplicable. DPO con AP = circulante. |
| 37 | Lista de supuestos de pantalla (§9). |
| 38 | Congelar firma; mapa cobros→receipts; caja off (§13.1); mockear HTTP. |

---

## 11. Qué no se ha hecho (a propósito)

- No hay código de `IPalanca`, ni FastAPI, ni front.
- No se ha reentrenado ni retocado `ScoreConfig`.
- No se afirma que `COMP_0153` / `COMP_0176` sean Northbrook / Velasco: son las trayectorias reales del panel.
- No se ha medido anticipación real sobre las ~370 de 24 meses (`real_world_anticipation_validated=false`).
- El dataset en `dataset/` **no se versiona**.

Cuando toque implementar: ver cierre de §13 (primer corte `#1` sobre `COMP_0031`; luego catálogo ancho + mutadores + dos pistas; caja apagada).

---

## 12. Addendum · Producto completo, no un MVP de tres palancas

**Fecha del addendum:** 2026-09-19. Corrige el sesgo de las secciones 1 y 19: ahí se cortó el catálogo por **cobertura** (factoring 19, línea 206, cuadro 40). Eso es un criterio de *demo en 2:30*, no de producto. En un TMS el 1,5 % de la cartera que tiene factoring **es** el caso de uso; la palanca se implementa y `GET /palancas` devuelve `es_aplicable=false` en las otras 1.267.

Tres filtros distintos, no uno:

| Filtro | Pregunta | Si falla |
| :--- | :--- | :--- |
| **A. Objeto** | ¿Existe el parámetro en *esta* empresa (AR, línea, factoring, HHI, …)? | `es_aplicable=false` + motivo. La Strategy **sí se escribe**. |
| **B. Visibilidad** | ¿El motor ve la mutación, o hay que mapear (receipts, caja, H)? | Se declara el adaptador. Sin él, ΔS=0 y no se finge. |
| **C. Honestidad** | ¿Mejora tesorería o solo el número? | Familia `salud` vs `circulante` + ranking (§13.2). La etiqueta de pantalla **no** basta: el sort codifica la honestidad. |

`is_prior` (116) sigue siendo filtro A global: ninguna palanca.

### 12.1 Las ocho de PRODUCTO, reabiertas (post-§13)

| Palanca | Gate | Mutador | Familia | Cómo no mentir |
| :--- | :--- | :--- | :--- | :--- |
| **Adelantar cobros / reducir DSO** | AR viva (~669) | M1 `ar_a_receipts` | salud | Pending → `receipts`+gap. 1 mes ⇒ no vender M. |
| **Descuento pronto pago** | AR viva + `tasa∈(0,1)` | M1 (superconjunto) | salud | **Id propio.** Siempre adelanta + haircut. **Nunca** junto a `#1` (422 `mutuamente_excluyentes`). Coste separado de caja bruta. |
| **Recortar opex** | `salary`∪`utility` (~1.157) | M2 | salud | Whitelist. Nunca tax/SS/`fee`/`payment`. |
| **Refinanciar** | H material ∧ D&lt;0,5 (~493) | M3 | salud | Bajar H **recurrente** + oferta. |
| **Ampliar DPO** | AP viva (~755) | M4 | **circulante** | Retrasar `payment`/`bulk_payment`. Sort **solo** por `caja_liberada_eur`; `delta_score=null` en lista. Nunca remedio de L. |
| **Bajar utilización de línea** | LOC + ratio alto (206) | M5 `delta_dispuesto&lt;0` | salud* | Hoy: euros no-score (`cash_known=0`, §13.1). |
| **Sustituir factoring** | `factoring` (19) | M6 | salud | Coste / deshinchar `collection` visible. n=19 = gate A. |
| **Reducir concentración** | HHI usable ∧ ≥2 clientes | M7 mix | salud | Sustituir mix por `counterparty_id`. Nunca el float HHI. |

\*Salud* solo cuando haya ΔS real (caja on + versión bump). Mientras caja off → canal euros / `delta_score=null`.

`amortizar_linea_con_caja` = M5 con `delta_dispuesto&lt;0` y checking≥euros. Misma familia/visibilidad que utilización (§13.1 / §13.4).

### 12.2 Extras (post-§13)

| `id` | Mutador | Familia | Gate | Nota |
| :--- | :--- | :--- | :--- | :--- |
| `usar_confirming` | M8 `confirming_fee` | **circulante** | confirming (70) + AP | **No** bajar/desplazar expenses. Fee (+ H si vence en t=23). Caja preservada = euro no-score. ΔS&gt;0 por E↓ ⇒ 422 (§13.7). |
| `disponer_linea` | M5 `delta_dispuesto&gt;0` | **circulante** | LOC con holgura | Mismo mutador que bajar/amortizar, signo +. Copy: *liquidez ahora, deuda después*. |
| `vender_inversiones` | M9 | **circulante** | investment con saldo | Euros no-score mientras caja off. |
| `ofrecer_pronto_pago_proveedor` | M10 | salud/caja | AP viva | Inverso de DPO; 422 con M4 misma AP. |
| `bajar_devoluciones` | M11 | salud | refunds altos | C vía `refund_score`. |
| `renegociar_interes` | M3 scope=`interes_only` | salud | `interest_charge` (470) | Strategy fina; 422 con otra M3 mismo H. |
| `leasing_a_cuota_menor` | M3 scope=`leasing_renting` | salud | leasing/renting | Strategy fina; misma mutación H. |

**DROP:** `alisar_calendario` — sonda: ΔS legal mediana ~0,03 / p90 ~0,38; reescribe timing booked; fuera del catálogo (§13.5). Timing honesto = colateral de cobros (gap al mapear receipts).

**Grupo / filiales:** solo con supuesto «`transfer` intragrupo» + mismo `group_id` + `Other (customer-defined)`; aproximado (RF-B1.13). Si no se defiende, no entra.

**No extraer:** tax/SS, equity, peer, quality, curva score→tipo, priors, `inyectar_caja_observada`.

### 12.3 Lo que sigue fuera — y no es por n pequeño

| Queda fuera | Por qué de verdad |
| :--- | :--- |
| Presentar DPO/confirming/disponer como *solidez* | Motor puede subir L; ranking de salud los veta (§13.2). Catálogo sí, como circulante. |
| Mutar el escalar HHI | Gaming. Mix de clientes sí. |
| Reescribir jun–jul para fabricar M | Mentira de trayectoria. |
| Inventar `cash_balance` solo en `/simulate` | Teatro de ΔS; un solo algoritmo (§13.1). |
| Meter checking→`cash_balance` «sin tocar la fórmula» | **Falso.** Caja **sustituye** L (84 % var; sonda +11,6). Es camino C de producto, no adaptador. |
| `alisar_calendario` | ΔS &lt;1 pt + rewrite ledger (§13.5). |
| `delta_bps` empírico | Curva retirada. Oferta explícita sí. |
| Palanca genérica «sube el score» | Allowlist por driver; dos pistas. |

### 12.4 Adaptadores reales (corregido §13.1)

**Adaptadores de capa intermedia (sin reescribir `calculate_scores`):** pending AR → `receipts` + `funding_gap`; retrasar/adelantar `payment`/`bulk_payment`; ERP snapshot en el corte (flag ya existente). **Caja no entra en este saco.** Meter la foto checking de `balances` en `cash_balance` **activa el canal ya codificado que sustituye L** (no la mezcla): L es ~84 % de la varianza; sonda cash=200 ⇒ ~+11,6 pts; reescalaría ~1.267 empresas. **Decisión congelada (camino A):** `/score` y `/simulate` con `cash_known=0`. Palancas M5/M9 reportan euros / tesorería **no-score** (`delta_score` nulo). **Prohibido** inventar caja solo en `/simulate`. Si Embat exige score-visibilidad de caja: camino C (opt-in en ambos endpoints, bump de versión, dual `L_bank` vs `L` cash) — no se vende como «sin tocar la fórmula». Un blend caja↔flujos (camino D) sí exige cambio de núcleo.

Con eso: **un Strategy por facade + pocos mutadores + predicado por empresa + dos pistas de ranking**. El agente no opina: recorre aplicables, simula, ordena. Que factoring solo salga en 19 fichas es correcto.

---

## 13. Addendum · Siete problemas y soluciones (2026-09-19)

Un subagente por problema. Veredictos congelados abajo. Las secciones 1–12 anteriores están sincronizadas con esto (T15–T19, T24, T26, T28, T32, T34, T36, T38, §10, §12).

| # | Problema | Solución |
| ---: | :--- | :--- |
| 1 | «Sin tocar la fórmula» + checking→caja | **Camino A:** caja off en ambos endpoints. Palancas de línea/inversión = euros no-score. Encender caja = release de núcleo, no adaptador Pedro. |
| 2 | Etiqueta no neutraliza ΔS (DPO…) | **Dos pistas:** `sugerencias[]` (salud, sort ΔS) y `opciones_circulante[]` (sort caja; ΔS=null). Hard veto + allowlist. |
| 3 | Descuento vs `#1` | **C:** id propio = adelanto + tasa&gt;0; `#1` = tasa 0; 422 `mutuamente_excluyentes`. Toggle UI cambia `id`. |
| 4 | 16 ids ≈ 9 mutaciones | **Opción 3:** muchas Strategy (OCP) sobre 9 mutadores; 422 a `(mutator_id, resource_key)`. |
| 5 | `alisar_calendario` sin medir | **DROP.** Sonda ΔS legal &lt;1 pt; rewrite ledger. Timing = colateral de cobros. |
| 6 | Secciones stale | Sincronizadas en este documento (principio: catálogo ancho + gates; cementerio ≠ cobertura). |
| 7 | Confirming = DPO | **Entra** id propio, circulante; expenses **intocados**; fee (+ H si vence t=23); 422 si E↓. |

### 13.1 Problema 1 · Caja y la fórmula

`liquidity = where(cash_used, 0.5*runway+0.5*coverage, liquidity_bank)`. Caja **sustituye** L. L = 84 % de la varianza. Sonda cash=200 ⇒ +11,63.

- **A (congelado):** `cash_known=0` en `/score` y `/simulate`. «Sin tocar la fórmula» = mutar inputs que el motor ya lee en modo bank (receipts, expenses, H, gap) + AR→receipts.
- **B rechazada:** caja solo en simulate = teatro (T21).
- **C diferida:** opt-in en ambos + bump versión + dual L — si Embat lo exige; no es «adaptador silencioso».
- **D:** blend = cambio de núcleo (Carlos/Antonio).

Bajo A: `bajar_utilizacion`, `amortizar_linea_con_caja`, `disponer_linea`, `vender_inversiones` → `delta_score=null` / canal euros.

### 13.2 Problema 2 · Ranking

Familia fija en Strategy + veto post-sim por mutación. Concatenar las dos listas y reordenar por ΔS = **bug de front**.

Si solo DPO aplica: `sugerencias=[]` + copy *nada que recomendar para la salud*; `opciones_circulante` visible. **Prohibido** promocionar DPO como `#1` del score.

### 13.3 Problema 3 · Descuento

```text
descuento_pronto_pago  ⊃  adelantar_cobros
   mismo pending → receipts + gap
   + receipts' = P × (1 − tasa), tasa ∈ (0, 1)
adelantar_cobros       ≡  tasa = 0 (campo tasa ausente/prohibido)
```

`GET /palancas`: ambos si hay AR; `excluido_con` mutuo; `reemplaza`. Demo WOW sigue en tres actos; si se enseña dto, se llama al id propio.

### 13.4 Problema 4 · Mutadores

| M | mutator_id | Facades |
| :---: | :--- | :--- |
| M1 | `ar_a_receipts` | `adelantar_cobros`, `descuento_pronto_pago`, alias `reducir_dso` |
| M2 | `opex_whitelist` | `recortar_opex` |
| M3 | `bajar_h_recurrente` | `refinanciar`, `renegociar_interes`, `leasing_a_cuota_menor` |
| M4 | `retrasar_ap` | `ampliar_dpo` |
| M5 | `caja_linea` | `bajar_utilizacion`, `amortizar_linea_con_caja`, `disponer_linea` (signo) |
| M6 | `factoring_a_linea` | `sustituir_factoring` |
| M7 | `mix_receipts` | `reducir_concentracion` |
| M8 | `confirming_fee` | `usar_confirming` |
| M9 | `liquidar_investment` | `vender_inversiones` |
| M10/M11 | auxiliares | pronto-pago proveedor / bajar devoluciones |

B8.1 se cumple: una clase Strategy por facade; `aplicar` delega al mutador. Añadir palanca = nueva Strategy; si reutiliza mutador, cero cambios en el compositor.

### 13.5 Problema 5 · Alisar calendario

Sonda (gap→0 en t=23): sintético extremo +0,76; panel real mediana **0,03** / p90 **0,38** / máx **0,81**. Techo teórico F = 8 pts; Hill satura. Mover `tx.date` booked en mes 23 **no** es `contrafactual_de_corte`. **Fuera del catálogo** (candidato research si algún día se remoldea `daily_net` sin pretender rewrite y con ΔS material).

### 13.6 Problema 6 · Sync documental

Principio: catálogo **ancho** + gates A/B/C; las 3 del WOW = orden de demo; DPO/confirming viven como circulante; descuento = id excluyente; mutadores colapsados; alisar drop; caja no desbloquea en silencio. Aplicado a T15–T19, T24, T26, T28, T32, T34, T36, T38, §10, §12.

### 13.7 Problema 7 · Confirming

Modelo: banco paga al proveedor hoy; empresa debe al banco (principal + fee); checking no sale hoy.

**Prohibido:** bajar `payment`/`bulk_payment`; desplazarlos (eso es DPO). **Lícito:** no tocar expenses; añadir `fee`; H solo si la cuota cae en t=23; `caja_liberada_eur` = euro no salido (no-score bajo P1). Familia circulante. 422 con `ampliar_dpo` / pronto-pago AP / `disponer_linea` sobre el mismo euro. ΔS&gt;0 por E↓ ⇒ 422.

---

Cuando toque implementar: primer corte = `POST /simulate` de `adelantar_cobros` (mapa a receipts) sobre `COMP_0031`, fixture offline, claves PRODUCTO con `delta_bps: null`. Luego el catálogo ancho con mutadores M1–M9, dos pistas de ranking, y caja **apagada** hasta un release explícito del núcleo.

