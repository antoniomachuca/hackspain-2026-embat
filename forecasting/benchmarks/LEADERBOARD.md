# Comparación común de modelos

Generado con `python -m forecasting.registry`. Se elige por **validación**, nunca por test.
Contrato comparable: `e96c8187e179a838`. Baseline: `db399a14836c57de`.

Dentro del 2% del mejor MAE por grupo gana la menor complejidad declarada (revisada en PR).
La tabla propone candidatos: no cambia automáticamente el modelo de la demo.
Δ positiva = mejora frente al candidato baseline; IC del bootstrap emparejado por grupo.
La regla del 2% no cambia: el IC es contexto para juzgar si la diferencia se distingue del ruido.

## 1 meses · candidato: huber_linear

| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Δ MAE vs ridge [IC 95%] | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |
|---|---|---:|---:|---:|---:|---:|
| [huber_linear · carlos__huber_linear-v1](runs/carlos__huber_linear-v1.json) **← candidato** | carlos | 4.17 | +0.38 [+0.10, +0.74] ✓ | 54.9% | 80.9% | 6.76 |
| [huber_linear · carlos__huber_linear-v2](runs/carlos__huber_linear-v2.json) | carlos | 4.17 | +0.38 [+0.10, +0.74] ✓ | 54.9% | 80.9% | — |
| [huber_cqr · carlos__huber_cqr-v1](runs/carlos__huber_cqr-v1.json) | carlos | 4.17 | +0.38 [+0.10, +0.74] ✓ | 54.9% | 78.8% | 6.76 |
| [huber_cqr · carlos__huber_cqr-v2](runs/carlos__huber_cqr-v2.json) | carlos | 4.17 | +0.38 [+0.10, +0.74] ✓ | 54.9% | 78.8% | — |
| [median_linear · carlos__median_linear-v1](runs/carlos__median_linear-v1.json) | carlos | 4.17 | +0.38 [+0.03, +0.78] ✓ | 53.6% | 82.0% | 6.74 |
| [median_linear · carlos__median_linear-v2](runs/carlos__median_linear-v2.json) | carlos | 4.17 | +0.38 [+0.03, +0.78] ✓ | 53.6% | 82.0% | — |
| [robust_ensemble · carlos__robust_ensemble-v1](runs/carlos__robust_ensemble-v1.json) | carlos | 4.27 | +0.28 [-0.06, +0.69] | 50.4% | 82.0% | 7.16 |
| [robust_ensemble · carlos__robust_ensemble-v2](runs/carlos__robust_ensemble-v2.json) | carlos | 4.27 | +0.28 [-0.06, +0.69] | 50.4% | 82.0% | — |
| [ridge_groupcv · carlos__ridge_groupcv-v1](runs/carlos__ridge_groupcv-v1.json) | carlos | 4.34 | +0.21 [+0.06, +0.39] ✓ | 56.5% | 81.5% | 6.66 |
| [ridge_groupcv · carlos__ridge_groupcv-v2](runs/carlos__ridge_groupcv-v2.json) | carlos | 4.34 | +0.21 [+0.06, +0.39] ✓ | 56.5% | 81.5% | — |
| [boosting · db399a14836c57de](baseline/benchmark.json) | baseline | 4.47 | — | 51.7% | 80.1% | 6.84 |
| [quantile_boosting · db399a14836c57de](baseline/benchmark.json) | baseline | 4.47 | — | 51.7% | 81.7% | 6.84 |
| [boosting_context · db399a14836c57de](baseline/benchmark.json) | baseline | 4.53 | — | 49.7% | 79.8% | 6.90 |
| [ridge · db399a14836c57de](baseline/benchmark.json) | baseline | 4.55 | — | 51.9% | 78.0% | 6.78 |
| [extra_trees_v1 · equipo__extra-trees-v1](runs/equipo__extra-trees-v1.json) | equipo | 4.61 | — | 49.8% | 78.8% | — |
| [monotone_boosting · carlos__monotone_boosting-v1](runs/carlos__monotone_boosting-v1.json) | carlos | 4.64 | -0.09 [-0.77, +0.62] | 46.7% | 81.5% | 7.27 |
| [random_forest · db399a14836c57de](baseline/benchmark.json) | baseline | 4.64 | — | 52.5% | 78.8% | 6.82 |
| [partial_mean_reversion · carlos__partial_mean_reversion-v1](runs/carlos__partial_mean_reversion-v1.json) | carlos | 4.68 | -0.13 [-0.87, +0.63] | 40.1% | 82.8% | 7.68 |
| [partial_mean_reversion · carlos__partial_mean_reversion-v2](runs/carlos__partial_mean_reversion-v2.json) | carlos | 4.68 | -0.13 [-0.87, +0.63] | 40.1% | 82.8% | — |
| [persistence · db399a14836c57de](baseline/benchmark.json) | baseline | 4.82 | — | 33.3% | 80.1% | 7.72 |
| [trailing_mean · db399a14836c57de](baseline/benchmark.json) | baseline | 5.52 | — | 44.8% | 83.1% | 9.67 |
| [damped_trend · db399a14836c57de](baseline/benchmark.json) | baseline | 5.55 | — | 36.4% | 80.1% | 8.78 |
| [seasonal · db399a14836c57de](baseline/benchmark.json) | baseline | 6.86 | — | 46.8% | 69.1% | 8.23 |
| [ridge_context · db399a14836c57de](baseline/benchmark.json) | baseline | 12.04 | — | 46.7% | 46.2% | 13.05 |

## 3 meses · candidato: trailing_mean

| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Δ MAE vs trailing_mean [IC 95%] | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |
|---|---|---:|---:|---:|---:|---:|
| [robust_ensemble · carlos__robust_ensemble-v1](runs/carlos__robust_ensemble-v1.json) | carlos | 7.18 | +0.03 [-1.59, +1.57] | 51.4% | 75.5% | 11.81 |
| [robust_ensemble · carlos__robust_ensemble-v2](runs/carlos__robust_ensemble-v2.json) | carlos | 7.18 | +0.03 [-1.59, +1.57] | 51.4% | 75.5% | — |
| [trailing_mean · db399a14836c57de](baseline/benchmark.json) **← candidato** | baseline | 7.20 | — | 56.1% | 82.4% | 14.90 |
| [partial_mean_reversion · carlos__partial_mean_reversion-v1](runs/carlos__partial_mean_reversion-v1.json) | carlos | 7.20 | +0.00 [+0.00, +0.00] | 56.1% | 82.4% | 14.90 |
| [partial_mean_reversion · carlos__partial_mean_reversion-v2](runs/carlos__partial_mean_reversion-v2.json) | carlos | 7.20 | +0.00 [+0.00, +0.00] | 56.1% | 82.4% | — |
| [extra_trees_v1 · equipo__extra-trees-v1](runs/equipo__extra-trees-v1.json) | equipo | 7.35 | — | 63.4% | 69.0% | — |
| [ridge · db399a14836c57de](baseline/benchmark.json) | baseline | 7.50 | — | 55.7% | 69.9% | 10.74 |
| [random_forest · db399a14836c57de](baseline/benchmark.json) | baseline | 7.65 | — | 63.1% | 67.6% | 10.53 |
| [monotone_boosting · carlos__monotone_boosting-v1](runs/carlos__monotone_boosting-v1.json) | carlos | 7.65 | -0.45 [-1.64, +0.74] | 64.3% | 68.5% | 10.46 |
| [boosting · db399a14836c57de](baseline/benchmark.json) | baseline | 7.78 | — | 60.7% | 65.7% | 10.65 |
| [boosting_context · db399a14836c57de](baseline/benchmark.json) | baseline | 7.78 | — | 60.7% | 65.7% | 10.65 |
| [quantile_boosting · db399a14836c57de](baseline/benchmark.json) | baseline | 7.78 | — | 60.7% | 76.4% | 10.65 |
| [median_linear · carlos__median_linear-v1](runs/carlos__median_linear-v1.json) | carlos | 8.09 | -0.88 [-3.25, +1.38] | 55.9% | 70.8% | 10.95 |
| [median_linear · carlos__median_linear-v2](runs/carlos__median_linear-v2.json) | carlos | 8.09 | -0.88 [-3.25, +1.38] | 55.9% | 70.8% | — |
| [ridge_groupcv · carlos__ridge_groupcv-v1](runs/carlos__ridge_groupcv-v1.json) | carlos | 8.45 | -1.25 [-3.62, +1.17] | 47.0% | 68.5% | 11.99 |
| [ridge_groupcv · carlos__ridge_groupcv-v2](runs/carlos__ridge_groupcv-v2.json) | carlos | 8.45 | -1.25 [-3.62, +1.17] | 47.0% | 68.5% | — |
| [persistence · db399a14836c57de](baseline/benchmark.json) | baseline | 8.53 | — | 33.3% | 78.7% | 16.32 |
| [seasonal · db399a14836c57de](baseline/benchmark.json) | baseline | 8.92 | — | 54.2% | 75.5% | 14.44 |
| [damped_trend · db399a14836c57de](baseline/benchmark.json) | baseline | 9.29 | — | 26.0% | 78.2% | 21.15 |
| [huber_linear · carlos__huber_linear-v1](runs/carlos__huber_linear-v1.json) | carlos | 9.34 | -2.13 [-4.80, +0.54] | 42.3% | 69.9% | 13.04 |
| [huber_linear · carlos__huber_linear-v2](runs/carlos__huber_linear-v2.json) | carlos | 9.34 | -2.13 [-4.80, +0.54] | 42.3% | 69.9% | — |
| [huber_cqr · carlos__huber_cqr-v1](runs/carlos__huber_cqr-v1.json) | carlos | 9.34 | -2.13 [-4.80, +0.54] | 42.3% | 76.9% | 13.04 |
| [huber_cqr · carlos__huber_cqr-v2](runs/carlos__huber_cqr-v2.json) | carlos | 9.34 | -2.13 [-4.80, +0.54] | 42.3% | 76.9% | — |
| [ridge_context · db399a14836c57de](baseline/benchmark.json) | baseline | 9.72 | — | 50.5% | 56.9% | 10.86 |

## 6 meses · candidato: median_linear

| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Δ MAE vs ridge [IC 95%] | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |
|---|---|---:|---:|---:|---:|---:|
| [monotone_boosting · carlos__monotone_boosting-v1](runs/carlos__monotone_boosting-v1.json) | carlos | 9.56 | +0.30 [-1.80, +2.03] | 53.3% | 58.7% | 10.33 |
| [median_linear · carlos__median_linear-v1](runs/carlos__median_linear-v1.json) **← candidato** | carlos | 9.58 | +0.29 [-1.07, +1.67] | 68.2% | 58.7% | 8.09 |
| [median_linear · carlos__median_linear-v2](runs/carlos__median_linear-v2.json) | carlos | 9.58 | +0.29 [-1.07, +1.67] | 68.2% | 58.7% | — |
| [extra_trees_v1 · equipo__extra-trees-v1](runs/equipo__extra-trees-v1.json) | equipo | 9.77 | — | 57.5% | 63.0% | — |
| [ridge · db399a14836c57de](baseline/benchmark.json) | baseline | 9.87 | — | 57.5% | 63.0% | 9.03 |
| [ridge_context · db399a14836c57de](baseline/benchmark.json) | baseline | 9.87 | — | 57.5% | 63.0% | 9.03 |
| [ridge_groupcv · carlos__ridge_groupcv-v1](runs/carlos__ridge_groupcv-v1.json) | carlos | 9.91 | -0.05 [-1.73, +1.47] | 55.4% | 65.2% | 9.70 |
| [ridge_groupcv · carlos__ridge_groupcv-v2](runs/carlos__ridge_groupcv-v2.json) | carlos | 9.91 | -0.05 [-1.73, +1.47] | 55.4% | 65.2% | — |
| [random_forest · db399a14836c57de](baseline/benchmark.json) | baseline | 9.98 | — | 53.2% | 65.2% | 10.35 |
| [huber_linear · carlos__huber_linear-v1](runs/carlos__huber_linear-v1.json) | carlos | 10.14 | -0.27 [-2.22, +1.45] | 55.5% | 65.2% | 10.07 |
| [huber_linear · carlos__huber_linear-v2](runs/carlos__huber_linear-v2.json) | carlos | 10.14 | -0.27 [-2.22, +1.45] | 55.5% | 65.2% | — |
| [huber_cqr · carlos__huber_cqr-v1](runs/carlos__huber_cqr-v1.json) | carlos | 10.14 | -0.27 [-2.22, +1.45] | 55.5% | 69.6% | 10.07 |
| [huber_cqr · carlos__huber_cqr-v2](runs/carlos__huber_cqr-v2.json) | carlos | 10.14 | -0.27 [-2.22, +1.45] | 55.5% | 69.6% | — |
| [boosting · db399a14836c57de](baseline/benchmark.json) | baseline | 10.14 | — | 57.4% | 60.9% | 10.67 |
| [boosting_context · db399a14836c57de](baseline/benchmark.json) | baseline | 10.14 | — | 57.4% | 60.9% | 10.67 |
| [quantile_boosting · db399a14836c57de](baseline/benchmark.json) | baseline | 10.14 | — | 57.4% | 60.9% | 10.67 |
| [robust_ensemble · carlos__robust_ensemble-v1](runs/carlos__robust_ensemble-v1.json) | carlos | 10.40 | -0.54 [-2.56, +1.30] | 62.7% | 65.2% | 10.95 |
| [robust_ensemble · carlos__robust_ensemble-v2](runs/carlos__robust_ensemble-v2.json) | carlos | 10.40 | -0.54 [-2.56, +1.30] | 62.7% | 65.2% | — |
| [trailing_mean · db399a14836c57de](baseline/benchmark.json) | baseline | 11.15 | — | 59.6% | 56.5% | 13.91 |
| [partial_mean_reversion · carlos__partial_mean_reversion-v1](runs/carlos__partial_mean_reversion-v1.json) | carlos | 11.15 | -1.29 [-4.03, +1.24] | 59.6% | 56.5% | 13.91 |
| [partial_mean_reversion · carlos__partial_mean_reversion-v2](runs/carlos__partial_mean_reversion-v2.json) | carlos | 11.15 | -1.29 [-4.03, +1.24] | 59.6% | 56.5% | — |
| [seasonal · db399a14836c57de](baseline/benchmark.json) | baseline | 11.44 | — | 53.9% | 60.9% | 8.38 |
| [persistence · db399a14836c57de](baseline/benchmark.json) | baseline | 11.83 | — | 33.3% | 65.2% | 12.83 |
| [damped_trend · db399a14836c57de](baseline/benchmark.json) | baseline | 15.48 | — | 31.1% | 60.9% | 20.21 |

*Test v1 ya publicado: diagnóstico, no criterio de selección. Para una nueva afirmación de generalización necesitamos otro holdout congelado.
Antes de promover: revisar explicación, recalls en ambas direcciones, cobertura, estrés y coste de inferencia.
