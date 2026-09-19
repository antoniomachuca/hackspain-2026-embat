# Previsión estructural v1

Ejecución `pedro__structural-v1`. Target: score bancario futuro; no probabilidad de impago.

Se proyectan cobros, pagos y servicio de deuda (reembolsos a ratio constante) y se aplica `calculate_scores`. El modelo no aprende la fórmula. Central = pendiente amortiguada del run-rate a 3 meses (ventana 6, clip ±20%). Bandas = volatilidad MoM de la empresa, clip 5–25%, con signo a favor/en contra del score.

Selección por MAE medio entre grupos de validación; el test es diagnóstico.

| Horizonte | N val / grupos | MAE val por grupo (IC 95%) | Dirección val | Cobertura 80% | N test / grupos | MAE test por grupo |
|---|---:|---|---:|---:|---:|---|
| 1 meses | 372 / 22 | 3.74 (2.98–4.66) | 61.2% | 56.2% | 446 / 21 | 5.99 (4.59–7.40) |
| 3 meses | 216 / 19 | 8.43 (6.09–10.60) | 41.6% | 63.4% | 265 / 17 | 15.91 (11.07–21.76) |
| 6 meses | 46 / 13 | 11.97 (5.46–19.02) | 50.4% | 39.1% | 59 / 15 | 15.30 (9.82–21.91) |

## Contra el laboratorio del PR #9 (validación; criterio de selección)

Mismas particiones que el baseline `db399a14836c57de` y `equipo__extra-trees-v1`. El run no entra en el tablero automático: el hash de evaluación ahora incluye `country.py`. Los recuentos de muestras coinciden.

| Meses | Modelo | MAE grupo ↓ | Dirección | Cobertura | Anchura | Recall mejora / deterioro |
|---|---|---:|---:|---:|---:|---|
| 1 | **structural_v1** | **3.74** | **61.2%** | 56.2% | 7.36 | 66.0% / 46.6% |
| 1 | boosting (mejor MAE PR #9) | 4.47 | 51.7% | 80.1% | — | — |
| 1 | ridge (candidato PR #9) | 4.55 | 51.9% | 78.0% | 23.30 | 32.0% / 56.3% |
| 1 | extra_trees_v1 | 4.61 | 49.8% | 78.8% | — | — |
| 1 | persistence | 4.82 | 33.3% | 80.1% | — | 0% / 0% |
| 3 | trailing_mean (candidato PR #9) | 7.20 | 56.1% | 82.4% | 39.02 | 38.9% / 63.8% |
| 3 | extra_trees_v1 | 7.35 | 63.4% | 69.0% | — | — |
| 3 | ridge | 7.50 | 55.7% | 69.9% | 29.24 | 70.8% / 65.0% |
| 3 | structural_v1 | 8.43 | 41.6% | 63.4% | 23.45 | 44.4% / 10.0% |
| 3 | persistence | 8.53 | 33.3% | 78.7% | — | 0% / 0% |
| 6 | extra_trees_v1 | 9.77 | 57.5% | 63.0% | — | — |
| 6 | ridge (candidato PR #9) | 9.87 | 57.5% | 63.0% | 25.44 | 66.7% / 69.6% |
| 6 | structural_v1 | 11.97 | 50.4% | 39.1% | 11.49 | 83.3% / 4.3% |
| 6 | persistence | 11.83 | 33.3% | 65.2% | — | 0% / 0% |

## Test diagnóstico (no selecciona)

| Meses | structural MAE grupo | Ridge MAE grupo | Candidato PR #9 MAE grupo |
|---|---:|---:|---:|
| 1 | 5.99 | 6.78 | 6.78 (ridge) |
| 3 | 15.91 | 10.74 | 14.90 (trailing_mean) |
| 6 | 15.30 | 9.03 | 9.03 (ridge) |

## Qué significa

A 1 mes, proyectar la cuenta y puntuar gana a Ridge y a boosting en MAE y en dirección. Caza mejoras (66% vs 32% de Ridge) a costa de un poco de recall de deterioro (47% vs 56%). Las bandas son caminos de la empresa, no cuantiles de residual: cubren el 56% en vez del 80% y miden 7 puntos frente a 23.

A 3 y 6 meses el camino amortiguado se queda corto. Casi no anticipa caídas (recall de deterioro 10% y 4%). Ridge, que modela el Δscore, sí. El MAE empeora; en test a 3 meses queda peor incluso que la media reciente que eligió el PR #9.

`zero_activity` no tiene muestras elegibles (calidad proyectada no salva un panel vacío). El resto de shocks sintéticos se evalúan; no seleccionan modelo.

## Límites

- Organizer data are synthetic and have already been explored by the team
- Only 24 months; six-month forecast has few independent temporal origins
- Bank classifications and company metadata lack historical vintages
- Overlapping forecast windows; uncertainty bootstrapped by business group
- ERP snapshot and terminal cash balances excluded from historical forecast features
- Synthetic shocks are hypotheses, never actual customer financials or ground truth for the challenge
- Las tres curvas son caminos de cuenta, no un intervalo de cobertura 80%
- Este run no usa macro: el tipo BCE aún no entra en `debt_service`

No se ha modificado `forecasting/benchmarks/baseline/` ni `forecasting/benchmarks/LEADERBOARD.md`.
Ver `forecasting/benchmarks/runs/pedro__structural-v1.json` para particiones, estrés, semillas y hashes.
