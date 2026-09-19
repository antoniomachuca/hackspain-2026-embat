# Comparación común de modelos

Generado con `python -m forecasting.registry`. Se elige por **validación**, nunca por test.
Contrato comparable: `ddaff17380bc72b3`. Baseline: `53880df7cd3ee3f2`.

Dentro del 2% del mejor MAE por grupo gana la menor complejidad declarada (revisada en PR).
La tabla propone candidatos: no cambia automáticamente el modelo de la demo.

## 1 meses · candidato: ridge

| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |
|---|---|---:|---:|---:|---:|
| [boosting · 53880df7cd3ee3f2](benchmark.json) | baseline | 4.47 | 51.7% | 80.1% | 6.84 |
| [quantile_boosting · 53880df7cd3ee3f2](benchmark.json) | baseline | 4.47 | 51.7% | 81.7% | 6.84 |
| [ridge · 53880df7cd3ee3f2](benchmark.json) **← candidato** | baseline | 4.55 | 51.9% | 78.0% | 6.78 |
| [boosting_context · 53880df7cd3ee3f2](benchmark.json) | baseline | 4.57 | 51.5% | 78.0% | 6.84 |
| [random_forest · 53880df7cd3ee3f2](benchmark.json) | baseline | 4.64 | 52.5% | 78.8% | 6.82 |
| [persistence · 53880df7cd3ee3f2](benchmark.json) | baseline | 4.82 | 33.3% | 80.1% | 7.72 |
| [trailing_mean · 53880df7cd3ee3f2](benchmark.json) | baseline | 5.52 | 44.8% | 83.1% | 9.67 |
| [damped_trend · 53880df7cd3ee3f2](benchmark.json) | baseline | 5.55 | 36.4% | 80.1% | 8.78 |
| [seasonal · 53880df7cd3ee3f2](benchmark.json) | baseline | 6.86 | 46.8% | 69.1% | 8.23 |
| [ridge_context · 53880df7cd3ee3f2](benchmark.json) | baseline | 12.52 | 46.8% | 47.0% | 13.46 |
| [ridge_national_v1 · pedro__national-macro-v1](../runs/pedro__national-macro-v1.json) | pedro | 12.52 | 46.8% | 47.0% | — |

## 3 meses · candidato: trailing_mean

| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |
|---|---|---:|---:|---:|---:|
| [trailing_mean · 53880df7cd3ee3f2](benchmark.json) **← candidato** | baseline | 7.20 | 56.1% | 82.4% | 14.90 |
| [ridge · 53880df7cd3ee3f2](benchmark.json) | baseline | 7.50 | 55.7% | 69.9% | 10.74 |
| [random_forest · 53880df7cd3ee3f2](benchmark.json) | baseline | 7.65 | 63.1% | 67.6% | 10.53 |
| [boosting · 53880df7cd3ee3f2](benchmark.json) | baseline | 7.78 | 60.7% | 65.7% | 10.65 |
| [boosting_context · 53880df7cd3ee3f2](benchmark.json) | baseline | 7.78 | 60.7% | 65.7% | 10.65 |
| [quantile_boosting · 53880df7cd3ee3f2](benchmark.json) | baseline | 7.78 | 60.7% | 76.4% | 10.65 |
| [persistence · 53880df7cd3ee3f2](benchmark.json) | baseline | 8.53 | 33.3% | 78.7% | 16.32 |
| [seasonal · 53880df7cd3ee3f2](benchmark.json) | baseline | 8.92 | 54.2% | 75.5% | 14.44 |
| [damped_trend · 53880df7cd3ee3f2](benchmark.json) | baseline | 9.29 | 26.0% | 78.2% | 21.15 |
| [ridge_context · 53880df7cd3ee3f2](benchmark.json) | baseline | 10.02 | 49.9% | 55.1% | 11.01 |
| [ridge_national_v1 · pedro__national-macro-v1](../runs/pedro__national-macro-v1.json) | pedro | 10.02 | 49.9% | 55.1% | — |

## 6 meses · candidato: ridge

| Modelo / ejecución | Autor | MAE validación por grupo ↓ | Dirección equilibrada ↑ | Cobertura 80% | MAE test por grupo* |
|---|---|---:|---:|---:|---:|
| [ridge · 53880df7cd3ee3f2](benchmark.json) **← candidato** | baseline | 9.87 | 57.5% | 63.0% | 9.03 |
| [ridge_context · 53880df7cd3ee3f2](benchmark.json) | baseline | 9.90 | 60.3% | 63.0% | 9.08 |
| [ridge_national_v1 · pedro__national-macro-v1](../runs/pedro__national-macro-v1.json) | pedro | 9.90 | 60.3% | 63.0% | — |
| [random_forest · 53880df7cd3ee3f2](benchmark.json) | baseline | 9.98 | 53.2% | 65.2% | 10.35 |
| [boosting · 53880df7cd3ee3f2](benchmark.json) | baseline | 10.14 | 57.4% | 60.9% | 10.67 |
| [boosting_context · 53880df7cd3ee3f2](benchmark.json) | baseline | 10.14 | 57.4% | 60.9% | 10.67 |
| [quantile_boosting · 53880df7cd3ee3f2](benchmark.json) | baseline | 10.14 | 57.4% | 60.9% | 10.67 |
| [trailing_mean · 53880df7cd3ee3f2](benchmark.json) | baseline | 11.15 | 59.6% | 56.5% | 13.91 |
| [seasonal · 53880df7cd3ee3f2](benchmark.json) | baseline | 11.44 | 53.9% | 60.9% | 8.38 |
| [persistence · 53880df7cd3ee3f2](benchmark.json) | baseline | 11.83 | 33.3% | 65.2% | 12.83 |
| [damped_trend · 53880df7cd3ee3f2](benchmark.json) | baseline | 15.48 | 31.1% | 60.9% | 20.21 |

*Test v1 ya publicado: diagnóstico, no criterio de selección. Para una nueva afirmación de generalización necesitamos otro holdout congelado.
Antes de promover: revisar explicación, recalls en ambas direcciones, cobertura, estrés y coste de inferencia.

## Ejecuciones excluidas

- `equipo__extra-trees-v1.json`: protocolo, datos, evaluación o contexto diferentes.
