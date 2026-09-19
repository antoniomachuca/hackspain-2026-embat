# Episodios de cambio: "cuándo se vio venir"

Responde a *quién empieza a torcerse / mejorando*, *por qué ha cambiado* y *cuándo se vio venir*,
en ambas direcciones. Complementa `research/dos_puntos_trayectoria.md` (punto hueco) y
`research/momento_en_que_se_tuercen.md` (tres relojes). Decisiones cerradas el 2026-09-19.

## Tres momentos, dos marcas

| Momento | Qué significa | Reloj | En el gráfico |
|---|---|---|---|
| **Perspectiva adversa** (punto hueco) | "Si seguimos así, la proyección a 6 meses sale mal". Hipótesis condicionada, no un hecho. | t_anticipación | Punto hueco, a la izquierda de la detección, si pertenece al mismo episodio |
| **Detección** (marca principal) | "Ya observamos una tendencia persistente". Es el aviso del monitor: entrada a `TORCIENDOSE`/`DETERIORO` o `MEJORANDO`/`RECUPERACION`, con datos solo hasta ese mes. | t_alerta | Línea vertical principal: "Aquí detectamos señales de deterioro/mejora" |
| **Cambio material** | "El cambio alcanzó el tamaño y la duración definidos". Sirve para evaluar el aviso. | t_evento (criterio propio) | Solo texto y tooltip. **Nunca una tercera marca.** |

El nombre visible del aviso es siempre **detección**. La anticipación indica siempre entre qué dos
momentos se calcula: "detectado N meses antes del cambio material" o "la perspectiva se vio N meses
antes de la detección".

## Definición del episodio

- **Abre** al entrar en un estado direccional desde uno no direccional (`directional_event_matrix`).
  `TORCIENDOSE → DETERIORO` no abre otro: es una **escalada** dentro del mismo episodio.
- **Cierra** cuando el estado deja de ser direccional durante `neutral_persistence_months` (2) meses
  —fecha = el segundo mes— o al entrar en la dirección contraria (que abre un episodio nuevo).
  `BACHE` **no** incrementa el contador de cierre (el pulso no cierra el episodio).
- **Inicio estimado** = detección − `persistence_months` + 1. Dato retrospectivo, etiquetado así.
- **Referencia** = `base_health` en detección − `persistence_months` (mes anterior a la racha). Se fija
  al abrir y no se mueve. Se usa `base_health` (liquidez + cobros + deuda, sin momentum) y no el
  score porque el score ya lleva la señal anticipatoria: evaluarlo contra sí mismo sería circular.
- **Cambio material**: primer mes, desde el inicio estimado hasta el cierre, en que `base_health`
  en la dirección del episodio (a) cruza una banda (40/70) respecto a la referencia **o** (b) se aleja
  ≥ 10 puntos de la referencia, manteniéndose **2 meses consecutivos**. La fecha es la del segundo mes;
  no se retrocede. Puede ocurrir **antes** de la detección (aviso tardío): no se fuerza que quede después.
- **Anticipación material** (`meses_anticipacion`) = cambio material − detección, en meses; JSON
  de medición, **no** copy de ficha. El N visible es `perspectiva.meses_antes_deteccion` (hueco → rojo).
- **Estado de confirmación**: `confirmado` · `pendiente` (episodio activo sin cambio material) ·
  `no_confirmado` (episodio cerrado sin cambio material; se muestra como "No se confirmó", nunca como pendiente).
- Umbrales (10 pts, 2 meses, bandas 40/70) son parámetros iniciales, declarados en la salida.

## Explicación en el momento del aviso

Se explica lo que se veía **en la detección**, con datos hasta entonces: deltas a 3 meses de los bloques
`liquidity/collections/debt/growth/fragility_points` (sin momentum ni clipping), valor antes → valor en
detección. **Respeta la dirección**: en deterioros solo contribuciones negativas relevantes, en mejoras
solo positivas (top 2). Solo señales y valores que existen en los datos. Familia `salud` por defecto;
`circulante` únicamente cuando la perspectiva de circulante dispara en el corte vivo. Copy cerrado por plantilla.

## Perspectiva adversa (punto hueco)

Receta de `research/dos_puntos_trayectoria.md` §5: fotocopia del banco hasta `t`, persistir el régimen
de 3 meses (R3/E3/H3) seis meses, `calculate_scores` congelado. Dispara si `Ŝ ≤ S_t − 3`, `Ŝ < 60` y
`Ŝ ≤ Ŝ_base − 3` (base = régimen de 12 meses). Solo deterioro en v1; circulante (AP) solo en el corte
vivo, histórico = solo salud. Nunca `banco[t+1:]` real.

- Una perspectiva es una **racha** de meses consecutivos elegibles con perspectiva adversa.
- Se asocia a un episodio de deterioro **solo si la racha sigue viva cuando empieza la racha de momentum**
  (último mes adverso ≥ detección − `persistence_months`). Una perspectiva antigua ya resuelta no se
  asocia a un deterioro posterior. El punto hueco es el primer mes de esa racha.
- Una perspectiva **caduca** cuando vuelve a `NINGUNA` durante 2 meses sin que haya detección; queda
  registrada como `perspectiva_sin_aviso` (falsa señal de perspectiva) para la medición, no en el gráfico.
- Se presenta como proyección condicionada ("si esto sigue, a 6 meses la nota cae"), nunca como PD.

## Contrato para front

```json
"episodios": [{
  "direccion": "deterioro|mejora", "estado": "activo|cerrado", "cierre": "2026-05-01"|null, "motivo_cierre": "estabilizacion|cambio_direccion|sin_evaluacion"|null,
  "deteccion": "2025-12-01", "estado_deteccion": "TORCIENDOSE", "score_deteccion": 76.1,
  "escaladas": [{"as_of": "2026-02-01", "estado": "DETERIORO"}],
  "inicio_estimado": "2025-10-01",
  "referencia_base_health": 71.4, "cambio_material": "2026-02-01"|null, "criterio": "delta_10|banda_70|banda_40"|null,
  "estado_confirmacion": "confirmado|pendiente|no_confirmado", "meses_anticipacion": 2|null,
  "perspectiva": {"as_of": "2025-08-01", "outlook": "SALUD_ADVERSA", "score_observado": 79.0, "score_proyectado": 55.2, "meses_antes_deteccion": 4}|null,
  "senales": [{"senal": "cobros", "antes": 14.2, "en_deteccion": 8.1, "delta_puntos": -6.1}],
  "familia": "salud|circulante", "texto": "…"
}],
"episodio_destacado": 0|null,
"perspectivas_sin_aviso": [{"inicio": "2025-03-01", "fin": "2025-05-01"}],
"trayectoria_marcas": {"deteccion": {...}|null, "camino": {...}|null, "texto": "…"},
"parametros": {"persistence_months": 3, "neutral_persistence_months": 2, "material_delta": 10, "material_persistence": 2, "bands": [40, 70]}
```

El backend calcula este contrato al vuelo en el detalle de empresa, sobre el recorte de
`score_panels.npz` + `bank_inputs.npz`. El front destaca uno: el activo o, si no hay, el último
cerrado, con su estado visible. "Ver histórico" permite elegir otro. Sin episodios → sin marcas.
El feed de alertas no cambia (`lead_months` sigue `null` en vivo).

## Invariantes que se prueban

- Detecciones, perspectivas y señales calculadas hasta `T` no cambian al añadir meses posteriores
  (solo pueden añadirse cierres y cambios materiales, que son retrospectivos por definición).
- La perspectiva usa exclusivamente historia hasta `t`.
- Sin estados nuevos en `NEGATIVE_STATES`; el monitor no se recalibra.

## Medición

Sobre las 1.286 empresas: episodios por dirección; confirmados / no confirmados / pendientes;
distribución de `meses_anticipacion` incluyendo ≤ 0 (detección tardía); perspectivas asociadas frente a
`perspectivas_sin_aviso`. Sobre los 19 escenarios sintéticos, además, detección y perspectiva frente al
mes real del shock y frente a la caja-oráculo ≤ 0. Se reportan también los fallos, no solo los aciertos.

## Resultados de la primera entrega (corte 2026-09-01)

`python -m algorythm.episodes_report` → `engine_results/episodes_report.md`. 1.286 empresas, 479 con
episodio, 837 episodios (373 deterioro / 464 mejora). Confirmados 509, no confirmados 267, pendientes 61.
Anticipación mediana **−1 mes** en ambas direcciones: ~70% de los cambios materiales se confirman el mes
anterior al aviso, ~18% el mismo mes, ~10–13% después (hasta 4 meses).

Lectura honesta: es esperable por construcción (monitor = 3 meses de momentum; cambio material = 2 meses
desde el inicio estimado; ambos leen `base_health`), y la anticipación mínima posible es −1. Este criterio
mide que el aviso es **consistente** con un cambio de tamaño material, no cuánto se adelanta a un evento
externo. La anticipación real exige un evento independiente: caja-oráculo sintética o el punto hueco.

## Plan (orden de prioridad)

1. ✔ `score_episodes.py`: episodios completos (ambas direcciones) + tests.
2. ✔ API calcula episodios al vuelo sobre `score_panels.npz` + `bank_inputs.npz`. Sin `episodes.json`.
3. ✔ Front: marca de detección, explicación, histórico; retirada la anticipación inventada.
4. ✔ `score_project.py` + `score_outlook.py` + asociación al episodio. Lotes por origen.
   Circulante (AP) solo en el corte vivo. Copy de familia en el gráfico; cambio material solo en JSON.
5. Pendiente: medición frente a caja-oráculo en los 19 escenarios sintéticos.
