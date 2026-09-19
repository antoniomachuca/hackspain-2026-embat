# Descomposición estructural vs coyuntural

**Rama:** `feat/descomposicion-factores`  
**Algoritmo:** `algorythm/score_decompose.py`  
**Guía para implementar el gráfico (front):** [`guia_front_reparto_bache_tendencia.md`](guia_front_reparto_bache_tendencia.md)

Esta nota es el research. La guía de front es el contrato de producto. No reimplementar esto en TypeScript.

---

El producto pide, mes a mes, *qué porcentaje del movimiento es bache y cuál es tendencia*. Hoy eso lo inventa el front con una pendiente OLS sobre el **score**. La idea de esta rama es partir el Δ con la fórmula y los flujos, usando la misma taxonomía salud/circulante que ya usamos en palancas y en el estructural.

## 0. Crítica de la idea (antes de enamorar)

Tienes razón en que el OLS no dice nada real. No tienes razón en que la fórmula, ella sola, distinga opex de “cobré antes”.

`expenses[t]` es un escalar. Recortar nómina y retrasar a un proveedor dejan el mismo número. `receipts[t]` sube igual si vendiste más o si adelantaste el cobro del mes que viene. Eso no es un fallo del motor: es no identificabilidad. Sin stocks (AP, AR, DSO) o sin categorías (nómina vs proveedor), **el tipo causal es un prior**, no una medición.

El ejemplo que pones —“reducir OPEX se queda; cobrar un mes antes no”— es una afirmación de **intervención**. En observación, el mes 1 de un recorte de opex y el mes 1 de un DPO puntual son el mismo gasto más bajo. La persistencia no es un capricho estocástico: es la estrategia de identificación cuando solo tienes el flujo. Tirarla del todo es pretender que el dato trae una etiqueta que no trae.

Lo que sí se puede hacer, y es estrictamente mejor que el OLS, es:

1. Atribuir el Δscore a drivers pasando contrafactuales por `calculate_scores` (la `f` congelada).
2. Etiquetar cada driver con un prior de dominio (opex/deuda = estructural; hueco de caja = coyuntural; cobros = mixto).
3. Dejar que **el dato overridee el prior** cuando hay firma contable: dos meses que conservan la suma (timing), salto de DSO, YoY de calendario.
4. Donde no hay firma, decir “sin confirmar”, no “70 % tendencia”.

El 30/70 de un mes sigue siendo un resumen. El entregable honesto es la lista de puntos por driver.

## 1. Qué hay hoy (y por qué está vacío)

`front/lib/data.ts` → `pendiente` + `repartir`:

- pendiente OLS a 6 meses **del score**
- si la pendiente y el Δ coinciden en signo, `pctTendencia = min(|pendiente|, |Δ|) / |Δ|`
- el resto es bache

Eso es una propiedad de la curva, no de la cuenta. Dos causas distintas con la misma senda de score salen iguales. Un salto de nivel (el recorte de opex) es, el mes del salto, casi todo residuo: la pendiente de 6 meses aún no se ha enterado. Justo el caso que querías pillar.

El estado `BACHE` de `classify_states` es **otra pregunta**: persistencia 3 meses sobre momentum. No responde “de este Δ, cuánto es qué”. No lo toques.

El estructural v2 (`φ=0.8` hacia la media a 12) también es un suavizado, pero de **inputs**. Tampoco sabe si el gasto es opex o DPO. En el mes del salto solo se traga 1/3 del nivel nuevo (la ventana de 3 meses). Por eso “fotocopiar el 3m y pasar por `f`” no basta.

## 2. Los tres approaches

| Método | Qué hace | Qué usa |
| :--- | :--- | :--- |
| `ols_score` | pendiente del score, como el front | solo `S_t` |
| `fotocopia_3m` | run-rate a 3m vs observado, ambos por `f` | flujos, no taxonomía |
| `factor_formula` | contrafactual secuencial por campo + prior salud/circulante + overrides | `f` + taxonomía + DSO/YoY/conservación de suma |

Código: `algorythm/score_decompose.py`. Tests: `algorythm/test_score_decompose.py`.

Overrides del prior:

- **Timing:** `(x_t + x_{t+1}) / 2 ≈ x_{t-1}` → cobros o pagos que se desplazan un mes. Necesita `t+1`.
- **DSO:** `|ΔDSO| ≥ 5 días` → la caída de cobros es AR, no volumen.
- **Estación:** YoY de nivel y de tendencia, y solo si el mes **se movió** (una serie plana no es estación).
- **Mes vivo de cobros** sin `t+1` y pulso > 25 % del run-rate → coyuntural sin confirmar.
- **Gastos sin `t+1`:** se quedan en opex. Ese es el sesgo que pediste.

## 3. Qué gana y qué pierde cada uno

Siete DGP etiquetados (el proceso generador es la etiqueta, no el score). Ventana: mes del shock y los dos siguientes; estación en 18–20, cuando el YoY ya existe.

Accuracy = fracción de meses con |Δ| ≥ 0,15 en los que `pctTendencia ≥ 50` coincide con la etiqueta.

| Caso | Etiqueta | OLS | Fotocopia | Factor |
| :--- | :--- | ---: | ---: | ---: |
| Recorte opex que se queda | estructural | 0 % | 67 % | **100 %** |
| Cobrar este mes lo del siguiente | coyuntural | 100 % | 100 % | **100 %** |
| Bache de cobros que vuelve | coyuntural | 100 % | 100 % | **100 %** |
| Caída exponencial de cobros | estructural | 0 % | 67 % | 67 % |
| Seno anual | coyuntural | 67 % | 0 % | **100 %** |
| Pagar proveedores un mes tarde | coyuntural | 100 % | 100 % | **100 %** |
| Shock de tipo (deuda se queda) | estructural | 0 % | 67 % | **100 %** |
| **Media** | | **52 %** | **71 %** | **95 %** |

Lectura:

- El OLS **acierta los pulsos** y **falla los cambios de nivel**. Es el detector de bache que ya teníamos, disfrazado de porcentaje. Inútil para el ejemplo del opex.
- La fotocopia mejora el nivel a partir del mes 2 (cuando el 3m se ha comido el salto) y **confunde la estación con tendencia**: el run-rate estacional *es* una tendencia local.
- El factor acierta el opex el día 1 y la estación. Falla el **primer mes** de una caída suave (~4 %): cabe en el deadband YoY de 6 %. El mes 3 ya lo llama volumen. Ese agujero es real; no lo tapes.

El DPO sin mes siguiente sigue saliendo opex. Si quieres “cobrar antes es coyuntural desde el minuto 0” **y** “bajar opex es estructural desde el minuto 0”, el precio es clasificar mal el DPO vivo. Sin AP no hay almuerzo gratis.

## 4. El formato 30/70 miente un poco

En el recorte de opex, el mes 1 es `expenses +1,71` (estructural). Los meses 2 y 3 el Δ sigue siendo grande, pero el driver ya no es el gasto nuevo: es el **arrastre** de la ventana de 3 meses, que pierde el mes caro. Eso es la fórmula, no un segundo recorte. Un 100 % tendencia es correcto; un “el opex sigue cayendo” sería falso.

En cobrar antes, el mes 1 es `receipts +2,69` coyuntural. El mes 2 mezcla arrastre estructural (la ventana suelta el mes normal) con el agujero de cobros. El 30/70 aplasta eso. Mejor:

```
feb · +2,7 pts · cobros +2,7 (adelanto, se revierte)
mar · −5,5 pts · cobros −10,1 (agujero) · arrastre +4,6 (ventana)
```

## 5. Qué no hacer

- No sustituir `classify_states` / `BACHE` / persistencia 3 por este split. El monitor contesta “¿hay giro?”. Esto contesta “¿de qué está hecho este mes?”.
- No usar `φ=0,8` aquí. Esa reversión dice “ya se le pasará”. Aquí opex no se le pasa.
- No pintar esto como causal. Es contrafactual de panel, igual que `/simulate`.
- No exigir un porcentaje único en v1. El back debería servir `drivers[]`.
- No reabrir umbrales del monitor para que este split quede bonito.

## 6. Si esto sale del laboratorio

El cálculo y el JSON ya están: `history_with_reparto` / `factor_to_reparto` en `algorythm/score_decompose.py`. Fixture de contrato: `research/fixtures/reparto_demo.json`. Guía de front: [`guia_front_reparto_bache_tendencia.md`](guia_front_reparto_bache_tendencia.md).

Este PR no toca FastAPI a propósito. Quien tenga `companies.py`, el gancho es anidar el dict en cada `HistoryPoint`:

```python
from algorythm.score_decompose import factor_to_reparto, attribute_month, empty_reparto
# por mes t>0: HistoryPoint(..., reparto=factor_to_reparto(attribute_month(bank, t, ...)))
# mes 0: empty_reparto()
```

Shape congelado (snake_case): `{ delta, pct_tendencia, pct_bache, struct_pts, circ_pts, drivers: [{ field, etiqueta, points, kind, family, reason, razon }] }`.

El front deja de usar `repartir()` de `data.ts`. No reimplementa `f` en TypeScript.

Cuando haya vintage de AP, el prior de gastos se puede caer: `Δexpenses` compensado por `ΔAP` es DPO, no opex. El mes vivo de cobros se queda en `cobros_sin_confirmar` hasta que exista `t+1` o un DSO.

El OLS del front se puede tirar; la persistencia del monitor no.
