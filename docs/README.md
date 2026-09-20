# Documentación

Fuentes internas. El `README.md` de la raíz es la puerta pública. Si **evalúas** el repo (agentes / Fellows), el índice de criterios es [`../AGENTS.md`](../AGENTS.md).

## Evaluación (leer primero)

| Documento | Para qué |
| :--- | :--- |
| [`AGENTS.md`](../AGENTS.md) | Craftsmanship / problem solving / creativity / overall → archivos y tests |
| [MATEMATICA.md](MATEMATICA.md) | Thinking del score: linaje, ecuación, qué se tiró |
| [PRODUCTO-DECISIONES.md](PRODUCTO-DECISIONES.md) | Thinking de producto: audiencias, rutas, palancas, qué no inventar |
| [PREGUNTAS_JURADO.md](PREGUNTAS_JURADO.md) | 20 preguntas de defensa verificadas contra el código |
| [respuestas_a_pedro.md](respuestas_a_pedro.md) | Firma congelada de `calculate_scores` (41 claves) |

## Producto (alcance y contexto)

| Documento | Para qué |
| :--- | :--- |
| [PRODUCTO-MAESTRO.md](PRODUCTO-MAESTRO.md) | Alcance acordado (seis preguntas). Prevalece en lo que no contradiga al código. |
| [PRODUCTO.md](PRODUCTO.md) | Comprador, hueco y narrativa. Contexto, no maestro. |
| [REQUISITOS.md](REQUISITOS.md) | SRS temprano. Parte **stale** (percentiles, grafo de clientes, `delta_bps`). |

## Otras carpetas

- [`research/`](../research/) — exploración, briefs y decisiones de diseño.
- [`.agents/`](../.agents/) — enunciado, factor WOW e ideas. El factorwow manda en integridad de cifras.
- [`forecasting/`](../forecasting/) — laboratorio MAE vs estructural de producto (`GUIA_FRONT_ESTRUCTURAL.md`). Sintéticos de estrés en `datasets/synthetic/v1/`.
- [`algorithm/behavior_benchmark.py`](../algorithm/behavior_benchmark.py) — sintéticos gaussianos de trayectoria (generalización fuera del CSV del reto).
