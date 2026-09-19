# Previsión estructural v2

Ejecución `pedro__structural-v2`. Target: score bancario futuro; no probabilidad de impago.

Cambios respecto a v1: el camino central revierte el run-rate a 3 meses hacia la media a 12 de la empresa (φ=0,8); cada mes proyectado se escala por el mismo mes del año pasado si ya está observado (regla del `seasonal` del PR #9, sobre flujos); las bandas crecen con √h.

Selección por MAE medio entre grupos de validación; el test es diagnóstico.

| Horizonte | N val / grupos | MAE val por grupo (IC 95%) | Dirección val | Cobertura 80% | N test / grupos | MAE test por grupo |
|---|---:|---|---:|---:|---:|---|
| 1 meses | 372 / 22 | 4.21 (3.26–5.31) | 63.4% | 56.5% | 446 / 21 | 6.06 (4.67–7.37) |
| 3 meses | 216 / 19 | 8.16 (5.92–10.66) | 48.9% | 75.9% | 265 / 17 | 13.73 (8.92–19.13) |
| 6 meses | 46 / 13 | 11.08 (5.75–16.35) | 52.9% | 67.4% | 59 / 15 | 9.74 (5.61–14.09) |

## Contra v1 y el laboratorio (validación)

| Meses | Modelo | MAE grupo ↓ | Dirección | Cobertura | Anchura | Recall mejora / deterioro |
|---|---|---:|---:|---:|---:|---|
| 1 | structural_v1 | 3.74 | 61.2% | 56.2% | 7.36 | 66.0% / 46.6% |
| 1 | **structural_v2** | 4.21 | **63.4%** | 56.5% | 7.69 | 60.2% / **60.2%** |
| 1 | boosting | 4.47 | 51.7% | 80.1% | — | — |
| 1 | ridge (candidato PR #9) | 4.55 | 51.9% | 78.0% | 23.30 | 32.0% / 56.3% |
| 3 | trailing_mean (candidato PR #9) | 7.20 | 56.1% | 82.4% | 39.02 | 38.9% / 63.8% |
| 3 | ridge | 7.50 | 55.7% | 69.9% | 29.24 | 70.8% / 65.0% |
| 3 | structural_v2 | 8.16 | 48.9% | 75.9% | 30.95 | 47.2% / **46.3%** |
| 3 | structural_v1 | 8.43 | 41.6% | 63.4% | 23.45 | 44.4% / 10.0% |
| 6 | ridge (candidato PR #9) | 9.87 | 57.5% | 63.0% | 25.44 | 66.7% / 69.6% |
| 6 | structural_v2 | 11.08 | 52.9% | 67.4% | 38.40 | 75.0% / **56.5%** |
| 6 | structural_v1 | 11.97 | 50.4% | 39.1% | 11.49 | 83.3% / 4.3% |

## Test diagnóstico (no selecciona)

| Meses | v2 MAE grupo | v1 MAE grupo | Ridge MAE grupo | Candidato PR #9 |
|---|---:|---:|---:|---|
| 1 | 6.06 | 5.99 | 6.78 | 6.78 (ridge) |
| 3 | 13.73 | 15.91 | 10.74 | 14.90 (trailing_mean) |
| 6 | 9.74 | 15.30 | 9.03 | 9.03 (ridge) |

## Qué cambió

La reversión a la media arregla el fallo de v1: el P50 ya puede decir “va a peor”. El recall de deterioro pasa de 10%→46% a 3 meses y de 4%→57% a 6 meses. El abanico √h sube la cobertura a 3 y 6 meses (63%→76%, 39%→67%) y abre las bandas.

A 1 mes el MAE sube un poco (3,74→4,21) porque φ=0,8 ya tira un 20% hacia la media larga; sigue por debajo de Ridge y boosting. En test a 6 meses v2 (9,74) se acerca a Ridge (9,03); v1 se iba a 15,3.

No se ha modificado `forecasting/benchmarks/baseline/` ni `forecasting/benchmarks/LEADERBOARD.md`.
Ver `forecasting/benchmarks/runs/pedro__structural-v2.json`.
