# Modelos predictivos · estado y colaboración

**Todo el laboratorio está aquí.** Target: score bancario futuro a **1, 3 y 6 meses**, con escenarios
P10 pesimista / P50 central-conservador / P90 optimista y explicación aditiva. La demo está en `/prevision`.

## Qué tenemos y quién va ganando

Probados: persistencia, media reciente, tendencia amortiguada, estacionalidad, Ridge y boosting
con/sin contexto externo, random forest, boosting por cuantiles y **ExtraTrees** (ejemplo de contribución independiente).
Segunda tanda (v2): Ridge con alpha por GroupKFold, lineal Huber, lineal por mediana, reversión parcial
a la media, boosting monótono, ensemble robusto y Huber con intervalos conformales (CQR).

| Horizonte | Candidato según la regla común | MAE validación por grupo ↓ | MAE test por grupo* |
|---|---|---:|---:|
| 1 mes | Lineal Huber | 4,17 | 6,76 |
| 3 meses | Media reciente | 7,20 | 14,90 |
| 6 meses | Lineal por mediana | 9,58 | 8,09 |

**Ranking actualizado: [benchmarks/LEADERBOARD.md](benchmarks/LEADERBOARD.md)** (24 ejecuciones × 3 horizontes;
las v2 corrigen la agregación de la CV interna y las v1 se conservan para el registro).
La tabla incluye ahora **Δ MAE frente al candidato baseline con IC 95%** de un bootstrap emparejado por
grupo: la regla del 2% no cambia, pero el intervalo dice si la diferencia se distingue del ruido.
Los IC no ajustan por selección múltiple ni por la exploración previa: son **evidencia favorable en
validación exploratoria**, no confirmación. A 1M los lineales robustos muestran evidencia favorable
frente a Ridge; a 3M nada supera a la media reciente; a 6M los IC incluyen 0 y la cobertura es pobre,
sin ganador claro. Candidato del ranking ≠ modelo promovido: la demo no cambia. ExtraTrees no se ha
evaluado en test. El contexto BCE/Eurostat no mejora consistentemente; faltan sectores
y muchos países. A 6M solo hay 59 muestras de test. *El test v1 ya es público: diagnóstico, no selección.*

También hay **19 escenarios de estrés, 24.624 observaciones**: baches, estacionalidad, mejora, caída,
cobros tardíos, cliente perdido, costes, deuda, FX, expansión, contagio y datos ausentes.
Calibrados con el dataset del reto e inspirados en casos públicos de Embat; **no son cifras reales de clientes**.

## Cómo aportar un modelo sin pisarnos

Desde la raíz del repo, con Python y `pip install -r requirements.txt`. El dataset original va en `data/`
(se reparte aparte); los datos sintéticos y el snapshot externo **sí están subidos al repo**.

1. Crea tu rama y copia `forecasting/experiments/extra_trees.py` a `forecasting/experiments/tu_nombre.py`.
   Cambia `MODEL_INFO` y `make_model(horizon, seed)`. El ejemplo envuelve un regresor sklearn;
   permite probar otros estimadores sin tocar el evaluador. Declara parámetros, enfoque y nuevas dependencias.
2. Entrena y registra una ejecución propia:

   ```bash
   python -m forecasting.experiment \
     --factory forecasting.experiments.tu_nombre:make_model \
     --author tu_nombre --run-name enfoque-v1
   python -m forecasting.registry
   ```

3. Mira la tabla y tu JSON en `forecasting/benchmarks/runs/tu_nombre__enfoque-v1.json`.
   Cada ejecución incluye métricas, estrés, tiempos, hashes, semilla y código del experimento.
   **Otro intento = otro `--run-name`**: no sobrescribir ni editar métricas a mano; conserva también resultados malos.
4. Abre PR con tu módulo, dependencias si hacen falta y JSON. No cambies protocolo/datos/baseline ni
   edites la tabla a mano. El mantenedor regenera `LEADERBOARD.md` al integrar los JSON; así no necesitamos
   modificar un registro central para añadir un modelo. La demo no se actualiza automáticamente.

Contrato para enfoques propios: `fit(train)`, `calibrate(calibration)`, `predict(samples)` → matriz
`[P10,P50,P90]`, `direction_probabilities(samples)` → `[baja,estable,sube]`, `explain(sample)`.
Ver [adapter](adapters.py) y [ejemplo ejecutable](experiments/extra_trees.py). El runner oculta `y` durante
predicción, valida cuantiles/probabilidades y comprueba que la explicación reconstruye el resultado.
Puedes transformar las features dentro del modelo, ajustando cualquier transformación **solo en train**.

## Cómo elegimos

Mismos datos, target, grupos, cortes temporales, horizontes y métricas para todos. El registro excluye
ejecuciones incompatibles por sus hashes. Entrenamiento/calibración/validación/test separan grupos completos.
**Menor MAE medio por grupo en validación**; dentro del **2%**, menor complejidad declarada y revisada en PR.
Antes de promover: revisar explicación, recall de mejora y caída, falsas alarmas, cobertura nominal del 80%,
estrés y latencia. No basta con bajar el error ocultando peores intervalos o perdiendo explicabilidad.

El runner no consulta test por defecto. `--final-test` añade el diagnóstico v1, sin afectar al ranking.
Para confirmar la próxima mejora de generalización necesitamos **un nuevo holdout congelado**, porque
el v1 ya se ha visto. Si cambias target, particiones o datos, acuerda un protocolo nuevo y reejecuta los baselines.

## Dónde está cada cosa

- [`datasets/synthetic/v1/`](datasets/synthetic/v1/): paneles banco/ERP, controles, metadatos y hashes; **congelados y versionados**. Oráculos solo para evaluar.
- [`datasets/external/`](datasets/external/): contexto externo con procedencia y fecha de disponibilidad.
- [`benchmarks/`](benchmarks/): baseline, resultados individuales y tabla común; [`protocol.json`](protocol.json) fija las reglas.
- `experiments/`: aportaciones independientes. `artifacts/`: exportaciones locales de la demo, ignoradas por Git.
- [Metodología completa](METHODOLOGY.md): fuentes, supuestos, métricas y límites. API/front permanecen en sus carpetas de aplicación.

Reproducir la demo: `python -m forecasting.benchmark --dataset data`.
Pruebas: `python -m pytest forecasting/tests backend/test_forecasts.py -q`.
