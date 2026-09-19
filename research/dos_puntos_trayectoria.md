# Dos puntos en la trayectoria · especificación de implementación

**Para:** quien implemente (Pedro / motor / front)  
**Fecha:** 2026-09-19  
**Rama:** `feat/dos-puntos-trayectoria`  
**Qué es:** contrato de producto + receta exacta. No es código.  
**Research de fondo:** `research/momento_en_que_se_tuercen.md` (por qué estas dos marcas y no un índice nuevo).  
**No reabrir:** umbrales del monitor (`momentum_threshold=0,10`, persistencia 3, frontera 60). No es PD. Caja y ERP siguen off en el score oficial.

---

## 0. Qué se entrega

En el gráfico de trayectoria de una empresa hay **como máximo dos puntos y un texto**. Nada más.

| Marca | Nombre interno | Qué significa | Reloj |
| :--- | :--- | :--- | :---: |
| **Punto rojo** (relleno) | `punto_confirmacion` | Aquí se jodió de verdad: el monitor confirmó un giro persistente | `t_alerta` |
| **Punto hueco** (anillo), a la izquierda del rojo si existe | `punto_camino` | Aquí, si no hacías nada, a 6 meses ya se veía feo | `t_anticipacion` |
| **Un texto** | `texto_familia` | Salud (el régimen malo sigue) o circulante (el colchón vence) | pie de foto |

Si el hueco no existe, o cae en el mismo mes o **después** del rojo, **solo se pinta el rojo**. Nunca tres marcas. Nunca una cuarta curva “índice de torcimiento”. Nunca P10/P50/P90 como “el momento”.

El punto hueco se pinta sobre la curva **observada** en `(as_of del origen t, score observado de t)`. No se pinta en el futuro. El número `Ŝ_{t+6}` es un test, no una coordenada del gráfico.

---

## 1. Por qué esto (para no deshacerlo a mitad)

El score `S_t = f(banco_t)` es una foto. El monitor ya dice cuándo esa foto lleva **tres meses** torciéndose (`TORCIENDOSE` / `DETERIORO`). Eso es el rojo.

Un DSO que sube, un opex de expansión o un stock de facturas aplazadas **aún no** tienen por qué haber tumbado `S_t`. El hueco pregunta el dual del `/simulate`:

> Si **no** reviertes lo que ya pasó, ¿el score a 6 meses de esta fotocopia ya es malo aunque hoy aún no?

Salud y circulante no se proyectan igual (detalle en §5). Mezclarlos es la trampa que el catálogo de palancas ya prohibió: el motor **premia** pagar más tarde (este mes salió menos dinero); un tesorero no llama a eso estar más sano.

Las hipótesis que **no** entran como marca: pendiente que “baja mucho”, cruce de signo +→−, N decisiones, liquidez a 0, peor factor como fecha, combinación ponderada. El peor factor y la liquidez sí pueden **escribir el texto** del rojo si no hay hueco previo. Ver §8.

---

## 2. Taxonomía: no inventar un `DETERIORO` paralelo

### 2.1 Estados observados (congelados)

Siguen saliendo de `classify_states` (`algorythm/score_states.py`). **No se añaden hermanos a `NEGATIVE_STATES`.**

| `state` | Uso en este sistema |
| :--- | :--- |
| `EVALUACION_PENDIENTE` | Sin puntos. |
| `ESTABLE` | Puede llevar hueco (`outlook ≠ NINGUNA`). |
| `BACHE` | Ámbar, provisional. **No es el rojo.** Puede convivir con hueco. |
| `TORCIENDOSE` | Rojo si es la **primera** entrada negativa del episodio (`base_health ≥ 60`). |
| `DETERIORO` | Rojo si es la primera entrada negativa, o si se pasa de `TORCIENDOSE` → `DETERIORO` (ya lo cuenta `directional_event_matrix`). |
| `MEJORANDO` / `RECUPERACION` | Sin rojo de deterioro. Fuera de alcance de este spec. |

`NEGATIVE_STATES = ('TORCIENDOSE', 'DETERIORO')` no se toca. Telegram `ALTA`/`MEDIA` sigue saliendo solo de esas entradas.

Bandas de nivel (`SOLIDA` / `INTERMEDIA` / `DEBIL`, cortes 70/40) y `COBERTURA_LIMITADA` / `SIN_EVIDENCIA` siguen siendo otro eje. No las uses como el punto.

### 2.2 Eje nuevo: `outlook` (perspectiva a 6 meses)

Campo **paralelo** a `state`, no un estado más.

| `outlook` | Significado |
| :--- | :--- |
| `NINGUNA` | El test a 6 meses no dispara en ese `t`. |
| `SALUD_ADVERSA` | Dispara el camino salud (§5.3). |
| `CIRCULANTE_ADVERSO` | Dispara el unwind de circulante (§5.4). |

Si disparan los dos el mismo `t`, **un solo** `outlook`: el de `Ŝ` más bajo. Un solo hueco. Un solo texto.

`outlook` **no** entra en `NEGATIVE_STATES`. **No** dispara alerta `ALTA`. **No** entra en el TOP 5 de deterioro. Como mucho severidad `INFORMATIVA` / watch. Si lo metes en `TORCIENDOSE`, rompes el techo de 1 falsa alarma/año y mientes: el score aún no ha confirmado el giro.

### 2.3 Badge en el anillo (front)

El anillo sigue pintando `state`. Empresa `ESTABLE` con hueco: anillo verde/estable + badge aparte “perspectiva 6 m · salud|circulante”. **No** cambiar el color del anillo a naranja.

No añadir el estado `PERSPECTIVA_ADVERSA` en v1. Si más adelante el front no puede vivir sin un valor de `state`, sería provisional como `BACHE` y **fuera** de `NEGATIVE_STATES`. No es este spec.

### 2.4 Familias (el texto)

La misma del catálogo `algorythm/levers_catalog.py`:

| Familia | Qué es | Palancas | Cómo se proyecta |
| :--- | :--- | :--- | :--- |
| **salud** | Solidez: cobros, opex, deuda, concentración, refunds | `adelantar_cobros`, `recortar_opex`, `refinanciar`, `bajar_devoluciones`, `reducir_concentracion`, … | El régimen **nuevo se queda** 6 meses |
| **circulante** | Comprar tiempo: DPO, confirming, línea | `ampliar_dpo`, `usar_confirming`, `disponer_linea`, … | El stock **se deshace** (la AP vence). `delta_score=null` en simulate |

Nunca un texto que trate las dos como lo mismo.

---

## 3. Contrato de datos (qué calcula el dominio)

Nuevo módulo sugerido: `algorythm/score_outlook.py`. Lo llaman el monitor, la API y el bot. El front **no** recalcula `Ŝ`.

### 3.1 Por empresa (serie mensual, misma malla que `score`)

```
outlook[t]            ∈ {NINGUNA, SALUD_ADVERSA, CIRCULANTE_ADVERSO}
outlook_score[t]      float   # Ŝ_{t+6} de la familia ganadora; NaN si NINGUNA
outlook_base_score[t] float   # Ŝ_base_{t+6}
punto_confirmacion    { as_of: date|null, state: TORCIENDOSE|DETERIORO|null, score: float|null }
punto_camino          { as_of: date|null, outlook: ..., score_observado: float|null, score_proyectado: float|null }
texto_familia         { familia: salud|circulante|null, texto: str }
```

`punto_confirmacion.as_of` = primer `as_of` con `directional_event_matrix == -1` (entrada a negativo). Es el mismo evento que hoy alimenta `alerts_history` en deterioro. **No retrodatar** al mes 1 de la racha de momentum: el punto es el mes que **completa** los 3 meses.

`punto_camino.as_of` = mínimo `t` elegible con `outlook[t] ≠ NINGUNA` **y** `state[t] ∉ NEGATIVE_STATES` **y** (`punto_confirmacion` es null **o** `t < punto_confirmacion`).

Si después del cálculo `punto_camino.as_of >= punto_confirmacion.as_of`, anular el hueco (`as_of=null`). El 2 es *antes* del 1, o no está.

### 3.2 El texto (uno)

Prioridad:

1. Si hay hueco → familia = `punto_camino.outlook` mapeado a `salud` / `circulante`.
2. Si solo hay rojo → familia = mapeo del peor bloque **firmado** del Δ a 3 meses (como `make_alert`, pero `arg min` de Δ, no `|Δ|`), sin `momentum_points` ni `clipping_points`. Liquidez/cobros/deuda/growth/fragility → `salud`, salvo que el unwind de circulante en ese mismo `t` hubiera disparado y el Δ de liquidez sea el ganador *por maquillaje*: entonces `circulante` (ver §8).
3. Sin puntos → `texto_familia` vacío. No rellenar con copy genérico.

Copy cerrado (no improvisar):

- salud: `Si esto sigue (cobros, gastos o deuda), a 6 meses la nota cae.`
- circulante: `Estás comprando tiempo; a 6 meses ese colchón vence.`
- solo rojo, salud: `Giro persistente de salud (cobros, gastos o deuda).`
- solo rojo, circulante: `Giro persistente: el colchón de circulante ya no basta.`

Una frase. Sin listar palancas en el gráfico (eso va al panel de `/palancas`).

### 3.3 JSON de API (propuesta)

Extender la ficha de empresa (no un endpoint nuevo en v1):

```json
"trayectoria_marcas": {
  "confirmacion": { "as_of": "2025-10-01", "state": "TORCIENDOSE", "score": 71.2 },
  "camino": {
    "as_of": "2025-06-01",
    "outlook": "SALUD_ADVERSA",
    "score_observado": 78.0,
    "score_proyectado": 54.1,
    "familia": "salud"
  },
  "texto": "Si esto sigue (cobros, gastos o deuda), a 6 meses la nota cae."
}
```

`camino` y `confirmacion` pueden ser `null`. `lead_months` del feed de alertas **sigue `null`** en vivo: no hay evento de colapso fechado. En replay sintético, si se quiere el bonus B5, se mide aparte contra caja-oráculo; no se cuela en este JSON.

Warnings fijos cuando `camino` no es null: `cartoon_dynamics`, `caja_off`, `causal: false`, `no_pd`.

---

## 4. Punto rojo · receta (ya existe)

Reutilizar, no reescribir.

1. `calculate_scores(bank)` → paneles.
2. `classify_states(scores)` → `state`.
3. `directional_event_matrix` → primera columna `t` con valor `-1`.
4. Ese `(as_of[t], score[t])` es `punto_confirmacion`.

Gates que **ya** aplica el clasificador (heredarlos; no pintar rojo si fallan):

- `momentum_ready`, no `is_prior`, `observed_months ≥ 6`, calidad de estado ≥ 0,50.
- `|momentum| > 0,10` durante **3** meses, y **no** `annual_pattern_match`.
- Un mes de margen −0,12 es `BACHE`, no rojo.
- El opositor de 3 pts rompe un estado positivo; **no** crea el rojo por sí solo.

Front hoy: `Trayectoria` ya recibe `alerta={mesDeteccion}` y pinta un `ReferenceDot`. Ese mes debe pasar a ser `punto_confirmacion.as_of`, no un fixture ni `24 - mesesAnticipacion` inventado.

---

## 5. Punto hueco · receta exacta (esto hay que construir)

Piezas reutilizables:

- `forecasting/structural.py`: `run_rate`, `long_rate`, `build_projected_bank`, `score_at_horizon`, `HOLD_FIELDS`.
- `algorythm/levers_objects.py`: `ap_pending_eur`.
- `algorythm/score_engine.calculate_scores`: la `f` congelada.

**No** usar el camino central del estructural v2 (`φ=0,8` hacia la media de 12 meses) para el test de salud. Esa reversión dice “ya se le pasará”. Aquí “si no haces nada” = el régimen de 3 meses **se queda**.

**No** leer `banco[:, t+1:]` real. Igual que `build_projected_bank`: history through origin only.

### 5.1 Elegibilidad de un origen `t`

Mismo espíritu que el monitor:

- `t ≥ 5` (hace falta ventana de 6 meses, índices 0…t).
- no `is_prior[t]`.
- `observed_months[t] ≥ 6`.
- `bank_quality[t] ≥ 0,50` (o el `state_quality` del clasificador).
- `state[t] ∉ {TORCIENDOSE, DETERIORO}`.
- `state[t] ≠ EVALUACION_PENDIENTE`.
- `BACHE` **sí** es elegible (el pulso no anula la perspectiva).

Si `t` no es elegible, `outlook[t] = NINGUNA` y se sigue.

### 5.2 Estadísticos (solo pasado, NaN → 0)

Sea `start3 = max(0, t-2)`, `start12 = max(0, t-11)`.

```
R3 = mean(receipts[t-2 : t])     # 3 meses, inclusivo
E3 = mean(expenses[t-2 : t])
H3 = mean(debt_service[t-2 : t])
R12, E12, H12 = lo mismo a 12 meses
ρ  = sum(refunds[t-2:t]) / sum(receipts[t-2:t])   # 0 si el denominador es 0
AP = ap_pending_eur en el corte t                  # 0 si no hay objeto
S_t = score observado en t
```

Refunds futuros = cobros futuros × `ρ`.  
`gross_receipts` futuros = cobros + refunds.  
`quality` futura = 1.  
`hhi`, `hhi_quality`, `funding_gap`: congelar el valor de `t` (`HOLD_FIELDS`).

Horizonte `H = 6`. Meses proyectados: índices `t+1 … t+6`. El score que se lee es `score[0, t+6]`.

### 5.3 Camino salud (persistir régimen)

Para `h = 1…6`:

```
receipts     = R3
expenses     = E3
debt_service = H3
```

Fotocopia `A`. `Ŝ_salud = calculate_scores(A)[t+6]`.

### 5.4 Camino base (como si lo reciente no hubiera pasado)

```
receipts     = R12
expenses     = E12
debt_service = H12
```

Fotocopia `B`. `Ŝ_base = calculate_scores(B)[t+6]`.

### 5.5 Camino circulante (deshacer el colchón)

```
receipts     = R12
debt_service = H12
expenses     = E12 + AP / 6
```

Fotocopia `C`. `Ŝ_circulante = calculate_scores(C)[t+6]`.

Si `AP = 0`, `C` coincide con `B` y **no puede disparar**. No uses `E3` de un mes en el que se dejó de pagar: eso es el maquillaje.

v1 no unwind de línea ni confirming vivo. Si más adelante hay `loc_drawn` / confirming stock, misma idea: devolver el stock a `debt_service` o fees, **nunca** persistir el mes maquillado. Hasta entonces, circulante = solo AP.

### 5.6 Test (constantes, no tunear por empresa)

Deadband = **3** puntos (la banda neutra de previsión). Frontera = **60** (`base_boundary`).

Una familia dispara en `t` si **las tres** se cumplen:

1. `Ŝ_familia ≤ S_t − 3`
2. `Ŝ_familia < 60`
3. `Ŝ_familia ≤ Ŝ_base − 3`

Así el camino tiene que ser peor que hoy, entrar en zona “ya no parece sana”, y el daño tiene que ser del cambio, no de la inercia de 12 meses.

`outlook[t]`:

- ninguna familia → `NINGUNA`
- solo salud → `SALUD_ADVERSA`
- solo circulante → `CIRCULANTE_ADVERSO`
- ambas → la de `min(Ŝ_salud, Ŝ_circulante)` (empate: `SALUD_ADVERSA`; la salud manda el copy de giro)

### 5.7 Elegir el punto hueco

Recorrer `t` de 5 … último mes **hacia delante**. Primer `t` con `outlook[t] ≠ NINGUNA` y elegible (§5.1). Ese es `punto_camino`.

No usar el `t` de máximo `|S_t − Ŝ|`. Eso vuelve al argmax que descartamos.

### 5.8 Ejemplo numérico

Mes índice 12, `as_of=2025-06-01`, `S_12=78`, `state=ESTABLE`.  
`R3` bajó, `E3` subió. `AP=90_000`.

- `Ŝ_salud=54` → 54 ≤ 75, 54 < 60, y vs `Ŝ_base=72`: 54 ≤ 69. Dispara.
- `Ŝ_circulante=74` → no dispara.

Hueco en junio 2025, y=78, texto salud. Si el monitor confirma en octubre (`TORCIENDOSE`), el rojo va en octubre. El hueco se queda a la izquierda.

---

## 6. Front

Archivo actual: `front/components/charts.tsx`, componente `Trayectoria`.

Hoy: un `ReferenceDot` naranja si llega `alerta`.

Cambio:

```
<Trayectoria
  datos={e.trayectoria}
  confirmacion={e.marcas?.confirmacion?.as_of}
  camino={e.marcas?.camino?.as_of}
/>
```

- Rojo/naranja **relleno**: `confirmacion` (el `ReferenceDot` actual, color deterioro `#e5775b` o el naranja de `TORCIENDOSE` `#e59f5e` según `state`).
- Hueco: mismo `ReferenceDot` con `fill="transparent"` (o fill del fondo) y `stroke` del color de familia (salud / circulante). Radio igual o 1 px mayor.
- Texto **debajo** del gráfico, una línea, `e.marcas.texto`. No tooltip obligatorio; si hay tooltip, score observado en ese mes, y en el hueco además `score_proyectado` etiquetado “proyectado a 6 m, no es un hecho”.
- Horizontal de referencia: **y=60**, no y=45. El 45 actual no es el umbral del monitor.
- No pintar P10/P50/P90 en este gráfico. `/prevision` se deja como está; **no** es el sitio del momento.

Páginas que hay que alinear (hoy pasan `alerta.mesDeteccion`):

- `front/app/empresa/[id]/page.tsx` y/o `front/app/[company_id]/page.tsx`
- `front/app/comparar/split.tsx` (Time-Machine: Velasco debe mostrar rojo ± hueco)
- `front/app/grupo/[id]/page.tsx`
- `front/lib/motor.ts` (dejar de fabricar `mesesAnticipacion` como `24 - índice`)

Copy de ficha que hoy dice “lo vimos N meses antes” **solo** si existen los dos puntos: `N = meses(confirmacion) - meses(camino)`. Si no hay hueco, no inventar N. No usar el 4 de los fixtures.

Filtros visuales: si `EVALUACION_PENDIENTE` o `annual_pattern_match` en el mes del hipotético rojo, no hay rojo. Badge “estación” / “sin dato” **en vez de** punto, no además.

---

## 7. Dónde va cada pieza (archivos)

| Pieza | Archivo | Qué hacer |
| :--- | :--- | :--- |
| Outlook + búsqueda del primer `t` | `algorythm/score_outlook.py` **nuevo** | Dominio puro. Sin HTTP, sin Telegram. |
| Tests del test §5.6 y del “hueco < rojo” | `algorythm/test_score_outlook.py` **nuevo** | Fixtures sintéticos: rampa salud, solo AP, bache, estación, AP=0. |
| Enganchar al snapshot | `algorythm/calc_score.py` (o el job que ya escribe `score_panels.npz`) | Guardar `outlook*` en el npz **o** un `outlook_panels.npz` versionado. Preferible el mismo snapshot para no desincronizar `as_of`. |
| Confirmación = evento ya existente | `algorythm/score_monitor.py` `directional_event_matrix` | No duplicar. |
| AP | `algorythm/levers_objects.py` `get_company_bank_slice` / cache `ap_pending_eur` | Leer en `t`. Si el objeto es snapshot final y no hay vintage mensual, v1: usar el AP del corte actual en **todos** los `t` es una mentira suave — documentar `ap_sin_vintage`. Mejor: AP=0 en `t` si no hay historia, y el camino circulante no dispara en histórico. **Decisión v1:** circulante solo en el último mes del panel (corte vivo). Histórico del hueco = **solo salud**. El hueco circulante aparece, como mucho, en el corte actual. Así no inventamos vintages de facturas. |
| Proyección | Reusar helpers de `forecasting/structural.py` **o** copiar `run_rate` / `build_projected_bank` al dominio `algorythm/` para que el monitor no importe el lab. Preferible **mover o extraer** funciones de panel a `algorythm/score_project.py` y que el lab las importe. No al revés (el motor no depende de `forecasting`). |
| API | `backend/schemas.py`, ruta de empresa | Campo `trayectoria_marcas`. |
| Front | `charts.tsx`, `motor.ts`, ficha, comparar | §6. |
| Bot | `telegram_notifier.py` | El rojo sigue igual. El hueco **no** es alerta `ALTA`. Si se menciona, una línea INFORMATIVA. |

### 7.1 Decisión v1 de circulante (léela)

Las facturas pending del ERP/objetos son un **snapshot**, no 24 vintages. Por tanto:

- **Histórico (meses 0…T−2):** `AP=0` → el hueco, si existe, es siempre `SALUD_ADVERSA`.
- **Corte actual (mes T−1):** `AP` real → puede nacer `CIRCULANTE_ADVERSO` *si* el estado aún no es negativo.

El Time-Machine de Velasco (24 meses sintéticos / fixture) se alimenta de palanca de salud (rampa de cobros/gastos), no de AP. Encaja.

Si más adelante hay vintages de AP, se quita el `AP=0` histórico sin cambiar el test.

---

## 8. Mapeo del texto cuando solo hay rojo

Bloques `POINTS` de `make_alert`, Δ a 3 meses, **signo negativo**, excluir `momentum_points` y `clipping_points`.

| Bloque ganador | Familia por defecto |
| :--- | :--- |
| `liquidity_points` | `salud` (flujo). Si en el corte actual el camino circulante dispararía, `circulante`. |
| `collections_points` | `salud` |
| `debt_points` | `salud` |
| `growth_points` / `fragility_points` | `salud` |

No uses `|Δ|`: un clipping positivo no es “peor factor”.

---

## 9. Tests mínimos (antes de pintar)

1. **Rampa suave tipo Velasco** (base ≥ 60, momentum persistente): hay rojo `TORCIENDOSE`. El hueco, si existe, es estrictamente anterior. No hay cruce de signo obligatorio.
2. **Bache de un mes** (margen −0,12 y recupera): no rojo. Hueco no por el bache solo.
3. **Estación YoY dentro del deadband 0,06:** no rojo.
4. **Opex 3 m alto, S_t=78, Ŝ_salud=54, Ŝ_base=72:** hueco salud en ese `t` si aún `ESTABLE`.
5. **AP grande, R3=R12, E3=E12:** hueco circulante solo en el corte con AP; histórico sin AP no dispara circulante.
6. **AP=0:** `Ŝ_circulante == Ŝ_base`, no dispara circulante.
7. **Hueco posterior al rojo:** se anula el hueco.
8. **`is_prior` / historia &lt; 6 / quality baja:** sin puntos.
9. **Identidad:** `Ŝ` sale de `calculate_scores` sobre la fotocopia; no hay atajo `S_t + k·Δflujo`.
10. **No fuga:** mutar `receipts[t+1]` real no cambia `Ŝ` calculado en `t`.

Calibración de FA del **monitor** no se reabre. El hueco es otro reloj; su tasa de disparo se **reporta** (cuántas `ESTABLE` tienen outlook) pero no se usa para retocar `momentum_threshold`.

---

## 10. Orden de implementación

1. Extraer/crear `score_project.py` (`build_projected_bank` sin depender de `forecasting`).
2. `score_outlook.py` + tests 4, 5, 6, 7, 10.
3. Enganchar al snapshot; API `trayectoria_marcas`.
4. Front: dos dots + texto + y=60; quitar anticipación ficticia.
5. Comparar / Time-Machine.
6. Telegram: no ALTA por outlook.
7. (Opcional) reportar disparo de outlook en el informe de estrés, separado de `detection_within_6_months`.

No empezar por el front con fixtures de dos puntos. El hueco sin `calculate_scores` es teatro.

---

## 11. Prohibiciones (checklist de review)

- [ ] No nuevo estado en `NEGATIVE_STATES`.
- [ ] No `φ=0,8` en el camino salud de este test.
- [ ] No persistir DPO / `E3` bajo como “camino circulante”.
- [ ] No pintar `Ŝ_{t+6}` como punto en el eje x futuro.
- [ ] No `lead_months` inventado en el feed vivo.
- [ ] No imputar 0 a un mes hueco de verdad (NaN de outage ≠ actividad cero).
- [ ] No usar caja-oráculo en UI ni como feature.
- [ ] No OR de detectores ni meta-score `U`.
- [ ] No tercer punto (cruce de signo, argmax de pendiente, caja 0).
- [ ] No P10 como “lo vimos”.

---

## 12. Relación con `/simulate` y `/prevision`

| Superficie | Pregunta | Relación con los dos puntos |
| :--- | :--- | :--- |
| Monitor / ficha | ¿Se jodió? ¿Ya se veía? | Este spec. |
| `POST /api/simulate` | Si **tiro una palanca**, ¿`ΔS` ahora? | Dual. Misma `f`. Salud vs circulante ya están. No recalcular outlook dentro de simulate v1. |
| `GET /prevision` | Fan P10/P50/P90 o estructural v2 | **No** es el hueco. No mezclar en el mismo SVG en v1. |

Cuando el estructural do-nothing de `/prevision` use **el mismo** persist-3m + unwind-AP, se podrá unificar. Hasta entonces, dos códigos de proyección son peores que uno: por eso §7 pide extraer `score_project.py` y que el lab importe de ahí.

---

## 13. Criterio de hecho (demo)

Una ficha (Velasco o `expansion_cash_squeeze`):

- Una línea de score 0–100.
- Horizontal 60.
- Rojo en la primera `TORCIENDOSE`/`DETERIORO`.
- Hueco a la izquierda si el test de salud disparó antes.
- Una frase debajo, familia correcta.
- Tooltip del hueco dice que 54 es **proyectado**, no observado.

Si el jurado pregunta “¿es quiebra?”: no. Es perspectiva de `f` a 6 meses sobre una fotocopia, con caja off.
