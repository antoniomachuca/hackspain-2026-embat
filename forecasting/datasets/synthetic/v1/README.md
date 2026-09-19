# Dataset sintético congelado v1

**Versionado en Git:** 19 casos × 36 empresas × 36 meses = 24.624 observaciones.
Paneles mensuales compatibles con `algorythm.score_engine.calculate_scores`; no son transacciones
reales ni cifras de clientes de Embat. Escala y covarianzas vienen de grupos de entrenamiento del
reto; shocks y perfiles son hipótesis. Fuentes y límites: [metodología](../../../METHODOLOGY.md).

Por caso:

- `<caso>.npz`: variables bancarias `(empresas, meses)`.
- `<caso>_erp.npz`: ERP simulado; `<caso>_control.npz`: control emparejado sin shock.
- `<caso>.json`: empresas, fechas, semilla y momento del cambio.
- `<caso>_oracle.npz`: caja para evaluar anticipación; **nunca usar como feature**.

`MANIFEST.json` fija los hashes y procedencia. No modificar v1 ni entrenar con él para después
presentarlo como evaluación independiente. Para probar augmentación, generar otro dataset/semilla
de desarrollo y reservar v1 para diagnóstico (ya es público); una validación final necesita v2.

```python
import numpy as np
from algorythm.score_engine import calculate_scores
bank = dict(np.load('forecasting/datasets/synthetic/v1/compound_crisis.npz'))
score = calculate_scores(bank)
```
