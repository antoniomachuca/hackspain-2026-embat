# Guía de implementación · reparto bache / tendencia (front)

**Para:** quien implemente el gráfico de previsión  
**Fecha:** 2026-09-19  
**Rama:** `feat/descomposicion-factores`  
**Qué hay en este PR (no toques Python):**

| Archivo | Para qué |
| :--- | :--- |
| `algorithm/score_decompose.py` | Cálculo + serializador JSON (`history_with_reparto`) |
| `algorithm/test_score_decompose.py` | Tests del algoritmo (17). No los dupliques en TS |
| `research/fixtures/reparto_demo.json` | History de dos empresas sintéticas, **mismo shape que el API** |
| `research/descomposicion_factores.md` | Por qué se cambia el método |

El anillo de «cuánto es bache y cuánto es tendencia» deja de inventarse en el cliente. Tú solo pintas JSON.

**No portes `calculate_scores` ni `attribute_month` a TypeScript.** Si el JSON no llega, el anillo se oculta. Nunca caigas a `repartir()`.

---

## 0. Decisiones cerradas (no reabras)

Pedro las cierra en este PR. No preguntes, no improvises copy.

| # | Decisión | Cerrada |
| :--- | :--- | :--- |
| D1 | ¿El front calcula el split? | **No.** Solo pinta. |
| D2 | ¿Un 70/30 o también drivers? | **Los dos.** Anillo = 70/30. Debajo, hasta 3 drivers. |
| D3 | ¿Se toca `classify_states` / color del anillo de estado? | **No.** `BACHE` ámbar del score sigue siendo persistencia 3 meses. |
| D4 | Mes vivo de cobros (no hay `t+1`) | `reason: cobros_sin_confirmar` → bache, copy «sin confirmar». |
| D5 | Si el punto no trae `reparto` | **Ocultar el anillo.** No llames a `repartir()`. |
| D6 | Copy de `kind` | `estructural` → «tendencia». `coyuntural` → «bache». Nunca «estructural» al CFO. |
| D7 | ¿Página `/descomposicion`? | **No.** Vive en `Prevision` que ya existe. |

### 0.1 Por qué se cambia (una frase)

Hoy `pendiente` + `repartir` en `front/lib/data.ts` hacen OLS a 6 meses **sobre el score**. Recortar opex (se queda) y cobrar este mes lo del siguiente (se revierte) salen iguales: ~14 % tendencia / 86 % bache. El factor los distingue: 100 % tendencia vs 100 % bache.

No es el cono P10/P50/P90, ni `φ = 0,8`, ni el estado `BACHE` del anillo grande. No las mezcles.

---

## 1. Qué hay hoy (y qué se tira)

### 1.1 Superficie

`front/components/prevision.tsx`, usado desde `front/app/page.tsx` y `front/app/[company_id]/page.tsx`.

Si llega `reparto`, el hover pinta `AnilloReparto` (morado tendencia `#b083e8`, ámbar bache `#dfb631`). Si no, el gráfico es el de siempre. **Esa puerta ya está.** v1 = tooltip con anillo + lista de drivers. v1.1 (opcional) = tira mes a mes, misma data.

### 1.2 De dónde sale el `reparto` ahora — **elimínalo del camino API**

En `front/lib/motor.ts`, al montar la empresa:

```ts
const serie = trayectoria.map((p) => p.score);
const tends = serie.map((_, k) => pendiente(serie, k));
reparto: trayectoria.map((p, k) => repartir(serie, tends, k, p.mes)),
```

Sustituye **solo** la línea de `reparto` (ver §5). `pendiente` / `inflexionDe` pueden seguir para la capa cuartil vs empresa. No las uses para el anillo.

En modo demo (`cargarEmpresa` = null) `empresa()` en `data.ts` también llama a `repartir`. Déjalo: es el mock. **No** lo uses como fallback del API.

### 1.3 Tipo de hoy (amplíalo, no lo rompas)

```ts
export type Reparto = { mes: string; delta: number; pctTendencia: number; pctBache: number };
```

`Empresa.reparto?: Reparto[]` — opcional, misma longitud que `trayectoria`, mismo `mes`.

---

## 2. Contrato JSON (cerrado, snake_case)

El campo nuevo se anida **dentro de cada punto** de `GET /api/companies/{id}/history`.

```
GET /api/companies/{id}/history
→ { company_id, months, history: [ { as_of, score, …campos de siempre…, reparto } ] }
```

- Misma malla y mismo orden que `trayectoria` (`as_of` → `YYYY-MM`).
- Índice 0 (primer mes): `reparto` vacío (`delta: 0`, `pct_*: 0`, `drivers: []`). Nunca `null`.
- `%` ya enteros. Puntos a 2 decimales.
- Drivers con `|points| < 0.05` **ya filtrados**. No vuelvas a filtrar salvo defensa.

Este PR **no modifica** `backend/routes/companies.py` ni `schemas.py` (no pisamos al resto del back). El serializador ya existe: `history_with_reparto` en `score_decompose.py`. Hasta que FastAPI anide el campo, implementas contra el fixture §2.4. El mapper es el mismo.

### 2.1 Tipos TS (cópialos a `front/lib/data.ts` y `front/lib/api.ts`)

```ts
export type KindMes = "estructural" | "coyuntural";
export type FamilyMes = "salud" | "circulante" | "dato" | "formula";

export type DriverMes = {
  field: string;
  etiqueta: string;     // ya traducida
  points: number;       // puntos de score, con signo. Suman ≈ delta
  kind: KindMes;        // estructural = tendencia; coyuntural = bache
  family: FamilyMes;
  reason: string;       // clave estable, inglés
  razon: string;        // frase corta ya traducida — píntala tal cual
};

export type Reparto = {
  mes: string;           // "2025-01"
  delta: number;
  pctTendencia: number;  // 0–100; 0 si el mes es plano
  pctBache: number;      // 0–100; suma 100 si hay movimiento
  structPts: number;
  circPts: number;
  drivers: DriverMes[];
};
```

En `front/lib/api.ts`, el punto de history gana `reparto?`:

```ts
export type ApiRepartoDriver = {
  field: string;
  etiqueta: string;
  points: number;
  kind: "estructural" | "coyuntural";
  family: "salud" | "circulante" | "dato" | "formula";
  reason: string;
  razon: string;
};

export type ApiReparto = {
  delta: number;
  pct_tendencia: number;
  pct_bache: number;
  struct_pts: number;
  circ_pts: number;
  drivers: ApiRepartoDriver[];
};

export type ApiHistoria = {
  company_id: string; months: number;
  history: Array<{
    as_of: string; score: number; base_health: number; state: string;
    momentum: number; data_confidence_index: number;
    reparto?: ApiReparto;
  } & Omit<ApiWaterfall, "clipping_points">>;
};
```

### 2.2 Ejemplo real — recorte de opex (mes del salto)

Del fixture `DEMO_OPEX`, `history[12]`, `as_of: 2025-01-01`:

```json
{
  "as_of": "2025-01-01",
  "score": 67.0,
  "reparto": {
    "delta": 1.71,
    "pct_tendencia": 100,
    "pct_bache": 0,
    "struct_pts": 1.71,
    "circ_pts": 0.0,
    "drivers": [
      {
        "field": "expenses",
        "etiqueta": "Gastos",
        "points": 1.71,
        "kind": "estructural",
        "family": "salud",
        "reason": "opex",
        "razon": "se queda"
      }
    ]
  }
}
```

Anillo: **100 % tendencia**. Primera línea: `Gastos  se queda  +1,7`.

Si ves 86 % bache, sigues en OLS.

### 2.3 Ejemplo real — cobrar este mes lo del siguiente

`DEMO_COBROS`, mes del salto (`2025-01`):

```json
{
  "delta": 2.69,
  "pct_tendencia": 0,
  "pct_bache": 100,
  "drivers": [
    {
      "field": "receipts",
      "etiqueta": "Cobros",
      "points": 2.69,
      "kind": "coyuntural",
      "reason": "pulso_cobros",
      "razon": "timing de cobros"
    }
  ]
}
```

Mes siguiente (`2025-02`) — **por esto el anillo solo no basta:**

```json
{
  "delta": -5.51,
  "pct_tendencia": 31,
  "pct_bache": 69,
  "struct_pts": 4.64,
  "circ_pts": -10.14,
  "drivers": [
    {
      "field": "arrastre",
      "etiqueta": "Ventana 3 meses",
      "points": 4.64,
      "kind": "estructural",
      "reason": "arrastre",
      "razon": "ventana 3 meses"
    },
    {
      "field": "receipts",
      "etiqueta": "Cobros",
      "points": -10.14,
      "kind": "coyuntural",
      "reason": "pulso_cobros",
      "razon": "timing de cobros"
    }
  ]
}
```

Tooltip de febrero: anillo 31/69 + dos líneas (ventana + cobros). No «arregles» el 31/69.

### 2.4 Fixture para implementar ya (sin esperar FastAPI)

`research/fixtures/reparto_demo.json`:

```json
{
  "shock_index": 12,
  "shock_as_of": "2025-01-01",
  "companies": [
    { "company_id": "DEMO_OPEX", "months": 24, "history": [ /* 24 puntos con reparto */ ] },
    { "company_id": "DEMO_COBROS", "months": 24, "history": [ /* idem */ ] }
  ]
}
```

Cópialo a `front/lib/reparto-demo.json` si quieres importarlo. Úsalo para verificar el tooltip. **No lo dejes en producción** como fallback de empresas reales: si el API no trae `reparto`, `undefined` y anillo off.

### 2.5 `field` / `reason` (cerrados; el JSON ya trae `etiqueta` y `razon`)

Pinta `etiqueta` y `razon`. Estas tablas son por si llega un campo nuevo o quieres un fallback.

| `field` | `etiqueta` | Notas UI |
| :--- | :--- | :--- |
| `expenses` | Gastos | — |
| `receipts` | Cobros | — |
| `debt_service` | Deuda | casi siempre tendencia |
| `refunds` | Devoluciones | — |
| `hhi` | Concentración | tendencia |
| `funding_gap` | Hueco de caja | bache |
| `quality` | Cobertura del dato | ocultar si llega (filtro back ya lo quita si `< 0,05`) |
| `arrastre` | Ventana 3 meses | copy §4.3 |
| `residual` | Resto | casi nunca material |

| `reason` | `razon` |
| :--- | :--- |
| `opex` | se queda |
| `volumen` | volumen |
| `pulso_cobros` | timing de cobros |
| `pulso_pagos` | timing de pagos |
| `estacion` | calendario |
| `dso` | plazos de cobro |
| `cobros_sin_confirmar` | sin confirmar |
| `prior` | nivel |
| `stock_timing` | timing de caja |
| `ola_puntual` | ola puntual |
| `cobertura_dato` | cobertura del dato |
| `arrastre` | ventana 3 meses |
| `residual` | resto |

Si llega un `reason` desconocido: muestra `razon` si viene, si no la clave en gris. No inventes.

### 2.6 Identidad

`sum(drivers.points) ≈ delta` (tolerancia 0,05). Si no cuadra, enseña lo observado. No recalcules `pctTendencia`.

Mes plano: `pctTendencia === 0 && pctBache === 0` → no pintes anillo (ya está: `pctTendencia + pctBache > 0`).

### 2.7 Ventana 6/12/24

`Prevision` hace `repartoTodo?.slice(-rango)` igual que `datos`. El array tiene la misma longitud y el mismo orden que `trayectoria`. Tras el slice, `reparto[i].mes === datos[i].mes`.

---

## 3. Archivos a tocar (solo front)

No crees `/descomposicion`. No toques `shell.tsx`. No toques Python.

| Archivo | Qué |
| :--- | :--- |
| `front/lib/data.ts` | Ampliar `Reparto` + `DriverMes`. **No borres** `pendiente` / `repartir` (el mock demo los usa). |
| `front/lib/api.ts` | `ApiReparto` / `ApiRepartoDriver` y `reparto?` en el punto de history. |
| `front/lib/motor.ts` | `mapReparto` (§5). Quitar `trayectoria.map(repartir…)`. |
| `front/components/prevision.tsx` | Debajo del anillo, 1–3 drivers (§3.1). |
| `front/app/page.tsx` y `front/app/[company_id]/page.tsx` | Ya pasan `reparto={e.reparto}`. Cero cambios si `e.reparto` viene bien. |

### 3.1 Tooltip (v1) — pégalo debajo del anillo

Hoy, ~líneas 322–334 de `prevision.tsx`. El bloque del anillo se queda. Justo después de los dos `%`, si `hRep.drivers?.length`:

```tsx
{hRep.drivers?.length > 0 && (
  <ul className="mt-1.5 space-y-0.5">
    {[...hRep.drivers]
      .sort((a, b) => Math.abs(b.points) - Math.abs(a.points))
      .slice(0, 3)
      .map((d) => (
        <li key={d.field} className="flex items-baseline justify-between gap-4 text-[11px]">
          <span className="text-[var(--color-ink-2)]">
            {d.etiqueta}
            <span className="ml-1 text-[var(--color-ink-4)]">{d.razon}</span>
          </span>
          <span
            className="tnum"
            style={{ color: d.kind === "estructural" ? "#b083e8" : "#dfb631" }}
          >
            {d.points >= 0 ? "+" : "−"}
            {num(Math.abs(d.points))}
          </span>
        </li>
      ))}
  </ul>
)}
```

Reglas:

- Color del **número** por `kind` (morado tendencia / ámbar bache). El texto no va solo color: `etiqueta` + `razon` están a la izquierda.
- Máximo 3, por `|points|` descendente.
- `reason === "cobros_sin_confirmar"`: `razon` ya es «sin confirmar». No añadas un badge extra.
- No pongas un segundo anillo OLS «para comparar».

### 3.2 Tira mes a mes (v1.1, opcional)

El comentario de cabecera de `Prevision` la promete. Si la haces:

- Una celda por mes del `rango` visible, alineada al mismo `x(i)` del SVG.
- Contenido: `Δ` y un mini anillo o dos barritas stacked (morado/ámbar).
- Hover de la tira = mismo `setHover(i)` que las zonas del gráfico.
- Mes plano: «—», sin anillo.

Misma data. Cero cálculo.

### 3.3 Pieza de copy bajo el gráfico

Hoy, si no hay `proyeccion` estructural, el pie habla de inercia. **No** añadas ahí «el 70 % es tendencia» global. El split es **por mes**, en el hover.

Si quieres una frase cuando el último mes tiene drivers:

> ene 25 · +1,7 pts · gastos (se queda)

Una línea. Sin listar palancas.

---

## 4. Copy y visual (cerrado)

### 4.1 Palabras al usuario

| Interno | UI |
| :--- | :--- |
| estructural | tendencia |
| coyuntural | bache |
| `cobros_sin_confirmar` | bache · sin confirmar |
| arrastre | ventana 3 meses |

No uses «estocástico», «OLS», «Shapley», «fotocopia», «φ», «estructural».

### 4.2 Colores (ya en el archivo)

- Tendencia / score: `#b083e8`
- Bache: `#dfb631`
- No introduzcas un tercer color para `family: circulante` en v1.

### 4.3 Arrastre

La ventana de 3 meses del score pierde el mes `t-3` aunque este mes copie al anterior. Eso mueve puntos **sin que el usuario haya hecho nada este mes**.

Copy: «ventana 3 meses». Tooltip largo opcional: «La fórmula aún arrastra el mes que sale de la media a 3 meses».

No lo traduzcas como «siguen bajando los gastos» si no hay driver `expenses`.

### 4.4 Estado `BACHE` vs anillo del mes

El anillo grande de la ficha (`anillo.tsx`) pinta `e.estado`. Puede ser `ESTABLE` con un mes de 90 % bache en el gráfico, o `BACHE` (estado) con un mes plano. **No cambies el color del anillo de estado** porque el split del mes sea coyuntural.

---

## 5. Adaptador (`motor.ts`) — pega esto

Quita el import de `repartir` **solo si deja de usarse** en este archivo. `pendiente` se queda para `inflexionDe`.

Hoy:

```ts
reparto: trayectoria.map((p, k) => repartir(serie, tends, k, p.mes)),
```

Mañana:

```ts
reparto: mapReparto(h?.history, trayectoria),
```

Función completa (este archivo o `data.ts`):

```ts
import type { ApiHistoria, ApiReparto } from "./api";
import type { DriverMes, Punto, Reparto } from "./data";

export function mapReparto(
  history: ApiHistoria["history"] | undefined,
  trayectoria: Punto[],
): Reparto[] | undefined {
  if (!history || history.length !== trayectoria.length) return undefined;
  if (!history.some((p) => p.reparto)) return undefined;

  return history.map((p, i) => {
    const r: ApiReparto | undefined = p.reparto;
    const mes = trayectoria[i].mes;
    if (!r) {
      return { mes, delta: 0, pctTendencia: 0, pctBache: 0, structPts: 0, circPts: 0, drivers: [] };
    }
    return {
      mes,
      delta: r.delta,
      pctTendencia: r.pct_tendencia,
      pctBache: r.pct_bache,
      structPts: r.struct_pts,
      circPts: r.circ_pts,
      drivers: (r.drivers ?? []).map((d): DriverMes => ({
        field: d.field,
        etiqueta: d.etiqueta,
        points: d.points,
        kind: d.kind,
        family: d.family,
        reason: d.reason,
        razon: d.razon,
      })),
    };
  });
}
```

Reglas de `mapReparto`:

1. Sin campo en ningún punto → `undefined` (anillo off).
2. `history.length !== trayectoria.length` → `undefined` (no desplaces meses).
3. `mes` sale de `trayectoria[i].mes` (ya mapeado de `as_of.slice(0, 7)`), no lo recalcules distinto.
4. No llames a `repartir`. No interpoles. No redondees otra vez.

`tends` sigue calculándose para `inflexion` si esa feature sigue viva.

---

## 6. Cómo comprobar que lo has hecho bien

Sin reimplementar el algoritmo. Carga el fixture o espera al API.

1. **DEMO_OPEX, ene 2025.** Anillo 100 % tendencia. Driver `Gastos · se queda · +1,7`. Si ves ~86 % bache, sigues en OLS.
2. **DEMO_COBROS, ene 2025.** Anillo 100 % bache. Driver `Cobros · timing de cobros · +2,7`.
3. **DEMO_COBROS, feb 2025.** Anillo ~31/69. Dos drivers: ventana 3 meses +4,6 y cobros −10,1. No «arregles» el porcentaje.
4. **Mes plano (cualquier DEMO, 2024).** Sin anillo.
5. **History real sin `reparto`.** Gráfico igual que antes, sin anillo. No caigas a `repartir`.
6. **Ventana 12 M.** Hover del mes i: `reparto[i].mes === datos[i].mes`.
7. **Estado TORCIENDOSE.** El anillo de estado de la ficha no se pone ámbar «bache» solo porque el mes tenga `pctBache` alto.

Tests automáticos: `python -m unittest algorithm.test_score_decompose` (no es tu job). Un test de adaptador, si tenéis, que `mapReparto` no importe `repartir` basta.

---

## 7. Qué hace el algoritmo (para no implementarlo, para no romperlo)

Referencia: `attribute_month` en `algorithm/score_decompose.py`.

1. Δ = score(t) − score(t−1) con `calculate_scores` (la `f` de producción).
2. Congela el mes t a los flujos de t−1. La diferencia con t−1 es **arrastre** de ventanas.
3. Descongela campos: expenses → debt_service → refunds → hhi → receipts → funding_gap → quality.
4. Etiqueta: prior (gastos/deuda = tendencia; hueco = bache; cobros = mixto) + override (conservación de dos meses → timing; DSO ≥ 5 días; YoY; pulso en el último mes → sin confirmar).
5. `pctTendencia = |struct| / (|struct| + |circ|)` si `|Δ| ≥ 0,15`.

Causal: **false**. El tooltip no dice «porque recortaste opex»; dice «gastos, se queda».

No uses `φ = 0,8`. Eso es el cono de previsión.

---

## 8. Dependencias con el resto del equipo

```
[Python, este PR]  history_with_reparto  →  JSON
[FastAPI, otro PR] anidar `reparto` en HistoryPoint   ← tú no lo haces
[front, tú]        mapReparto → Prevision pinta
```

Tú puedes mergear tooltip + mapper **antes** de que FastAPI exista: con `reparto` ausente el UI es el de hoy. Lo que no puedes dejar es `repartir()` una vez el JSON exista.

Si quieres pintar el tooltip ya, importa el fixture. No enchufes OLS «mientras tanto».

---

## 9. Checklist de review

- [ ] Cero `pendiente` / `repartir` en el camino `cargarEmpresa` → `Prevision.reparto`.
- [ ] `reparto[i].mes === trayectoria[i].mes` (tras el slice de 6/12/24).
- [ ] Mes plano: sin anillo.
- [ ] Drivers: máximo 3, color por `kind` + texto `etiqueta`/`razon`.
- [ ] `razon` del JSON, no copy improvisada.
- [ ] «Sin confirmar» visible si `reason === cobros_sin_confirmar` (`razon` ya lo trae).
- [ ] Anillo de **estado** de la ficha no usa `pctBache`.
- [ ] Sin página `/descomposicion`.
- [ ] Sin portar `score_engine` / `score_decompose` a TS.
- [ ] Copy: tendencia / bache, no estructural / coyuntural.
- [ ] History sin `reparto` → anillo off, gráfico intacto.

---

## 10. Números de research (por si te discuten el anillo)

Ventana: mes del shock + 2 (estación en meses 18–20). Acierto = `pctTendencia ≥ 50` coincide con la etiqueta del DGP.

| Caso | Etiqueta | OLS acc. | Factor acc. | Factor % tendencia medio |
| :--- | :--- | ---: | ---: | ---: |
| Recorte opex | estructural | 0 % | 100 % | 100 |
| Cobrar antes | coyuntural | 100 % | 100 % | 16 |
| Bache de cobros | coyuntural | 100 % | 100 % | 21 |
| Caída exponencial | estructural | 0 % | 67 % | 67 |
| Seno anual | coyuntural | 67 % | 100 % | 0 |
| DPO un mes | coyuntural | 100 % | 100 % | 19 |
| Shock de tipo | estructural | 0 % | 100 % | 100 |
| Control (plano) | neutro | — | — | anillo off |

El OLS es un detector de **picos**. El producto necesita distinguir **picos de cambios de nivel**. Por eso se cambia el método, no el dibujo.

Umbrales (`YOY_DEADBAND = 0,06`, `DSO_TIMING_DAYS = 5`, `DEADBAND = 0,15`) no se tunan en el front.
