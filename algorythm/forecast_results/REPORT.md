# Benchmark de previsión y estrés

Ejecución `2fcec1dde80ffb0b`. Target: score bancario futuro; no probabilidad de impago.

Selección por MAE medio entre grupos de validación; el test se consulta después.

| Horizonte | Modelo seleccionado | N test / grupos | MAE test | MAE por grupo (IC 95%) | Cobertura 80% | Recall mejora / deterioro |
|---|---|---:|---:|---|---:|---|
| 1 meses | ridge | 446 / 21 | 7.37 | 6.78 (5.19–8.21) | 79.8% | 56.0% / 42.4% |
| 3 meses | trailing_mean | 265 / 17 | 13.09 | 14.90 (10.29–19.39) | 72.5% | 41.8% / 45.8% |
| 6 meses | ridge | 59 / 15 | 8.23 | 9.03 (6.36–12.05) | 79.7% | 78.3% / 54.2% |

## Comparación completa (test)

| Meses | Modelo | MAE grupo | MAE | Dirección equilibrada | Cobertura | Anchura |
|---|---|---:|---:|---:|---:|---:|
| 1 | persistence | 7.72 | 7.92 | 33.3% | 77.6% | 22.40 |
| 1 | trailing_mean | 9.67 | 10.31 | 39.3% | 72.9% | 28.77 |
| 1 | damped_trend | 8.78 | 9.12 | 32.5% | 74.2% | 23.28 |
| 1 | seasonal | 8.23 | 8.94 | 44.7% | 75.1% | 22.40 |
| 1 | ridge | 6.78 | 7.37 | 55.2% | 79.8% | 23.30 |
| 1 | ridge_context | 13.05 | 14.97 | 39.3% | 40.8% | 22.68 |
| 1 | random_forest | 6.82 | 7.32 | 54.2% | 77.6% | 22.42 |
| 1 | boosting | 6.84 | 7.35 | 47.9% | 77.6% | 20.46 |
| 1 | boosting_context | 6.90 | 7.40 | 47.2% | 76.7% | 20.09 |
| 1 | quantile_boosting | 6.84 | 7.35 | 47.9% | 80.7% | 22.05 |
| 3 | persistence | 16.32 | 14.68 | 33.3% | 72.8% | 41.58 |
| 3 | trailing_mean | 14.90 | 13.09 | 50.7% | 72.5% | 38.96 |
| 3 | damped_trend | 21.15 | 18.57 | 25.7% | 73.2% | 50.35 |
| 3 | seasonal | 14.44 | 11.90 | 51.5% | 81.5% | 41.62 |
| 3 | ridge | 10.74 | 10.65 | 55.8% | 76.2% | 29.24 |
| 3 | ridge_context | 10.86 | 10.95 | 48.9% | 63.4% | 29.27 |
| 3 | random_forest | 10.53 | 9.62 | 64.3% | 73.6% | 29.61 |
| 3 | boosting | 10.65 | 9.89 | 63.0% | 73.6% | 30.96 |
| 3 | boosting_context | 10.65 | 9.89 | 63.0% | 73.6% | 30.96 |
| 3 | quantile_boosting | 10.65 | 9.89 | 63.0% | 75.5% | 27.01 |
| 6 | persistence | 12.83 | 12.69 | 33.3% | 69.5% | 31.58 |
| 6 | trailing_mean | 13.91 | 12.17 | 45.0% | 61.0% | 25.97 |
| 6 | damped_trend | 20.21 | 17.28 | 36.4% | 72.9% | 42.99 |
| 6 | seasonal | 8.38 | 8.66 | 52.1% | 88.1% | 28.40 |
| 6 | ridge | 9.03 | 8.23 | 60.8% | 79.7% | 25.44 |
| 6 | ridge_context | 9.03 | 8.23 | 60.8% | 79.7% | 25.44 |
| 6 | random_forest | 10.35 | 9.61 | 60.7% | 81.4% | 28.02 |
| 6 | boosting | 10.67 | 9.80 | 52.4% | 69.5% | 24.76 |
| 6 | boosting_context | 10.67 | 9.80 | 52.4% | 69.5% | 24.76 |
| 6 | quantile_boosting | 10.67 | 9.80 | 52.4% | 74.6% | 27.45 |

## Estrés del score y monitor

| Caso | Delta emparejado mediano | Detección ≤6m | Alertas adversas/año |
|---|---:|---|---:|
| control | 0.00 | — | 0.33 |
| seasonality | -1.86 | — | 0.72 |
| temporary_dip | -0.00 | — | 0.53 |
| deterioration | -7.51 | 38.9% | 0.78 |
| improvement | 6.99 | 27.8% | 0.48 |
| late_collections | -2.47 | 55.6% | 0.60 |
| rate_shock | -3.59 | 41.7% | 0.45 |
| fx_shock | -5.46 | 61.1% | 0.63 |
| expansion_cash_squeeze | -8.51 | 72.2% | 0.82 |
| customer_loss | -15.13 | 80.6% | 0.81 |
| refinancing | 0.24 | 36.1% | 0.48 |
| group_contagion | -16.02 | 63.9% | 0.76 |
| refund_wave | -23.71 | 86.1% | 0.74 |
| data_outage | -0.04 | — | 0.30 |
| cold_start | -0.02 | — | 0.38 |
| compound_crisis | -28.09 | 88.9% | 0.71 |
| zero_activity | -11.56 | — | 0.51 |
| debt_balloon | 0.04 | 41.7% | 0.53 |
| recovery | 16.88 | 88.9% | 0.44 |

La tasa de alertas es falsa alarma solo en controles estables/estacionales; en shocks mezcla alertas verdaderas y falsas.

## Contexto y límites

Modo externo: `strict_point_in_time`; cobertura de indicadores: 20.0%.
La ablación con contexto queda sin evidencia cuando no hay observaciones externas disponibles a fecha de corte.

- Organizer data are synthetic and have already been explored by the team
- Only 24 months; six-month forecast has few independent temporal origins
- Bank classifications and company metadata lack historical vintages
- Overlapping forecast windows; uncertainty bootstrapped by business group
- ERP snapshot and terminal cash balances excluded from historical forecast features
- Synthetic shocks are hypotheses, never actual customer financials or ground truth for the challenge

Los tres escenarios son cuantiles marginales por horizonte; las líneas que los unen no representan trayectorias conjuntas ni una garantía del 80%.
La mediana se etiqueta central/conservador: no incorpora una política adicional de aversión al riesgo.
Ver benchmark.json para particiones, métricas de todos los modelos bajo estrés, semillas y hashes.
