# Medición de episodios · corte 2026-09-01

1286 empresas, 479 con al menos un episodio, 837 episodios.

Anticipación = cambio material − detección (meses). Negativa = el cambio material se confirmó antes del aviso.
Se cuentan también los avisos no confirmados y pendientes; no solo los aciertos.

| Dirección | Episodios | Confirmados | No confirmados | Pendientes | Anticipación mediana | Aviso antes | Mismo mes | Aviso tardío |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| deterioro | 373 | 229 | 124 | 20 | -1.0 | 10% | 19% | 72% |
| mejora | 464 | 280 | 143 | 41 | -1.0 | 13% | 17% | 70% |

## Detalle

### deterioro

- Histograma de anticipación (n=229): {-1: 164, 0: 43, 1: 15, 2: 5, 3: 1, 4: 1}
- Criterio del cambio material: {'delta_10': 212, 'banda_70': 15, 'banda_40': 2}
- Señales en la detección: {'liquidez': 353, 'cobros': 137, 'crecimiento': 165, 'deuda': 27, 'fragilidad': 29}
- Episodios con escalada: 4 · duración mediana detección→cierre: 2.0 meses · cierre: {'estabilizacion': 309, 'sin_evaluacion': 5}

### mejora

- Histograma de anticipación (n=280): {-1: 196, 0: 47, 1: 27, 2: 9, 3: 1}
- Criterio del cambio material: {'delta_10': 243, 'banda_40': 10, 'banda_70': 27}
- Señales en la detección: {'liquidez': 437, 'cobros': 157, 'crecimiento': 250, 'fragilidad': 34, 'deuda': 22}
- Episodios con escalada: 0 · duración mediana detección→cierre: 2.0 meses · cierre: {'estabilizacion': 359, 'sin_evaluacion': 9}

## Lectura

La mayoría de los cambios materiales se confirman en el mes anterior al aviso o el mismo mes. Es esperable por construcción:
el monitor exige 3 meses de momentum y el cambio material 2 meses consecutivos desde el inicio estimado, y ambos leen la misma
`base_health`. La anticipación mínima posible con este criterio es −1. Este criterio mide la **consistencia** del aviso con un cambio
de tamaño material, no cuánto se adelanta a un evento externo. Para medir anticipación real hace falta un evento independiente:
la caja-oráculo de los escenarios sintéticos o la perspectiva a 6 meses (punto hueco), pendientes de la siguiente entrega.
