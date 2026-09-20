# Respuestas Técnicas Verificadas para Pedro y Carlos · X-Ray Engine & What-If

**Contexto:** Integración de la capa de palancas y simulación contrafactual (`/simulate`) sobre el motor analítico de solvencia bancaria de **X-Ray** (HackSpain 2026 · Track Embat).  
Documento auditado y verificado línea a línea contra el código fuente real del repositorio (`algorithm/score_engine.py`, `algorithm/score_data.py`, `algorithm/score_whatif.py`, `algorithm/calc_score.py`, `backend/main.py`, `backend/routes/whatif.py`, `algorithm/engine_results/score_manifest.json` y `xray.duckdb`).

---

### Firma y paneles

#### 1. ¿Congeláis la firma `calculate_scores(bank, erp=None, config=None)` y los nombres de salida (`score`, `liquidity_points`, `collections_points`, `debt_points`, `momentum_points`, `is_prior`, `cash_known`, `erp_used`, `debt_service_observed`, …)?
**SÍ, 100% congelada.**
* **Firma exacta en código** ([`algorithm/score_engine.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/score_engine.py#L139)):
  ```python
  def calculate_scores(
      bank: Mapping[str, np.ndarray],
      erp: Mapping[str, np.ndarray] | None = None,
      config: ScoreConfig | None = None
  ) -> dict[str, np.ndarray]:
  ```
* **Nombres de salida exactos devueltos por `calculate_scores` (41 claves):**
  `score`, `base_health`, `L`, `L_bank`, `C`, `C_bank`, `D`, `momentum`, `growth_quality`, `fragility`, `liquidity_points`, `collections_points`, `debt_points`, `momentum_points`, `growth_points`, `fragility_points`, `clipping_points`, `raw_score`, `erp_collection_adjustment_points`, `bank_quality`, `confidence_index`, `data_confidence_index`, `erp_weight_used`, `erp_growth_weight_used`, `erp_used`, `cash_known`, `cash_used`, `commitments_known`, `dso_change_known`, `hhi_used`, `liquidity_available`, `collections_available`, `debt_service_observed`, `fragility_evidence`, `history_ready`, `momentum_ready`, `observed_months`, `bank_base_health`, `monthly_flow_margin`, `monthly_data_quality`, `flow_margin_available`, `is_prior`.
* **Claves añadidas de trayectoria por `classify_states` (8 claves):**
  `state`, `state_eligible`, `state_provisional`, `state_quality`, `health_band`, `state_evaluation_reason`, `seasonality_available`, `annual_pattern_match`.
* Ninguna de estas claves se va a renombrar, mover o eliminar.

#### 2. ¿El panel banco sigue siendo `receipts` / `expenses` / `debt_service` / `gross_receipts` / `refunds` / `quality` / `funding_gap` / `hhi` (+ opcionales de caja)?
**SÍ.**
* **Requeridos estrictos:** `receipts` (debe existir en el dict), `expenses`, `debt_service`. Matrices 2D NumPy `float` de forma `(N, M)` con importes no negativos o `NaN`. `quality` con valores en $[0, 1]$ (si se omite, default es 1.0).
* **Opcionales evaluados del motor bancario:** `gross_receipts` ($\ge 0$), `refunds` ($\ge 0$), `funding_gap` ($\ge 0$), `hhi` ($[0, 1]$), `hhi_quality` ($[0, 1]$). Si se omiten, el motor aplica default `np.nan` (o 0).
* **Opcionales de caja (inactivos este fin de semana):** `cash_balance`, `commitments_30d`, `negative_balance_fraction`.
* **Validación interna:** [`validate_optional_fields`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/score_engine.py#L71) exige que todos compartan forma `(N, M)` y cumplan sus cotas matemáticas.

#### 3. ¿`debt_service` sigue saliendo solo de `debt_repayment` + `interest_charge` (no de `outstanding`)?
**SÍ.**
* **Código fuente exacto** ([`algorithm/score_data.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/score_data.py#L14-L57)):
  ```python
  DEBT_CATEGORIES = {'debt_repayment', 'interest_charge'}
  # ...
  if category in DEBT_CATEGORIES and amount < 0:
      return 'debt_service', -amount
  ```
* `debt_service` captura exclusivamente salidas reales de caja en el extracto bancario imputadas al pago de cuotas de deuda o liquidación de intereses.
* **No computa saldos vivos concedidos (`outstanding_balance`)** de productos de crédito (`debt_products.csv`). Es un flujo mensual de caja saliente, no una foto estática de balance.

---

### Defaults que no podemos romper

#### 4. ¿`/score` (y cualquier artefacto oficial) sigue con ERP off y `cash_known=0` este fin de semana?
**SÍ.**
* **Evidencia oficial congelada** en [`algorithm/engine_results/score_manifest.json`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/engine_results/score_manifest.json#L34-L68):
  ```json
  "audit": {
    "erp": {
      "mode": "disabled_without_verified_direction_and_historical_states"
    }
  },
  "cash_observations_sha256": null,
  "endpoint_cash_known_count": 0,
  "endpoint_erp_used_count": 0
  ```
* Tanto `scores_monthly.csv`, como `score_panels.npz`, como las tablas analíticas de [`xray.duckdb`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/xray.duckdb) están precomputadas bajo esta premisa para no romper la comparabilidad longitudinal de 24 meses.

#### 5. Si en algún momento encendéis caja u ERP, ¿lo haréis en score y simulate a la vez con bump de `model_version` (nunca solo en simulate)?
**SÍ, 100% de acuerdo.**
* **Mecanismo técnico** ([`algorithm/calc_score.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/calc_score.py#L102-L105)):
  `model_version` se computa como el SHA-256 de los hashes de código del motor, `ScoreConfig`, `StateConfig` y el modo de auditoría ERP (`audit['erp']['mode']`).
* Cualquier activación de ERP o Caja altera la identidad algorítmica del sistema, obligando a generar un nuevo `model_version` tanto para la baseline oficial como para las proyecciones. Jamás existirá divergencia entre `/score` y la línea base de `/simulate`.

#### 6. ¿Vais a meter percentiles/peers (B2) en el motor a corto plazo, o seguimos en Hill/tanh como ahora?
**NO hay peers; SEGUIMOS 100% en Hill/tanh.**
* **Justificación técnica:** Todas las sub-puntuaciones de [`algorithm/score_engine.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/score_engine.py) están calibradas analíticamente por empresa de forma univariada:
  - Liquidez: $L = 0.5 + 0.5 \cdot \tanh(\text{flow\_margin} / 0.50)$
  - Regularidad: $1 / (1 + \text{CV}(r))$
  - Endeudamiento: $D = 0.5 - 0.5 \cdot \tanh(\text{debt\_burden} / 0.25)$
  - Estrés de liquidez: $\text{Hill}(\text{gap\_ratio}, 0.50)$
* Al no depender de percentiles de cohorte cruzada, calcular o simular una empresa es una operación puramente $O(1)$ que tarda menos de **4 milisegundos**.

---

### Cómo me dejáis mutar para simular

#### 7. ¿Quién construye/expone el panel empresa×mes para que yo haga la fotocopia: lo clono yo desde `score_data.load_bank_panel`, o me dais una API/función interna tipo `get_panels(entity_id)` + `score(panels)`?
**AVISO CRÍTICO DE ARQUITECTURA Y RENDIMIENTO:**
* **NO llaméis a `score_data.load_bank_panel` en cada request HTTP:** Esa función parsea 2.55 millones de transacciones de `transactions.csv` y tarda **13.1 segundos** de CPU. Meterla en un endpoint tumbaría la API por timeout.
* **`score_panels.npz` NO contiene las entradas bancarias raw:** Sólo almacena las matrices de *salida* del motor (`score`, `L`, `liquidity_points`, etc.), no las entradas de `receipts`, `expenses` o `debt_service`.
* **Solución que os proporcionamos:**
  Os dejamos una función helper interna:
  ```python
  def get_company_bank_slice(company_id: str) -> dict[str, np.ndarray]:
      ...
  ```
  Alimentada desde una precarga en memoria o desde `engine_results/bank_inputs.npz` (un archivo de apenas ~2.5 MB que serializa los arrays de entrada para las 1.286 empresas).
  - Devuelve en **< 1 ms** el diccionario bancario listo con `shape=(1, 24)`.
  - Vuestro simulador simplemente hace una copia mutable del slice, aplica las palancas en el mes 23 y llama directamente a `calculate_scores(bank_mutado)`.

#### 8. ¿OK que mi `/simulate` mute solo el último mes del panel (`as_of=2026-09-01`, txs en agosto) y recalcule con el mismo `ScoreConfig`?
**SÍ, 100% OK.**
* El último mes corresponde al índice temporal 23 (`month=23`, corte `2026-09-01`).
* **Comportamiento en el motor:**
  - Las ventanas móviles de 3 meses (`r3`, `e3`, `h3`) en el mes 23 abarcan los meses 21, 22 y 23. Por tanto, mutar el mes 23 actualiza inmediatamente el margen de flujo $\frac{r3-e3}{r3+e3} \to L$, el ratio de deuda $\frac{h3}{r3+h3} \to D$, la fragilidad $F$ y el `score`.
  - En la clasificación de estados (`score_states.py`), un incremento de score $> 3.0$ puntos activa `opposing_positive`, rompe la inercia de deterioro (`hold`) y permite transicionar de `DETERIORO`/`TORCIENDOSE` a `ESTABLE` o `MEJORANDO`.
* **Advertencia matemática:** Al ser promedios móviles trimestrales, una inyección de $X$ euros en el mes 23 se distribuye en la ventana como $X/3$. Esto es financieramente realista y protege contra picos cosméticos de un solo mes.

#### 9. ¿OK el mapa cobros: bajar `pending` de AR e inyectar en `receipts`/`gross_receipts` + recalcular `funding_gap` de ese mes? ¿Lo preferís vosotros en el adaptador o lo hago yo en mi capa?
**SÍ al mapa financiero. Hacedlo vosotros en vuestra capa de palancas.**
* **Fórmula canónica en el mes 23:**
  Si se anticipan $X$ euros netos de facturas pendientes de cobro:
  - `receipts[:, 23] += X`
  - `gross_receipts[:, 23] += X`
  - `funding_gap[:, 23] = np.maximum(funding_gap[:, 23] - X, 0.0)`
* Como las palancas de factoring implican comisiones de descuento (haircut 2-5%), tipos de anticipo y selección de facturas específicas por cliente y vencimiento, es mucho más limpio que esa lógica resida en vuestro módulo de simulación antes de inyectar el panel a `calculate_scores`.

#### 10. ¿OK mutar `expenses` solo en categorías `salary` ∪ `utility` (opex) y `payment`/`bulk_payment` (DPO / circulante)?
**SÍ.**
* En [`algorithm/score_data.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/score_data.py#L13), `EXPENSE_CATEGORIES` está definida como:
  ```python
  EXPENSE_CATEGORIES = {'payment', 'bulk_payment', 'salary', 'social_security', 'tax', 'utility', 'fee'}
  ```
* Reducir OPEX (`salary`, `utility`) o diferir pagos a proveedores extendiendo DPO (`payment`, `bulk_payment`) reduce `expenses[:, 23]`.
* Recordad aplicar siempre cota inferior: `expenses[:, 23] = np.maximum(expenses[:, 23] - ahorro, 0.0)`.
* Esto expande directamente el flujo neto mensual, aumenta $L$ y despresuriza el ratio de timing stress.

#### 11. ¿OK bajar `debt_service` / `interest_charge` recurrente para refinanciar (nunca vender un repayment one-shot como mejora de D)?
**SÍ, absolutamente rotundo y crucial.**
* En [`algorithm/score_engine.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/score_engine.py#L176):
  $$\text{debt\_burden} = \frac{h_3}{r_3 + h_3}, \quad D = 0.5 - 0.5 \cdot \tanh\left(\frac{\text{debt\_burden}}{0.25}\right)$$
* En extractos bancarios, una amortización de golpe (*one-shot repayment*) entra como `debt_repayment` saliente, lo cual **aumenta** `debt_service` puntual y penalizaría gravemente el ratio de solvencia $D$.
* La refinanciación real alarga plazos o negocia mejores tipos, lo que **reduce la cuota periódica mensual** de amortización e intereses. Reducir `debt_service[:, 23]` recurrente es la forma exacta de simular una mejora en $D$.

---

### Línea / caja / ERP

#### 12. Con caja off, ¿aceptáis que utilización/amortizar/disponer/vender_inversiones devuelvan euros + `delta_score=null`, y que amortizar/disponer además pueda acoplar una bajada de intereses para que algo mueva D?
**SÍ, totalmente aceptado.**
* Con `cash_balance` apagado, los movimientos de balance y tesorería patrimonial (mover saldos entre cuentas, disponer de líneas de crédito sin venta o monetizar inversiones) no son ingresos comerciales (`receipts`) ni gastos de explotación (`expenses`).
* Responder con los euros liberados de liquidez patrimonial y `delta_score = null` (o `0.0` con nota técnica de balance) es financieramente impecable.
* Y acoplar a la amortización de pasivo una reducción en la cuota mensual recurrente de `debt_service` para generar un impacto positivo en $D$ es el mecanismo perfecto.

#### 13. ¿Hay plan de ERP histórico as-of (DSO mes a mes), o el snapshot solo a 2026-09-01 se queda así? (Si no hay histórico, no prometo “reducir DSO en mes 18”.)
**NO hay plan de ERP histórico mes a mes; el snapshot se queda a 2026-09-01.**
* En `dataset/invoices.csv`, el campo `pending_amount` es un dato estático a fecha actual (`2026-09-01`). No disponemos del saldo vivo histórico de cada factura en meses anteriores (2024/2025) sin cometer *data leakage*.
* Por tanto, **no prometáis reducir DSO en el mes 18**. Cualquier simulación de palanca de ERP/DSO debe operar sobre el corte actual (`2026-09-01`) o proyectar hacia el futuro (mes +1 / +3).

---

### API / despliegue

#### 14. ¿Quién monta el HTTP (`/score`, `/simulate`, …): Antonio la API y yo solo el dominio de palancas, o meto yo FastAPI en un módulo que luego engancháis?
**Antonio ya tiene montada la API FastAPI centralizada.**
* En [`backend/main.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/backend/main.py) ya está desplegado el servidor FastAPI con CORS configurado, DuckDB conectado y documentación interactiva Swagger en `/docs`.
* Actualmente ya existe un endpoint en [`backend/routes/whatif.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/backend/routes/whatif.py) con la ruta `POST /api/whatif`.
* **Cómo nos coordinamos:**
  - **Opción A (Recomendada):** Escribís vuestro dominio de palancas en un módulo (ej. `algorithm/levers.py` o `backend/levers.py`) con una función limpia `simulate_levers(payload: dict) -> dict`. Nosotros la conectamos al endpoint.
  - **Opción B (Router FastAPI independiente):** Si preferís implementar el router vosotros, cread `backend/routes/simulate.py` con `router = APIRouter(prefix="/api/simulate")`. Antonio sólo tendrá que añadir `app.include_router(simulate_router)` en [`backend/main.py`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/backend/main.py) y quedará integrado de inmediato.

#### 15. ¿Hay ya (o habrá hoy) un `model_version` / hash de motor+datos que yo deba devolver en cada `/simulate`?
**SÍ, YA EXISTE.**
* El hash oficial actual registrado en [`algorithm/engine_results/score_manifest.json`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/algorithm/engine_results/score_manifest.json#L48) es:
  ```
  "model_version": "7c92ba879e37066fcbb1f8e3d3974026d370eb48f5c091238f31865bdcc684a8"
  ```
* Incluidlo como campo `"model_version"` en el JSON de respuesta de `/simulate` para auditoría y trazabilidad ante el jurado.

---

### No bloqueante pero útil

#### 16. ¿Los paneles precomputados (`engine_results/score_panels.npz`) son la fuente de verdad del endpoint o se puede rescorear on the fly siempre?
* **Para lectura y filtrado de cartera (CFO Dashboard):** La fuente de verdad ultra-rápida (< 5 ms) es la base de datos [`xray.duckdb`](file:///Users/antoniomachuca/Documents/REPO%20HACKATHON/xray.duckdb) (vista `v_latest_company_scores` y tabla `company_scores`).
* **Para `/simulate`:** **SÍ se puede y se debe rescorear on the fly**.
  - `calculate_scores` sobre un slice individual `(1, 24)` tarda apenas **3.9 milisegundos**.
  - Esto garantiza respuestas de la API en 10–20 ms, permitiendo sliders reactivos y fluidos en el frontend sin latencia perceptible.

#### 17. ¿Alguna empresa/fixture que queráis fijar vosotros para demo además de trayectorias tipo `COMP_0153` / `COMP_0176` / `COMP_0031`?
*(Auditoría de datos reales verificada en `xray.duckdb` y `company_scores`)*:

| Empresa | Grupo | Score | Estado | Banda | $\Delta 3\text{m}$ | $L_{\text{pts}}$ | $D_{\text{pts}}$ | Caso de Uso para Demo |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`COMP_0176`** | `GROUP_0225` | **5.1** | **`DETERIORO`** | `DEBIL` | **-77.7** | 0.9 | 0.0 | **Colapso de solvencia (Killer Demo).** Asfixia de deuda y flujo nulo. Una inyección o refinanciación la saca de quiebra. |
| **`COMP_0122`** | `GROUP_0086` | **57.4** | **`TORCIENDOSE`** | `INTERMEDIA` | **-18.7** | 27.2 | 10.0 | **Alerta temprana preventiva.** Aparenta solvencia pero la aceleración negativa avisa antes de que entre en impago. |
| **`COMP_0010`** | `GROUP_0013` | **45.6** | **`BACHE`** | `INTERMEDIA` | **-26.7** | 20.0 | 10.0 | **Bache vs Insolvencia.** Caída transitoria aislada con éxito. Tiene facturas reales impagadas en `invoices.csv` (fixture de tests backend). |
| **`COMP_0805`** | `GROUP_0213` | **67.5** | **`RECUPERACION`** | `INTERMEDIA` | **+44.9** | 33.1 | 10.0 | **Trayectoria de éxito.** Demuestra cómo el motor premia la recuperación consistente de flujo tras un bache previo. |
| **`COMP_0153`** | `GROUP_0115` | **83.4** | **`ESTABLE`** | `SOLIDA` | **+15.3** | 48.6 | 10.0 | **Empresa excelente de control.** Excelente salud y liquidez máxima ($L=48.6$). Sirve para contrastar contra el deterioro de `COMP_0176`. |

*(Nota de auditoría: En el borrador inicial se habían transpuesto accidentalmente `COMP_0153` y `COMP_0176` y citado `GROUP_0055` en vez de `GROUP_0013`; esta tabla contiene los datos exactos del motor).*
