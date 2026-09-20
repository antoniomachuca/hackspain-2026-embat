# Matemáticas del score · fuente para agentes

Documento de conocimiento interno. Lo leen agentes (y humanos que implementan o explican el sistema). No es un pitch. Si un README, un brief o un whitepaper discrepan del código, **gana el código**.

**Decisiones de producto (rutas, audiencias, palancas, UI):** [`PRODUCTO-DECISIONES.md`](PRODUCTO-DECISIONES.md).

**Código canónico del score:** `algorythm/score_engine.py` (`calculate_scores`, `ScoreConfig`).  
**Ingesta del panel:** `algorythm/score_data.py`.  
**Estados:** `algorythm/score_states.py` (`classify_states`, `StateConfig`).  
**Firma congelada y 41 claves de salida:** `respuestas_a_pedro.md`.  
**Whitepaper (intención + fórmulas, a veces stale):** `algorythm/formula/score_financiero.tex`.  
**Brief original (lo que se diseñó antes de ver el dato):** `research/algo_research_pedro.md`.  
**Exploración que tumba varias piezas del brief:** `research/informe_exploracion.md`.  
**Crítica empírica posterior al motor:** `research/revision_algoritmo_hugo.md`.

---

## 0. Cómo está montado el sistema alrededor del score

El score no es un ranking aprendido. Es una función determinista \(f\) sobre un panel mensual de flujos bancarios:

\[
S_t = f(\text{banco}_t),\qquad f=\texttt{calculate\_scores}.
\]

Todo lo demás reutiliza \(f\) congelada (mismos `ScoreConfig` y, si aplica, mismos artefactos):

| Superficie | Archivo | Qué se le pasa a \(f\) |
| :--- | :--- | :--- |
| Score oficial | `calc_score.py` → `engine_results/` | Panel banco, ERP off, `cash_known=0` |
| Estados | `score_states.py` | Salidas de \(f\) (`score`, `base_health`, `momentum`, calidad, flags) |
| Anillo bache/tendencia | `score_decompose.py` | El mismo panel, campos congelados/descongelados uno a uno |
| `/simulate` | `levers.py` | Fotocopia del panel, mutada solo en el último mes |
| Perspectiva a 6 meses | `score_outlook.py` | Fotocopia hasta \(t\) + régimen \(R_3,E_3,H_3\) persistido |
| Previsión estructural | `forecasting/structural.py` | Cobros/pagos/deuda proyectados mes a mes, luego \(f\) |

Si se enciende caja o ERP, hay que hacerlo en `/score` y `/simulate` a la vez y bumpear `model_version` (`calc_score.py` hashea código + configs + modo ERP). Nunca un simulate con una \(f\) distinta.

Panel de entrada requerido: matrices `(empresas, meses)` `receipts`, `expenses`, `debt_service` (no negativos o NaN). Opcionales banco: `gross_receipts`, `refunds`, `funding_gap`, `hhi`, `hhi_quality`, `quality`. Opcionales caja (apagados): `cash_balance`, `commitments_30d`, `negative_balance_fraction`. ERP (apagado): `dso_days`, `late_fraction`, `quality`, `conversion`, `sales_growth`, `hhi`, `hhi_quality`.

Artefacto oficial: `algorythm/engine_results/score_manifest.json` — `erp.mode = disabled_without_verified_direction_and_historical_states`, `cash_observations_sha256 = null`, `endpoint_cash_known_count = 0`, `endpoint_erp_used_count = 0`.

---

## 1. Linaje de research (qué se diseñó, qué se tiró, qué quedó)

Leer esto antes de “arreglar” el motor. Varias ideas que parecen obvias ya se consideraron y se rechazaron con el dato en la mesa.

### 1.1 Brief de Pedro (`research/algo_research_pedro.md`) — 18 sep, pre-dato fino

Problema: no hay etiqueta de impago. Consecuencia: **reglas auditables**, no GBDT. SHAP/LIME, WOE/IV, PD/Gini, Isolation Forest/LSTM/HMM como núcleo, Altman/Merton: descartados (circularidad, 24 puntos, exige balance o precio, o etiqueta).

Diseño propuesto entonces:

- Cuatro bloques de **percentiles contra peer** (país × cuartil de ingresos): liquidez 30 %, conducta de pago 30 %, deuda 25 %, concentración 15 %.
- Ventana 12 meses, creciente desde mes 6.
- Tendencia = OLS 6 meses sobre \(N(t)\), mediana de las 3 últimas pendientes, umbral ±1 pt/mes.
- Score = \(0{,}6\,N + 0{,}4\,(N+3T)\).
- Confianza mezclada con % conciliado, meses/24, etc.
- ML opcional solo para reajustar pesos, target = flujo futuro (no \(S_t\)), Ridge + GroupKFold, doble test (temporal y leaderboard).
- Máximo 5–6 variantes contra el test oculto.

Eso **no es lo que hay en código**. Es el origen de las preguntas (nivel, trayectoria, bache vs caída, explicación exacta, anticipación) y de varias prohibiciones que sí se conservaron.

### 1.2 Exploración del dataset (`research/informe_exploracion.md`) — 18 sep, CSV en mano

Cifras calculadas, no estimadas. Decisiones que dispara:

| Hecho | Consecuencia en el motor |
| :--- | :--- |
| Ningún target en los 9 ficheros | Reglas. GBDT solo si el script de scoring revelara etiqueta (no lo hizo). |
| País 82 % nulo, sucio (`ES`/`ESPAÑA`/`España`) | Peer por país **muerto**. |
| Cruce `counterparty_id` ↔ `company_id` = 0,0 % | Grafo de clientes **muerto**. |
| Contraparte en txs 9,8 %; en facturas 98,7 % | HHI de banco casi vacío; HHI de invoices era el plan, pero ERP off. |
| `payment_date` en pending/overdue ≈ `due_date` (96–98 %) | Leakage si se usa. As-of obligatorio. |
| `balances.csv` = foto 1-sep-2026 | Reconstruir caja hacia atrás = lookahead. REQ-B1.1 lo prohíbe. |
| `debt_schedule_config`: 87 filas / 1.261 préstamos (7 %) | DSCR de cuadro **inservible**. Servicio = flujos `debt_repayment` + `interest_charge`. |
| Historia: mediana 18,4 meses; 32 % < 12 meses; 29 % con 24 | Warmup 6 meses obligatorio. Anticipación solo donde hay serie. |
| Signo de `amount` en facturas = dirección (99,6 % vs banco) | AR vs AP se puede inferir, pero el núcleo oficial no enciende ERP histórico. |

Research externo (Claude/Gemini/ChatGPT-Carlos, Quirce) coincidía en LightGBM/XGBoost + SHAP. Se contrastó y se rechazó porque no hay \(y\). Un experimento Astra (HistGradientBoosting sobre flujo futuro) no superó baseline/Ridge. No se sustituyó el núcleo.

### 1.3 Lo que implementó el motor (Carlos/Antonio)

En lugar de percentiles + 4 asignaturas + mezcla 60/40:

- Tres pilares **absolutos** \(L,C,D\) con Hill/tanh, pesos **50/30/20**.
- Concentración **fuera** de la base: va a fragilidad \(F\) (techo −8).
- Trayectoria **aditiva** \(\lambda M\) con \(\lambda=8\), \(M\in[-1,1]\), no mezcla 60/40 ni OLS de \(N\).
- Crecimiento \(+6\) y fragilidad \(-8\) como términos aparte.
- Confianza **ortogonal** (DCI), no contrae pilares hacia 0,5.
- ERP y caja **apagados** en artefactos oficiales.
- Puntuar una empresa es \(O(1)\) (~4 ms), invariante a otras empresas del lote (\(\Delta_{\text{batch}}=0\)).

Motivación explícita (`score_financiero.tex`, `respuestas_a_pedro.md` §6): sin país ni sector, un peer inventado mueve a todo el mundo cuando entra una empresa del test oculto. Hill/tanh no tiene esa fuga.

### 1.4 Iteraciones de diseño **dentro** del motor (whitepaper §3, §5)

Tres cambios respecto a formulaciones iniciales que **sí llegaron a código**:

1. **Se elimina `observed_blend`.** Antes: \(\mathcal{A}(x,\rho)=0{,}5+\rho(x-0{,}5)\) contraía pilares hacia el prior cuando faltaba dato. Efecto: falta de densidad = “más normal”, y opacidad amortiguaba el riesgo. La función sigue definida en `score_engine.py` y **no se llama**. Los pilares reflejan el flujo observado; la calidad vive en `confidence_index`.
2. **Crecimiento: media aritmética, no geométrica.** \(G^b\) usaba \(\sqrt{L^b C^b}\). En recuperación, un \(L\) bajo estrangula \(G\) a 0 aunque los cobros ya se recuperen. Hoy: \(0{,}5(L^b+C^b)\). \(G\) es unilateral (`max(g,0)`): nunca resta.
3. **Fragilidad sin \(\times q_3\).** Multiplicar \(F\) por cobertura premiaba opacidad (peor dato → menos penalización). Se quitó. El estrés es noisy-OR de timing / descubierto / mora ERP.

Cuarto cambio, en estados no en \(S\): **opposing momentum breaker**. La histéresis de 2 meses retenía `MEJORANDO`/`RECUPERACION` durante un shock. Ahora, \(M\) contrario o \(|\Delta S|>3\) rompe el hold. Caso documentado: `COMP_0010`, 2026-02 → 2026-03, \(S\) 69,86 → 39,00.

### 1.5 Crítica de Hugo (`research/revision_algoritmo_hugo.md`) — 19 sep, post-motor

Nota global 5,5/10: chasis de ingeniería alto; la señal, ruidosa y sesgada por el categorizador. Un agente que toque el score **tiene que conocer esto**; no está “resuelto” por el whitepaper.

Hallazgos empíricos (sobre paneles exportados y CSV, no sobre los JSON de validación):

- El motor **no usa** categorías `-` (24,9 % filas, 38,8 % volumen) ni trata `transfer` (6 % / 18,9 %) como intra-grupo: `normalize_transaction` las manda al fallback por signo. Mediana de volumen no clasificado por empresa ~29 %.
- \(L\) explica **~68 %** de la varianza transversal del score (Hugo) / hasta ~84 % en sondas de capa intermedia. Spearman \(L\) vs signo neto de lo descartado: **−0,56**. Si los pagos cayeron en `-`, la empresa parece líquida.
- AUC vs 29 empresas con caja terminal negativa: **0,46**. \(\rho\)(score, % facturas emitidas vencidas) ≈ 0. El pilar \(C\) correlaciona **−0,64** con el CV a 6 meses de cobros: penaliza estacionalidad. Refunds = 0,02 % del volumen.
- Momentum: \(\rho\) parcial con margen futuro (controlando margen actual) **negativa**. Cambia de signo el 24 % de meses en que está activo. Causa plausible: \(v=(B_t-B_{t-3})/3\) sobre una base que ya es media 3m → reversión. La antelación “8–14 meses” del whitepaper es **sintético** (`observed_on_real_companies: false`).
- Estabilidad mes a mes del score 0,74–0,78 (brief pedía >0,85); a 6 meses 0,33. El margen crudo a 12 meses es más estable.
- \(D=0{,}5\) exacto en el 58 % de observadas. \(F\) ~0 % de varianza. HHI banco usable: manifiesto actual **74** empresas (Hugo midió 125 en un corte anterior). \(G=0\) en ~50 % (unilateral).
- El ERP se apagó por “signo no verificado”; el dato responde (negativo = AP, positivo = AR). No se encendió en el núcleo oficial.

Recomendaciones de Hugo (clasificar `-` por signo, series DSO point-in-time, peer por tamaño, OLS 6m, validar contra saldo terminal como *evaluación* no como input) **no se adoptaron como cambio de \(f\)** en el hackathon. El protocolo del laboratorio de forecast es explícito: no se cambian pesos del score al ver fallos; se registran. Un agente no debe “arreglar” \(L\) o \(M\) sin tratar esto como cambio de `model_version` y de narrativa.

### 1.6 Lo que se conservó del brief, en otra forma

| Idea del brief | Forma en código |
| :--- | :--- |
| Sin etiqueta → reglas | `calculate_scores` determinista |
| Trayectoria, no solo foto | \(M\) aditivo + estados |
| Bache vs caída | persistencia 3m + estado `BACHE` (pulso de margen 0,12) |
| Explicación exacta, no SHAP | \(\Delta S=\sum\Delta P_j+\Delta P_{\mathrm{clip}}\) |
| Confianza ≠ riesgo | DCI ortogonal; `is_prior` → 50 |
| Point-in-time | txs `booked` en corte; ERP no retrodatado; caja no reconstruida |
| No grafo si cruce bajo | cruce 0 → no hay grafo de clientes |
| Grupo 65/35 + contagio | API (`backend/routes/stats.py`), no el motor |
| Congelar antes de tunear el test oculto | umbrales versionados, `credit_rating_calibrated: false` |

---

## 2. Del CSV al panel (`score_data.py`)

El motor no lee facturas ni saldos. Lee un panel mensual construido así.

**Calendario.** `month_edges('2024-09-01', '2026-09-01')`: 24 meses, end exclusivo. El 1-sep-2026 (muchos movimientos de un solo día) **queda fuera** del panel.

**Filtros por transacción.** Solo `status==booked`. Producto debe existir y pertenecer a la empresa. Se excluye FX (`currency` del producto ≠ moneda de la empresa, o `exchange_rate ≠ 1`). Hugo: ~97 k txs excluidas por FX.

**Mapeo de categorías** (`normalize_transaction`):

| Destino | Categorías |
| :--- | :--- |
| `receipts` (+) | `collection`, `bulk_collection`, `pos_settlement`, `cash_settlement(s)` con amount > 0 |
| `receipts` (refund, signed < 0, luego `refunds -= signed`) | `collection_refund` con amount < 0 |
| `expenses` | `payment`, `bulk_payment`, `salary`, `social_security`, `tax`, `utility`, `fee` (se guarda \(-amount\), luego clip ≥ 0) |
| `debt_service` | `debt_repayment`, `interest_charge` con amount < 0 |
| Fallback | amount < 0 → expenses; amount > 0 → receipts |

`transfer` **no** está en ingresos ni gastos: cae al fallback por signo. No hay filtro intragrupo. Tras agregar: `receipts` y `expenses` se clipean a ≥ 0 (un mes con más refunds que cobros no deja receipts negativos).

**Calidad.** `native_share` = txs en moneda nativa / booked. `classified_share` = volumen reconocido / volumen nativo. `quality = min(native_share, classified_share)`. Entra en DCI y en el gate de persistencia de \(M\), no en \(L,C,D\).

**Funding gap.** Sobre el flujo diario neto del mes: máximo drawdown intra-mes menos el déficit terminal del mes. Es tensión de *timing*, no de solvencia de stock. NaN si no hay txs nativas ese mes.

**HHI.** Sobre cobros con `counterparty_id`, rolling 3 meses, solo si cobertura ≥ 0,95. Si no, NaN y \(\theta=0\) (fragilidad sin concentración).

**Caja (función existe, manifiesto null).** `add_cash_observations` exige `observed_at ≤ as_of`. No rellena meses anteriores. El núcleo oficial no la llama.

**ERP snapshot (opt-in, no oficial).** No usa `payment_date` para inferir pago (`payment_date_used_to_infer_payment = False`). No se retropropaga. Blend \(C\) acotado a \(\eta\le 0{,}40\) *si* hay ERP; con ERP off, \(\eta=0\).

---

## 3. La función \(f\) (`calculate_scores`)

### 3.1 Ecuación

\[
S_{\mathrm{raw}}=50L+30C+20D+8M+6G-8F,\qquad
S=\begin{cases}
\mathrm{clip}(S_{\mathrm{raw}},0,100) & \text{si hay evidencia}\\
50 & \text{si }\texttt{is\_prior}
\end{cases}
\]

\[
B=50L+30C+20D=\texttt{base\_health}
\qquad\text{(usa }L\text{ ya sustituido por caja si }\texttt{cash\_used}\text{)}.
\]

`bank_base_health` es la base **solo banco** (\(L_{\mathrm{bank}},C_{\mathrm{bank}},D\)). El momentum se calcula sobre **`base_bank`**, no sobre la base con caja/ERP. Tests: ERP/caja no fabrican \(M\).

Pesos en `ScoreConfig.base_weights`; `__post_init__` exige suma 1, no negativos, escalas > 0. No se estiman. Justificación declarada: tesorería (capacidad de absorber compromisos ahora) 50 %; cobros 30 %; deuda 20 % conservador porque el extracto no trae cuadros. \(D\le 0{,}5\) ⇒ el bloque deuda **nunca** entrega 20 puntos.

### 3.2 Saturaciones

Hill en código:

```python
def hill(values, scale):
    return 1 - scale / (np.maximum(values, 0) + scale)
```

Es \(h(x;a)=x/(x+a)\) para \(x\ge 0\), \(h(a;a)=0{,}5\), rango \([0,1)\), derivada \(a/(x+a)^2\le 1/a\). Monótona, saturante. El whitepaper la escribe igual.

`tanh` (impar, \([-1,1]\)) en margen, deuda, velocity, cruce EMA, \(\Delta\)DSO, crecimiento. Un margen 10× no vale 10× de salud.

**No hay percentiles ni peers en `algorythm/`.** REQUISITOS B2 no existe en código. Documentos que hablen de “el gradiente miente al cruzar un decil” están stale: los kinks reales son Hill/tanh, deadband de persistencia, enteros de racha, `clip`, switches `cash_used` / ERP / HHI / `is_prior`.

### 3.3 Ventanas y NaN

- \(R_3,E_3,H_3,q_3\): rolling 3 meses (`rolling_sum` / `rolling_mean`). El mes 0 y 1 quedan NaN en esas ventanas.
- CV de cobros: **6 meses**.
- `divide`: NaN si denominador ≤ 0 (no inf).
- Flujos no finitos en un mes se ponen a 0 para agregar, pero `valid` exige los tres (`receipts`, `expenses`, `debt_service`) finitos. `quality` se anula donde no `valid`.

### 3.4 Liquidez \(L\)

Margen relativo 3 meses (el servicio de deuda **no** entra en \(m_3\); sí entra en el margen mensual de confirmación de \(M\)):

\[
m_3=\frac{R_3-E_3}{R_3+E_3},\qquad
L_{\mathrm{bank}}=\begin{cases}
0{,}5+0{,}5\tanh(m_3/0{,}50) & m_3\text{ finito}\\
0{,}5 & \text{si no}
\end{cases}
\]

Equilibrio \(R=E\) ⇒ \(L=0{,}5\). \(\sigma_L=0{,}50\) (`liquidity_scale`).

**Si `cash_used`** (`cash_known` y cobertura finita), \(L_{\mathrm{bank}}\) **se sustituye**, no se mezcla:

\[
b=\max\bigl((E_3+H_3-R_3)/3,\,0\bigr),\quad
S_{\mathrm{run}}=\frac{K^+}{K^++3b},\quad
S_{\mathrm{cob}}=\frac{K^+}{K^++P_{30d}}
\]

\(K^+=\max(K,0)\). Si \(K^+=0\) y \(b\) finito, runway = 0. \(P_{30d}=\) `commitments_30d` si existe, si no \((E_3+H_3)/3\). \(L=0{,}5\,S_{\mathrm{run}}+0{,}5\,S_{\mathrm{cob}}\).

Default oficial: caja off ⇒ \(L=L_{\mathrm{bank}}\) siempre. Sonda de capa intermedia: cash=200 movía ~+11,6 pts y \(L\) absorbía ~84 % de esa varianza; por eso no se encendió en silencio.

Efecto colateral importante para palancas: **bajar `expenses` (p.ej. retrasar AP) sube \(m_3\) y sube \(L\)**. El motor no distingue recorte de opex de DPO. La capa intermedia lo trata como familia *circulante* y no ordena por \(\Delta S\) (véase §8).

### 3.5 Cobros \(C\)

\[
f=\frac{U_3}{R^{\mathrm{bruto}}_3},\quad
s^{\mathrm{ref}}=1-\mathrm{hill}(f,0{,}05)=\frac{0{,}05}{f+0{,}05}
\]

\(k=0{,}05\): un 5 % de devoluciones sobre cobros brutos es el punto medio, no un percentil de sector. Devoluciones con neto 0 **sí cuentan** (test). NaN → 0,5.

\[
s^{\mathrm{reg}}=\frac{1}{1+\mathrm{CV}_6(R)},\qquad
C_{\mathrm{bank}}=\tfrac12 \tilde s^{\mathrm{ref}}+\tfrac12 \tilde s^{\mathrm{reg}}.
\]

Con ERP (apagado): \(z=1-\mathrm{hill}(\mathrm{DSO},60)\); si hay DSO en \(t\) y \(t-3\) con calidad ERP > 0, \(z\leftarrow 0{,}75z+0{,}25(0{,}5-0{,}5\tanh(\Delta_3\mathrm{DSO}/30))\). \(C_{\mathrm{erp}}=\tfrac12 z+\tfrac12(1-p^{\mathrm{late}})\). Mezcla \(\eta=0{,}40\cdot q^e\cdot\mathbf{1}_{C_{\mathrm{erp}}\text{ finito}}\). \(C=C_{\mathrm{bank}}+\eta(C_{\mathrm{erp}}-C_{\mathrm{bank}})\).

### 3.6 Deuda \(D\)

Solo flujo bancario \(H=\) `debt_service`. No usa `outstanding`, `granted`, ni el cuadro.

\[
d^H=\frac{H_3}{R_3+H_3},\qquad
D=\begin{cases}
0{,}5-0{,}5\tanh(d^H/0{,}25) & d^H\text{ finito}\\
0{,}5 & \text{si no}
\end{cases}
\]

Sin cuota observada, \(D=0{,}5\) (neutro, **no** “desapalancada”). Más \(H\) nunca sube \(D\). Amortizar un mes extra **empeora** \(D\) (el what-if de “amortizar” no es refinanciar). Refinanciar de verdad = bajar \(H\) *recurrente* con oferta explícita.

### 3.7 Momentum \(M\) (el bloque más delicado)

Se calcula en `bounded_momentum` sobre `base_bank` y un margen mensual de confirmación:

\[
x_t=\frac{R_t-E_t-H_t}{R_t+E_t+H_t}.
\]

(Aquí sí entra \(H\). Distinto de \(m_3\).)

**EMA, no medias simples.** El whitepaper a veces escribe \(E_3-E_6\); el código es:

\[
\alpha_{\mathrm{fast}}=\tfrac12,\qquad \alpha_{\mathrm{slow}}=\tfrac27=2/(6+1).
\]

Solo se actualizan en meses `history_ready`. Si el mes no está listo, EMA → NaN (se reinicia).

**Velocidad:** \(v=(B_t^b-B_{t-3}^b)/3\).

**Persistencia, bloques no solapados.** `previous = t-5:t-3`, `recent = t-2:t` (tres meses cada uno). Dirección = signo(mediana reciente − mediana vieja). `agreeing` = meses de `recent` con \(\mathrm{dir}\cdot(x_j-\mathrm{old})>0{,}02\) (`persistence_deadband`).

\[
c=\mathrm{clip}\bigl((\texttt{agreeing}-1)/2,\,0,1\bigr)\cdot\min_{k=0..5} q_{t-k}
\]

| agreeing | \(c\) (si \(\min q=1\)) |
| ---: | ---: |
| 0–1 | **0** (un mes = bache, \(M=0\)) |
| 2 | 0,5 |
| 3 | 1 |

**Gate `comparable_history`:** 4 bases `history_ready` (`t-3…t`) y ≥2 finitos en cada bloque de confirmación. `history_ready` = **6 meses observados consecutivos** (`rolling_sum(observed, 6)==6`), no `month index ≥ 5`. `observed` = calidad > 0 y (flujos > 0 o gross o refunds). \(t<5\) ⇒ \(M=0\).

\[
M=c\cdot\bigl[0{,}5\tanh(v/2)+0{,}5\tanh(\Delta_{\mathrm{EMA}}/5)\bigr],\qquad P_M=8M.
\]

La estacionalidad anual (`annual_pattern_match`, deadband YoY 0,06) **no anula \(M\)**. Silencia la racha en `classify_states`. Dos relojes.

Hugo: esta \(M\) es anti-predictiva del margen futuro tras controlar el nivel. No se retocó \(\lambda\) ni las escalas en el hackathon. El clasificador usa \(|M|>0{,}10\) tres meses; eso es **estado**, no un segundo score.

### 3.8 Crecimiento \(G\)

Unilateral, techo \(+6\):

\[
g^b=\frac{R_{3,t}-R_{3,t-3}}{R_{3,t}+R_{3,t-3}},\quad
G^b=\tanh\bigl(\max(g^b,0)/0{,}20\bigr)\cdot\tfrac12(L_{\mathrm{bank}}+C_{\mathrm{bank}})\cdot\min(q_{3,t},q_{3,t-3}).
\]

El README a veces escribe \(\propto q_3\); el código es \(\min(q_{3,t},q_{3,t-3})\). Un spike de cobros de un mes **sí** puede encender \(G\) ( \(M\) no, por persistencia). ERP: mezcla ≤ 0,40 con ventas y conversión.

### 3.9 Fragilidad \(F\)

Solo resta, techo \(-8\).

\[
s^{\mathrm{tim}}=\mathrm{hill}\bigl(\overline{\mathrm{gap}}_3\big/\tfrac{E_3+H_3}{3},\,0{,}50\bigr)
\]
\[
s^{\mathrm{neg}}=\mathrm{hill}(\mathrm{frac}_{K<0},\,0{,}25),\quad
s^{\mathrm{late}}=\mathrm{hill}(p^{\mathrm{late}},0{,}25)\cdot\mathbf{1}_{q^e>0}
\]

\(0{,}25\) de descubierto/mora está **hardcoded** (no está en `ScoreConfig`). Si no hay fracción y hay caja, se infiere `cash<0`.

\[
s=1-(1-s^{\mathrm{tim}})(1-s^{\mathrm{neg}})(1-s^{\mathrm{late}})\qquad\text{(noisy-OR)}
\]

\[
\theta=0{,}5\cdot\mathrm{clip}(q^{\mathrm{HHI}},0,1)\cdot\mathbf{1}_{\mathrm{HHI}\text{ finito}},\quad
F=(1-\theta)s+\theta\cdot\mathrm{hill}(\mathrm{HHI},0{,}25).
\]

ERP HHI gana si `erp_hhi_quality > hhi_quality` banco. Con ERP off, solo banco, gate 95 % → pocas empresas.

Hill de HHI es plana en la zona útil (sonda 0,3→0,9 ≈ −0,95 pts). Diversificar como mucho quita penalización, no suma.

### 3.10 Evidencia, prior, clip, DCI

Flags de evidencia (OR): liquidez disponible (margen finito y \(q_3>0\), o `cash_used`); cobros disponibles; deuda con \(q_3>0\); fragilidad con \(q_3>0\) y (gap o caja o HHI o mora); ERP usado. Si no hay evidencia: `is_prior=True`, \(S=50\), DCI = 0. 116 empresas en el endpoint oficial.

\[
\mathrm{DCI}=\mathrm{clip}\bigl(100\cdot q_3\cdot\min(m_{\mathrm{obs}}/6,1),0,100\bigr)
\]

\(m_{\mathrm{obs}}=\mathrm{cumsum}(\texttt{observed})\). No entra en \(S\). Spearman score vs calidad en corte maduro: whitepaper \(\rho=0{,}107\) (objetivo: no colinear con cobertura). Hugo matiza que distancia a 50 vs calidad es +0,46: el desacople no es perfecto.

\[
\Delta P_{\mathrm{clip}}=S-S_{\mathrm{raw}},\qquad
S=\sum_j P_j+\Delta P_{\mathrm{clip}}.
\]

Tests: `atol=1e-12` en nivel y en `np.diff`. En panel real el clip casi no muerde (máx ~88,9). El waterfall de producto **es** esta identidad. `score_decompose.py` es otro waterfall (contrafactuales de *inputs*); no lo sustituye.

### 3.11 Constantes (`ScoreConfig`)

| Campo | Valor | Dónde actúa |
| :--- | :--- | :--- |
| `base_weights` | (0,50, 0,30, 0,20) | \(B\) |
| `momentum_weight` | 8 | \(P_M\) |
| `growth_weight` | 6 | \(P_G\) |
| `fragility_weight` | 8 | \(P_F\) (resta) |
| `momentum_mix` | 0,50 | velocity vs EMA |
| `velocity_scale` | 2,0 | \(\tanh(v/2)\) |
| `ema_scale` | 5,0 | \(\tanh(\Delta_{\mathrm{EMA}}/5)\) |
| `persistence_deadband` | 0,02 | acuerdo de márgenes |
| `liquidity_scale` | 0,50 | tanh margen |
| `refund_scale` | 0,05 | Hill devoluciones |
| `debt_scale` | 0,25 | tanh carga |
| `hhi_scale` | 0,25 | Hill HHI |
| `funding_gap_scale` | 0,50 | Hill gap |
| `growth_scale` | 0,20 | tanh \(\Delta R\) |
| `dso_scale` | 60 | Hill DSO (ERP) |
| `dso_change_scale` | 30 | tanh \(\Delta\)DSO |
| `erp_weight` | 0,40 | techo \(\eta\) |

Hardcoded fuera del dataclass: Hill 0,25 descubierto/mora; mix HHI 0,50.

### 3.12 Claves de salida que otros módulos consumen

No renombrar (`respuestas_a_pedro.md` Q1). Las que más se pisan:

- `score`, `raw_score`, `clipping_points`, `is_prior`
- `base_health` (L+C+D **tras** caja), `bank_base_health`
- `L`, `L_bank`, `C`, `C_bank`, `D`
- `*_points` de los seis sumandos
- `momentum`, `history_ready`, `momentum_ready`, `observed_months`
- `monthly_flow_margin`, `flow_margin_available`, `monthly_data_quality`, `bank_quality`
- `cash_known`, `cash_used`, `erp_used`, `hhi_used`, `debt_service_observed`
- `confidence_index` (= `data_confidence_index`)

`classify_states` añade: `state`, `state_eligible`, `state_provisional`, `state_quality`, `health_band`, `state_evaluation_reason`, `seasonality_available`, `annual_pattern_match`.

Bandas de salud (`SOLIDA` ≥ 70, `INTERMEDIA`, `DEBIL` < 40) son **eje paralelo** a `state`. `is_prior` → `SIN_EVIDENCIA`. Calidad baja → `COBERTURA_LIMITADA`. No pintan el punto rojo del monitor.

---

## 4. Estados (`score_states.py`) — no son el score

`S` es continuo. El estado es un **verbo** sobre \(M\), persistencia y `base_health`. No entra en \(S\). No es PD (`credit_rating_calibrated: false` en el manifiesto).

Elegibilidad: `momentum_ready` ∧ ¬`is_prior` ∧ `observed_months ≥ 6` ∧ `state_quality ≥ 0,50` (mínimo de \(q_3\) en \(t\) y \(t-3\)). Si falla → `EVALUACION_PENDIENTE`.

Silenciador: `annual_pattern_match` (desde mes 14; medianas de margen vs año anterior, deadband 0,06). Esa racha **no** incrementa momentum direccional.

| Estado | Condición real |
| :--- | :--- |
| `ESTABLE` | Elegible y no hay racha confirmada, pulso ni hold. Incluye \|M\|≤0,10 **y** \|M\|>0,10 aún no persistido **y** estación. El README que lo reduce a \|M\|≤0,10 está corto. |
| `TORCIENDOSE` | Racha \(M<-0{,}10\) ≥ 3 meses y `base_health` ≥ 60 |
| `DETERIORO` | Misma racha, base < 60 |
| `MEJORANDO` | Racha \(M>+0{,}10\) ≥ 3, sin debilidad previa |
| `RECUPERACION` | Misma racha **con** debilidad: algún `NEGATIVE_STATES` en 6 meses previos **o** mediana de base de 3 meses previos < 60 |
| `BACHE` | Margen del mes < mediana de los 3 anteriores − 0,12; ≥2 meses válidos; calidad ≥ 0,50; **sin** racha confirmada ni estado direccional previo. Un mes. Provisional. |

Histéresis: estado direccional se sostiene mientras `neutral_streak < 2` y no hay opositor. Opositor: momentum en contra **o** \(\Delta S>3\). El opositor rompe inercia; **no** abre alerta. `TORCIENDOSE → DETERIORO` es escalada de episodio, no episodio nuevo (`score_episodes.py`).

`NEGATIVE_STATES = (TORCIENDOSE, DETERIORO)`. Telegram ALTA/MEDIA solo ahí. `BACHE` y `outlook` no.

Umbrales (`StateConfig`), versionados, no tunados por empresa:

| Campo | Valor |
| :--- | :--- |
| `momentum_threshold` | 0,10 |
| `persistence_months` | 3 |
| `base_boundary` | 60 |
| `pulse_margin_drop` | 0,12 |
| `neutral_persistence_months` | 2 |
| `minimum_quality` | 0,50 |
| `minimum_observed_months` | 6 |
| `year_over_year_deadband` | 0,06 |

Persistencia 2 meses es `admissible: false` en `behavior_results/calibration.json` (rompe ≤ 1 FA/empresa-año en sanas, REQ-B5.1). Persistencia 3 es la seleccionada. No bajarla porque un caso de demo falle: hay test oculto.

El enunciado (Northbrook 45→65 vs Velasco 82→68) es exactamente `RECUPERACION` vs `TORCIENDOSE` con base aún alta. El umbral ±1 pt/mes del brief no dispara la rampa de Velasco (~0,6 pts/mes); el monitor de persistencia sobre \(M\) sí, si \(|M|>0{,}10\) se mantiene.

---

## 5. Tres relojes (no mezclarlos)

Documentado en `research/momento_en_que_se_tuercen.md` y `algorythm/EPISODIOS.md`.

| Reloj | Pregunta | Dónde vive | Trampa |
| :--- | :--- | :--- | :--- |
| \(t_{\mathrm{evento}}\) | ¿Cuándo se materializó? | Caja-oráculo ≤ 0, **solo sintético** | Usar el cruce del detector |
| \(t_{\mathrm{alerta}}\) | ¿Cuándo lo confirma lo observado? | Primera entrada `TORCIENDOSE`/`DETERIORO` (mes que completa los 3) | Retrodatar al mes 1 de la racha |
| \(t_{\mathrm{anticipación}}\) | ¿Desde qué corte ya se veía el camino feo? | `score_outlook.py`, punto hueco | Pintar P10 como hecho; inventar `lead_months` |

En feed vivo `lead_months=null`. Si el evento *es* el detector, la antelación es cero por construcción.

**Episodio.** Referencia = `base_health` en detección − persistencia (mes anterior a la racha), **no** el score (circular: el score ya lleva \(M\)). Cambio material: 10 pts o banda 40/70, 2 meses consecutivos. Puede ocurrir *antes* de la detección. Cerrado sin material → `no_confirmado`, copy “No se confirmó”.

**Outlook / punto hueco.** Fotocopia banco hasta \(t\), persistir \(R_3,E_3,H_3\) seis meses, \(f\) congelada. Dispara si \(\hat S\le S_t-3\), \(\hat S<60\), \(\hat S\le\hat S_{\mathrm{base}}-3\) (base = régimen 12 meses). Circulante: unwind de AP (`E12+AP/6`), **nunca** persistir el mes maquillado de DPO. No usa \(\varphi=0{,}8\) (eso es el estructural de `/prevision`). Warnings: `cartoon_dynamics`, `caja_off`, `causal: false`, `no_pd`. No es estado; no dispara ALTA.

Definiciones **rechazadas** como “el momento”: pendiente bajó mucho; cruce +→− (es el máximo local; Velasco puede no cruzar); N decisiones de CFO (no hay log); índice \(U=\sum w_i x_i\) (doble conteo); “el factor que más empeoró” como fecha (post-hoc).

---

## 6. Identificación bache vs tendencia (`score_decompose.py`)

Pregunta distinta al estado `BACHE`. El monitor pregunta “¿hay giro persistente?”. Esto pregunta “¿de qué está hecho **este** \(\Delta\) de **este** mes?”.

El front OLS a 6 meses **sobre el score** (`pendiente` + `repartir`) es geometría de \(S\), no de la cuenta. Un recorte de opex el mes del shock sale casi todo “bache”. Se rechazó como explicación. El producto no debe reimplementar \(f\) en TypeScript; consume `reparto` del backend.

Tres métodos, DGPs etiquetados (el proceso generador es la etiqueta, no el score). Accuracy = en meses \(|\Delta|\ge 0{,}15\), `pctTendencia≥50` coincide con la etiqueta:

| Caso | Etiqueta | OLS | Fotocopia 3m | `factor_formula` |
| :--- | :--- | ---: | ---: | ---: |
| Recorte opex que se queda | estructural | 0 % | 67 % | **100 %** |
| Cobrar este mes lo del siguiente | coyuntural | 100 % | 100 % | **100 %** |
| Bache de cobros que vuelve | coyuntural | 100 % | 100 % | **100 %** |
| Caída exponencial suave (~4 %/mes) | estructural | 0 % | 67 % | 67 % |
| Seno anual | coyuntural | 67 % | 0 % | **100 %** |
| Pagar proveedores un mes tarde | coyuntural | 100 % | 100 % | **100 %** |
| Shock de tipo (deuda se queda) | estructural | 0 % | 67 % | **100 %** |
| **Media** | | **52 %** | **71 %** | **95 %** |

Mecánica: congelar mes \(t\) a flujos de \(t-1\), descongelar campos en orden declarado (`expenses → debt_service → refunds → hhi → receipts → funding_gap → quality`), cada paso por `calculate_scores`. Identidad `sum(drivers)≈Δ` (tol 0,05). Orden = Shapley de camino, no grafo causal. `causal: false`.

**No identificabilidad.** `expenses[t]` no distingue recortar opex de retrasar proveedor. `receipts[t]` no distingue vender más de adelantar cobro. El tipo es un **prior** (opex/deuda estructural; gap coyuntural; cobros mixto). Overrides: conservación de suma \(t\) y \(t+1\); \(|\Delta\mathrm{DSO}|\ge 5\); YoY de calendario si el mes se movió; cobro puntual (≥40 % del año y ≥4× mediana de los otros meses), también cuando **sale** de la ventana 3m. Gastos **sin** \(t+1\) se quedan en opex (test `test_dpo_without_next_month_keeps_the_opex_prior`). Sin AP no hay almuerzo gratis.

El 30/70 aplasta arrastre de ventana (mes 2 de un recorte no es un segundo recorte). El entregable honesto es `drivers[]`. No usar \(\varphi=0{,}8\) aquí (opex no “se le pasa”). No retocar umbrales del monitor para que el anillo quede bonito.

**Lumps (COMP_0902 y similares).** Un cobro gordo entra en la ventana 3m → \(S\) sube; sale → \(S\) se cae. El prior de arrastre gritaba 100 % tendencia. El cono v2 revertía a \(\mu_{12}\) que aún recuerda el spike. Palanca C: anillo marca `cobro_puntual` (coyuntural) al aterrizar **y** al salir; cono lumpy (≤2 meses con cobro o un mes ≥50 % del año) usa **mediana** 12m en el central y deja el alto soñar la media. No unifica las dos preguntas; las hace consistentes. Umbral de lumpy = firma, no medición de régimen. Research `descomposicion_factores.md` describe el motor pre-0902; `cobro_puntual` está en código/tests.

Detalle: `research/descomposicion_factores.md`, `research/guia_front_reparto_bache_tendencia.md`.

---

## 7. Previsión estructural (`forecasting/`)

El laboratorio del PR #9 predice **score en \(t+h\)** (a menudo \(\Delta S\)) con features de \(t\). Con 24 meses sintéticos eso redescubre \(f\). El approach de producto:

1. Proyectar cobros, pagos, deuda.
2. Rellenar **todos** los meses hasta \(h\) (el motor usa ventanas 3 y 6).
3. Aplicar `calculate_scores` congelado.

`structural_v2` (`forecasting/structural.py`, `PHI=0.8`):

\[
\mathrm{flujo}_h=\mu_{12}+(0{,}8)^{h}(\mathrm{run\text{-}rate}_3-\mu_{12}).
\]

Estación: si el mismo mes del año pasado está observado, escala `clip(valor_YoY/\mu, 0.5, 2)`. Bandas: vol MoM del run-rate, \(\times\sqrt{h}\), clip 5–25 %, tope 0,80. No son cuantiles de residuales (el lab sí usa P10/P50/P90 de residuales, cobertura 80 % **nominal marginal**, banda neutra ±3, Brier; **no PD**).

v1 (inercia del 3m) no decía “va a peor” en el P50. v2: recall deterioro 10 %→46 % (3m), 4 %→57 % (6m). MAE 1m 3,74→4,21. Huber de laboratorio: MAE 1m **4,17**. Diferencia 0,04 pts. Se eligió identificabilidad y dirección, no el MAE mínimo. El estructural **no entra** en `LEADERBOARD.md`. Candidato de lab ≠ promoción.

Protocolo: split por `group_id` 60/20/10/10, corte temporal, semilla 419. A 6 meses hay **un** origen de train y uno de test (59 empresas / 15 grupos). Comparar MAE 6m vs 3m es tramposo (cambian N y periodos). No redes profundas. Oráculo de caja **nunca** feature. 19 DGPs sintéticos (`SYN_*`, inspiración pública Embat, no cifras de clientes). BCE/Eurostat se midieron: Ridge+contexto **empeora** a 1m; no se presenta como win. País 230/1286; sector 0. Abstención: 278 empresas sin 6 meses consecutivos calidad ≥ 0,8.

IC de la segunda tanda no están ajustados por selección múltiple (Cawley & Talbot 2010). A 3m nada gana a `trailing_mean`. A 6m todos los IC incluyen 0.

Fuentes: `forecasting/METHODOLOGY.md`, `forecasting/benchmarks/structural-v2/REPORT.md`, `forecasting/GUIA_FRONT_ESTRUCTURAL.md`.

---

## 8. Contrafactuales (`levers.py`, research capa intermedia)

`/simulate` = clonar panel, mutar, `calculate_scores` + `classify_states` con el mismo `ScoreConfig`. No gradiente. Motivo real (no hay percentiles): kinks Hill/tanh, ventanas, deadband entero, clip, switches.

Contrato `contrafactual_de_corte`: mutar **solo** el último mes del extracto (`LAST_MONTH=-1`, agosto 2026 / índice 23). Prefijo `score[:, :23]` idéntico. \(\Delta M=0\) por construcción. Copy: *si el último mes del extracto hubiera sido así*, no proyección a 90 días. Reescribir jun–jul para fabricar momentum está prohibido como default.

Dos familias. El motor premia DPO como liquidez; un tesorero no. Salud (`sugerencias[]`) ordena por \(\Delta S\). Circulante (`opciones_circulante[]`) ordena por euros netos y pone `delta_score=null`. Concatenar y reordenar por \(\Delta S\) es un bug.

Costes: `adelantar_cobros` unifica descuento (`lineas[]`: facturas/clientes, días, tasa). Tasa 0 solo con supuesto tipado. Confirming: fee, no baja `expenses`. `delta_bps=null` (87 tipos / 40 empresas; implícito no es tipo). `caja_liberada` = circulante, no beneficio. `is_prior` → cero palancas.

Dual: simulate = *si tiro \(L\)*; outlook = *si no revierto*. Circulante se deshace, no se persiste.

Fuentes: `research/capa_intermedia_mejoras.md`, `research/capa_intermedia_decisiones.md`, `respuestas_a_pedro.md`.

---

## 9. Grupo y grafo

Motor puntúa **filiales**. Consolidado en API `backend/routes/stats.py`, no en `score_engine.py` ni `build_duckdb.py` (el README §2.5 apunta mal).

\[
S_{\mathrm{grupo}}=0{,}65\,\bar S + 0{,}35\,\min S
\]

Media **aritmética**, no ponderada por volumen. `contagion_penalty=\max(0,(40-S_{\min})\cdot 0{,}25)` si \(S_{\min}<40\): campo **aparte**, no se resta del consolidado.

Grafo clientes: cruce 0,0 % → no existe. HHI de *tus* facturas era el plan; score vivo usa HHI banco en **74** empresas.

Grafo intra-grupo (`backend/routes/graph.py`): misma fecha, `amount_A=-amount_B`, ≥ 500 €, categorías transfer/payment/collection/cash_settlement/`-`. Default `min_matches=2`. Intra 4,5 coincidencias/par vs inter 0,19 (~24×). \(P(X\ge 2\mid \lambda=0{,}19)\approx 1{,}6\%\). No contagia scores.

`transfer` no se resta al consolidar: entra en \(L\) de cada filial vía fallback. El filtro de doble conteo de PRODUCTO **no está**. No improvisarlo en un what-if.

Stress `group_contagion`: shock compartido 0,45 de cobros. No valida red de contrapartes.

---

## 10. Mapa de archivos para no contradecir el motor

| Si vas a… | Lee primero | No hagas |
| :--- | :--- | :--- |
| Cambiar \(L/C/D/M/G/F\) | este doc §1–3, `score_engine.py`, tests `test_score_engine.py` | Tunear pesos mirando una ficha; encender caja solo en simulate |
| Explicar un \(\Delta S\) | identidad de puntos + clip; si es el anillo, `score_decompose.py` | OLS sobre el score; SHAP; llamar “causal” al anillo |
| Pintar un estado o alerta | `score_states.py`, `EPISODIOS.md` | Mezclar `BACHE` con el 30/70; usar outlook como `DETERIORO` |
| Simular una palanca | `capa_intermedia_mejoras.md` §0–1, `levers.py` | Mutar meses 21–22; ordenar DPO por \(\Delta S\); inventar bps |
| Proyectar a 6–12 meses | `structural.py`, `METHODOLOGY.md` | Predecir \(\Delta S\) y venderlo como el cono de producto; interpolar 1/3/6 como trayectoria de \(f\) |
| Hablar de grafo / grupo | `informe_exploracion.md`, `graph.py`, `stats.py` | DebtRank; restar contagio en silencio; HHI de 1.286 empresas |
| Validar “si acierta” | Hugo §3, whitepaper §6–7, `calibration.json` | Colgar antelación 14 meses como resultado en cartera real; AUC de PD |

Divergencias docs vs código (gana código): \(G\propto\min(q_{3,t},q_{3,t-3})\) no \(q_3\); caja **sustituye** \(L_{\mathrm{bank}}\); `observed_blend` muerto; EMA ½ y 2/7 no \(E_3-E_6\); `history_ready` = 6 observados consecutivos; consolidado 0,65/0,35 en `stats.py` con media simple; HHI invoices no está on.

---

## 11. Lo que el score no es (para no afirmarlo)

- No es un modelo de impago ni una PD. No hay Gini/AUC de default. ELMS del brief es coherencia futura, nunca entrenamiento.
- No es Informa ni un bureau. Complementa fotos contables tardías con flujo; el dato es sintético.
- No es comparable entre sectores: misma Hill/tanh para constructora y consultora.
- No ve el 58 % del volumen no mapeado a categorías “limpias” más que por signo.
- No ve caja histórica ni ERP histórico en el núcleo oficial.
- No es estable a 6 meses como pedía el brief (ρ≈0,33).
- \(M\) no es un predictor validado del margen futuro en el panel real.
- `lead_months` en vivo no es “meses hasta quiebra”.
- P10/P50/P90 de laboratorio no son caminos de cuenta; las bandas estructurales no son un 80 % calibrado.

El chasis (point-in-time, \(O(1)\), identidad aditiva, abstención, una sola \(f\)) es el contrato. La señal (qué fracción es salud vs artefacto del categorizador) es la crítica abierta de Hugo. Cualquier cambio de \(f\) es un cambio de modelo, no un hotfix de front.
