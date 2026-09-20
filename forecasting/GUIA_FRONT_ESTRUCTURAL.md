# Guía para el front: tres escenarios estructurales en el gráfico principal

Esto es lo que hay que hacer para que **Histórico y proyección** (home y ficha `/{company_id}`) pinte el abanico con el algoritmo estructural, no con `momentum × 14`.

**Regla de oro:** el front **no calcula** el estructural. No hay que portar `forecasting/structural.py` a TypeScript. El motor de score (`calculate_scores`) usa ventanas de 3 y 6 meses sobre cobros, pagos, deuda, calidad, HHI, etc. Eso vive en Python. El front solo **pide** tres series de score y las **dibuja**.

---

## 1. Qué ve hoy el usuario

El gráfico principal es `front/components/prevision.tsx`, usado desde:

- `front/app/page.tsx` (home)
- `front/app/[company_id]/page.tsx` (ficha)

Hoy, si no llega `proyeccion`, el componente inventa el abanico en el cliente:

```ts
central = scoreHoy + momentum * 14
amplitud = 9 + |momentum| * 13
alto / bajo = central ± amplitud
```

`momentum` sale de `GET /api/companies/{id}` (componente del score **actual**, no un forecast). Las sendas intermedias son un puente con ruido (`senda(...)`). Eso **no** es el modelo estructural.

La página de laboratorio `/prevision` (`ForecastChart` + `getForecastPage`) es **otra cosa**: lee `forecasting/artifacts/forecasts.json` (Ridge / media reciente / el ganador del benchmark). Tampoco es estructural. No la uses para este gráfico.

---

## 2. El front ya está a medio cablear

En la rama actual el gráfico **ya acepta** el estructural si le pasas esto:

```ts
proyeccion?: { alto: number[]; medio: number[]; bajo: number[] } | null
```

Contrato que el componente exige (`prevision.tsx`):

| Campo | Significado | Longitud | Unidades |
|---|---|---|---|
| `alto` | escenario **optimista** (mejor para el score) | exactamente `meses` (por defecto **12**) | score 0–100, **un valor por mes futuro** (`t+1` … `t+12`) |
| `medio` | escenario **central** | igual | igual |
| `bajo` | escenario **pesimista** | igual | igual |

- **No** incluye el score de hoy. El componente hace `[hoy, ...proyeccion.alto]`.
- Si falta `proyeccion`, o alguna serie no tiene 12 puntos, cae al fallback de momentum.
- Home y ficha ya hacen `proyeccion={proyeccion}` y llaman a `cargarPrevision(id)`.

**Lo que falta en el front:** `cargarPrevision` **no existe** en `front/lib/motor.ts` (está importada y no definida). Tampoco hay `apiPrevision` en `front/lib/api.ts`. Eso es el trabajo de front, una vez el back sirva el JSON.

Mapeo de nombres (no confundir):

| Gráfico (front) | Algoritmo (Python) | API de laboratorio (`points[]`) |
|---|---|---|
| `alto` | `optimistic` | `optimistic` / P90 |
| `medio` | `central` | `conservative` / P50 |
| `bajo` | `pessimistic` | `pessimistic` / P10 |

Alto = cuenta que **ayuda** al score (más cobros, menos gastos, menos deuda). Bajo = lo contrario. No es “más caja” en abstracto: es el score después de puntuar esa cuenta.

---

## 3. Dónde está el algoritmo (back / lab)

| Pieza | Ruta | Qué hace |
|---|---|---|
| Algoritmo | `forecasting/structural.py` | Proyecta flujos + puntúa |
| Factory del lab | `forecasting/experiments/structural_v1.py` | Nombre `structural_v2` |
| Motor de score (congelado) | `algorithm/score_engine.py` → `calculate_scores` | Convierte un mes de cuenta en score 0–100 |
| Panel bancario | `algorithm/score_data.py` → `load_bank_panel` | Cobros, pagos, deuda, refunds, quality… |
| Runs del lab | `forecasting/benchmarks/runs/pedro__structural-v2.json` | Métricas 1/3/6 meses, **no** series para el gráfico |
| Informe | `forecasting/benchmarks/structural-v2/REPORT.md` | Qué ganó/perdió vs Ridge |

API **existente** que **no** sirve para este gráfico:

```
GET /api/companies/{id}/forecast     →  backend/routes/forecasts.py
GET /api/forecasts
GET /api/benchmarks/forecasts
```

Esas leen `forecasting/artifacts/forecasts.json` (gitignored, se genera con `python -m forecasting.benchmark`). Devuelven **tres puntos** (horizontes 1, 3 y 6) del modelo **seleccionado por MAE** (Ridge / trailing_mean / Huber…), no 12 meses de camino estructural. `503` si no hay artefactos.

Historia de score (eso sí se usa, para la línea sólida):

```
GET /api/companies/{id}              → score y momentum de hoy
GET /api/companies/{id}/history?months=24  → trayectoria pasada
```

Definidas en `backend/routes/companies.py`. Eso alimenta `cargarEmpresa` → `e.trayectoria` + `e.momentum`.

---

## 4. Qué hace el estructural (para no implementarlo mal)

Objetivo: **no adivinar el número**. Adivinar la **cuenta** de los próximos meses y pasar cada mes por el mismo `calculate_scores` de producción.

### 4.1. Tres caminos de flujos, luego el score

Para cobros (`receipts`), pagos (`expenses`) y servicio de deuda (`debt_service`):

1. **Nivel corto** = media de los últimos 3 meses (run-rate).
2. **Nivel largo** = media de los últimos 12 meses (o lo que haya hasta hoy).
3. **Central del mes `h`** (h = 1…12):

   `flujo_h = media_larga + (0.8 ^ h) × (run_rate_3m − media_larga)`

   A 1 mes te quedas cerca del 3m; a 6–12 te vas a “así cobra esta empresa de verdad”.

4. **Estacionalidad:** si el mes `hoy+h−12` ya está en el histórico, se multiplica por  
   `clip(valor_hace_un_año / media_larga, 0.5, 2.0)`.  
   Si no hay año atrás, factor = 1. El panel del reto tiene 24 meses, así que para 12 meses vista **sí** hay un año.

5. **Bandas:** volatilidad mes a mes del run-rate, clip 5–25%, y se abre con el horizonte: `m × √h` (tope 0.80).

   - Cobros: optimista = central × (1+m√h), pesimista = central × (1−m√h).
   - Gastos y deuda: al revés (bajarlos ayuda al score).

6. **Reembolsos** = cobros proyectados × (ratio refunds/receipts de los últimos 3 meses). Constante.

7. Se pega esa cuenta al histórico **hasta hoy** (sin leer el futuro real) y se llama `calculate_scores`. El score de cada mes futuro es el de esa cuenta proyectada, no un Ridge sobre el índice.

Constantes en `forecasting/structural.py`: `PHI = 0.8`, `LONG_WINDOW = 12`, `RUN_WINDOW = 3`, `M_MIN/M_MAX = 0.05/0.25`.

### 4.2. Hueco importante para el gráfico (back, no front)

`StructuralForecaster.predict()` del laboratorio devuelve **un solo trío** `(pesimista, central, optimista)` en el horizonte `h` (1, 3 o 6). El gráfico necesita **12 scores por senda**.

`calculate_scores` sobre el panel proyectado ya calcula **todos** los meses. El back, para el gráfico, debe extraer:

```text
score[origin + 1], score[origin + 2], …, score[origin + 12]
```

para cada uno de los tres caminos. No basta con los `points[]` de 1/3/6 meses (eso dejaría 9 huecos y el componente rechazaría la serie).

`origin` = último mes observado del panel (índice de la columna, 0-based). Con 24 meses, origin típico = 23.

---

## 5. Contrato de API que el front necesita (hay que añadirlo en back)

Hoy **no existe**. Hay que exponerlo (Python) y luego consumirlo (TS). Propuesta alineada con el gráfico:

```http
GET /api/companies/{id}/prevision-estructural?meses=12
```

`{id}` igual que el resto: `COMP_0010` o `10` (`normalize_company_id`).

### 5.1. 200 — hay cuenta suficiente

```json
{
  "company_id": "COMP_0010",
  "model": "structural_v2",
  "as_of": "2026-08-01",
  "meses": 12,
  "current_score": 61.4,
  "alto":  [62.1, 62.8, 63.0, "...12 números"],
  "medio": [61.0, 60.7, 60.4, "..."],
  "bajo":  [59.2, 58.1, 56.9, "..."]
}
```

- `alto` / `medio` / `bajo`: arrays de **floats**, longitud = `meses`, orden cronológico `t+1` … `t+meses`.
- Clipped a `[0, 100]`.
- `as_of`: mes del corte (último observado), ISO `YYYY-MM-01`, el mismo espíritu que history.
- Si `current_score` no coincide exactamente con `e.score` de la ficha, el gráfico igual pega las sendas al último punto de `trayectoria`. No interpolar en el front.

### 5.2. Errores

| Caso | HTTP | Front |
|---|---|---|
| Empresa desconocida | 404 | como el resto de la ficha |
| Sin panel / historia corta | 200 con `status: "insufficient_history"` **o** 204/404 vacío | `cargarPrevision` → `null` → fallback momentum |
| Motor caído | fetch fail | `null` → fallback (igual que `cargarEmpresa`) |

El gráfico **ya** hace fallback si `proyeccion` es `null`. No hace falta un skeleton especial.

### 5.3. Cómo lo implementa el back (referencia, no lo hagas en TS)

Esqueleto conceptual (nombres reales del repo):

```python
from forecasting.structural import (
    StructuralForecaster, build_projected_bank, scenario_paths,
)
from algorithm.score_engine import calculate_scores

horizon = 12
model = StructuralForecaster(horizon)          # carga panel de data/ o dataset/
bank, row = model.banks[company_id]
origin = bank['receipts'].shape[1] - 1         # último mes observado
refunds = bank.get('refunds', zeros)[row]
paths = scenario_paths(
    bank['receipts'][row], bank['expenses'][row], bank['debt_service'][row],
    refunds, origin, horizon)

def scores_mensuales(nombre):  # 'optimistic' | 'central' | 'pessimistic'
    flows = {k: paths[nombre][k] for k in ('receipts', 'expenses', 'debt_service', 'refunds')}
    panel = build_projected_bank(bank, row, origin, horizon, flows)
    score = calculate_scores(panel)['score'][0]
    return score[origin + 1 : origin + 1 + horizon].clip(0, 100).tolist()

return {
    'alto': scores_mensuales('optimistic'),
    'medio': scores_mensuales('central'),
    'bajo': scores_mensuales('pessimistic'),
    ...
}
```

`load_company_banks()` ya cachea el panel. No reentrenar nada: `fit`/`calibrate` del estructural son no-ops.

Dataset: misma carpeta que el resto del API (`data/` o `dataset/`, `companies.csv` + transacciones). Si el FastAPI ya carga el panel para history, se puede reutilizar; si no, `StructuralForecaster(12)` lo carga solo.

Coste: 3 × `calculate_scores` por empresa (o 1 si se apilan los 3 caminos como 3 filas, como hace `score_named_paths`). Orden de milisegundos por request si el panel está en memoria; la primera carga del CSV es lenta (~1 min en frío). Cachear el `StructuralForecaster` a nivel de proceso.

No hace falta `forecasting/artifacts/`. No hace falta correr el benchmark.

---

## 6. Trabajo de front (checklist)

Cuando el endpoint exista:

### 6.1. `front/lib/api.ts`

Añadir tipo y GET, mismo patrón que `apiEmpresa` (fail → `null`):

```ts
export type ApiPrevisionEstructural = {
  company_id: string;
  model: string;
  as_of: string;
  meses: number;
  current_score: number;
  alto: number[];
  medio: number[];
  bajo: number[];
};

export const apiPrevisionEstructural = (id: string, meses = 12) =>
  get<ApiPrevisionEstructural>(
    `/api/companies/${encodeURIComponent(id)}/prevision-estructural?meses=${meses}`,
  );
```

Base: `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`), ya en `API`.

### 6.2. `front/lib/motor.ts`

Implementar lo que las páginas ya importan:

```ts
export async function cargarPrevision(id: string, meses = 12) {
  const r = await apiPrevisionEstructural(id, meses);
  if (!r?.alto || r.alto.length !== meses || r.medio.length !== meses || r.bajo.length !== meses) {
    return null;
  }
  return { alto: r.alto, medio: r.medio, bajo: r.bajo };
}
```

No mezclar con `getForecastPage` / `forecast-contract.ts` (eso es `/prevision` del lab).

### 6.3. Páginas

Home y `/{company_id}` **ya** hacen:

```ts
const [e, proyeccion] = await Promise.all([
  cargarEmpresa(id),
  cargarPrevision(id),
]);
// ...
<Prevision datos={e.trayectoria} momentum={e.momentum} proyeccion={proyeccion} />
```

En home: `proyeccion = real ? rawPrev : null` (en demo sin motor, no fingir estructural). Dejarlo así.

`meses={12}` es el default. Si alguien cambia el horizonte del gráfico, hay que pedir el mismo `meses` al API. Hoy el selector 6/12/24 **solo recorta el histórico**, no el horizonte de proyección (sigue siendo 12). No toques eso salvo que el producto pida otra cosa.

### 6.4. `prevision.tsx`

No hace falta redibujar el SVG. Solo verificar:

1. `proyeccion.alto.length === meses` (12).
2. Las sendas estructurales **no** pasan por `senda()` (el ruido browniano). El `if (estructural && proyeccion)` ya lo evita.
3. Orden: índice `0` = primer mes futuro, no hoy.
4. No reordenar alto/medio/bajo “por si el score se cruza”: el back ya hace `min(low, median)` / `max(high, median)` en el **último** horizonte del lab; para una senda mensual es mejor **no** cruzar a mano en el front. Si un mes el pesimista de flujos da un score un poco por encima del central, se pinta así (es raro, pero es honesto).

### 6.5. Qué no hacer

- No recalcular `momentum * 14` “por si acaso” cuando hay `proyeccion`.
- No interpolar 1, 3 y 6 meses a 12 en el cliente (el score no es lineal; el motor usa ventanas de 3/6 meses).
- No usar `/api/companies/{id}/forecast` ni `forecasts.json`.
- No pintar P10/P50/P90 de Ridge como si fueran caminos de cuenta.
- No pedir 12 meses de cobros al usuario: el back los proyecta.

---

## 7. Cómo comprobar que es el estructural de verdad

1. Arrancar FastAPI con el dataset del reto.
2. `GET /api/companies/COMP_0010/prevision-estructural?meses=12` → 12+12+12 números, `model: structural_v2`.
3. Home con `NEXT_PUBLIC_API_URL` apuntando a ese API: el pie del gráfico debe decir *“Las tres sendas proyectan cobros, gastos y deuda…”* (ya está el ternario en `page.tsx`). Si ves lo de “inercia observada”, `proyeccion` es `null`.
4. Quitar el API: el gráfico tiene que volver al abanico de momentum, no romperse.
5. Sanidad: `alto[i]` no tiene por qué ser monótono; el score puede bajar aunque los cobros reviertan. Las tres curvas salen del **mismo** hoy.

Contraejemplo útil: una empresa con cobros de 3 meses muy por encima de su media a 12 meses. El **medio** estructural a 12 meses **cae** hacia esa media (reversión). El fallback de momentum **subiría**. Si el gráfico sube, todavía está en inercia.

---

## 8. Relación con el laboratorio (1 / 3 / 6 meses)

El lab evalúa MAE en 1, 3 y 6 meses sobre grupos holdout. El producto pide un **camino de 12 meses** para el dibujo. Es el mismo algoritmo (`structural_v2`), distinto recorte temporal.

No hace falta que el gráfico muestre MAE, cobertura 80% ni el leaderboard. Si más adelante se quieren los puntos 1/3/6 en un tooltip, se pueden marcar `medio[0]`, `medio[2]`, `medio[5]` (meses 1, 3, 6) — siempre que el array sea mensual desde `t+1`.

Números de referencia (validación, no para el UI): a 1 mes MAE grupo 4,21; a 3 meses 8,16; a 6 meses 11,08. Detalle en `forecasting/benchmarks/structural-v2/REPORT.md`.

---

## 9. Orden de implementación sugerido

1. **Back:** endpoint de la sección 5 (una persona Python). Sin esto el front no puede.
2. **Front:** `api.ts` + `cargarPrevision` (hueco ya abierto).
3. Probar home y `/{company_id}` con motor arriba y abajo.
4. Dejar `/prevision` del lab como está, o una tarea aparte.

Cualquier duda de semántica (qué es “alto”, por qué 12 meses, por qué no Ridge): el estructural está en `forecasting/structural.py` y esta guía. El gráfico solo debe ser el consumidor de `alto` / `medio` / `bajo`.
