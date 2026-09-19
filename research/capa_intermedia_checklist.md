# Checklist de implementación · capa intermedia

**Rama:** `feat/capa-intermedia-mejoras`  
**Ley:** `capa_intermedia_decisiones.md` §10–§11 + `capa_intermedia_mejoras.md` §12–§13.  
**No reabrir decisiones.** Esto es cola de trabajo, no research.

```
HECHO     bank_inputs + get_company_bank_slice + mutadores básicos + POST /api/simulate
FALTA     objetos/empresa, gates, D2C/D3C, confirming honesto, rankings, GET /palancas, Telegram
```

## Dependencias (qué es paralelo)

```
            [catálogo congelado]
                    |
        +-----------+-----------+
        |           |           |
     OBJETOS      COSTES     MUTADORES (fix confirming/factoring)
        |           |           |
        +-----+-----+-----+-----+
              |
           GATES (necesita objetos)
              |
           SIMULATE v2 (gates + costes + mutadores)
              |
           BÚSQUEDA / DOS RANKINGS
              |
        +-----+-----+
        |           |
      HTTP API    TELEGRAM
```

| Fase | Piezas | Relación |
| :---: | :--- | :--- |
| **0** | Catálogo ids/familias/mutex/acuerdo | Contrato compartido. Bloquea a todos. |
| **1** | Objetos · Costes · Mutadores honestos | **Paralelo** (archivos distintos). |
| **2** | Gates | Tras objetos. |
| **3** | `simulate_levers` v2 | Tras 1+2. |
| **4** | Búsqueda + rankings | Tras 3. |
| **5** | `GET /palancas` + `POST /simulate` | Tras 4. Paralelo con Telegram si el dominio ya expone funciones. |
| **6** | Bot Telegram | Tras 4 (mismas funciones, otra UI). |

## Done por pieza

### P0 Catálogo
- [x] Un único `LEVER_CATALOG` con familia, mutator, gates, `excluido_con`, tipos de acuerdo
- [x] Alias `reducir_dso` → `adelantar_cobros`
- [x] Mutex: cobros↔dto; M3 entre sí; DPO↔confirming↔pronto-pago AP

### P1 Objetos (`levers_objects.py`)
- [x] Snapshot por empresa **sin** `load_bank_panel` ni scan de invoices por request
- [x] AR pending, AP pending, opex/H/refunds mes 23, LOC/factoring/confirming/leasing/inversión/checking
- [x] Selección AR por días 7/15/30 (+ overdue; `clientes[]` opcional)

### P2 Costes (`levers_cost.py`)
- [x] Suelo `tipo_ref 3% anual × días/365`
- [x] Anclas dto 0.5/2/3 %; DPO perder dto 2 % o recargo 1–2 %
- [x] `tipo_acuerdo` obligatorio en cobros y DPO (D2C/D3C)

### P3 Mutadores
- [x] Cobros: pending → receipts/gross/gap; haircut solo en `descuento_pronto_pago`
- [x] Confirming: **no** tocar expenses; euros no-score; 422 si E↓
- [x] Línea/inversión: euros + `delta_score=null`; amortizar puede acoplar ↓H
- [x] Factoring/concentración: visibles; ΔS null si no hay mutación honesta
- [x] `impacto_anual_eur = 12 × Δmensual` en opex/refi (D5C)

### P4 Gates
- [x] `is_prior` → todo inaplicable
- [x] Predicado de objeto por id; `motivo_rechazo` nunca vacío si false
- [x] Refi no-op si D≥0.49 o H=0
- [x] Simulate de inaplicable → 422, no ΔS fingido

### P5 Búsqueda
- [x] Rejilla cobros 7/15/30; opex 5/10; refi 20/40; dto anclas
- [x] Presupuesto N≤60; top-10 por ranking
- [x] `sugerencias[]` sort ΔS (solo salud)
- [x] `opciones_circulante[]` sort caja neta, `delta_score=null`
- [x] 1 recomendado = mejor ratio impacto/coste

### P6 HTTP
- [x] `GET /api/palancas?company_id=` catálogo ancho
- [x] `POST /api/simulate` contrato PRODUCTO (`modo`, warnings, `eur_año`, model_version)
- [x] `GET /api/simulate/rankings`
- [x] `/whatif` heurístico **no se borra** (bot legacy)

### P7 Telegram
- [x] `/palancas COMP_XXXX`
- [x] `/simulate COMP_XXXX` → rankings + botones
- [x] Callbacks palancas / rankings / aplicar recomendada
- [x] `/whatif` se mantiene; teclado alerta añade Palancas
- [x] Tests de routing sin red

## SOLID
- Strategy por facade; mutadores inyectables
- Objetos / gates / costes / search / HTTP / bot = módulos distintos
- El bot y FastAPI **no** duplican fórmulas: llaman al dominio
