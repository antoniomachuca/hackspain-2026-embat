# Factor WOW v2 · Estrategia de demostración para **ganar**

> Sustituye a la v1. El objetivo no es que el jurado piense "qué bonito", es que
> **no pueda discutir ninguna cifra** y que en 2:30 vea las tres cosas que se puntúan:
> **si acierta, si llega a tiempo y si vale algo** (enunciado §7, los tres bloques pesan igual).

---

## 0. Veredicto sobre la v1

La v1 acertaba en el diagnóstico (un dashboard pasivo pierde) y en el gancho de la paradoja
del mes 24. Pero tenía cuatro fallos que, ante este jurado concreto —fundadores de Embat e
inversores de K Fund—, cuestan más que cualquier cosa que sume:

| Lo que hacía la v1 | Por qué no gana | Qué hace la v2 |
| :--- | :--- | :--- |
| Cifras inventadas y **contradictorias entre sí** (alerta en mes 18/"6 meses", pero §4 dice mes 19/"3 meses"; 42.000/64.000/14.000 €; +6/+8 pts) | El especialista de datos de Embat pregunta por el método. Un número que no sale del motor o no cuadra con el otro documento es la vía rápida a la pregunta 4 | **Todo número en pantalla lo pone el motor.** Cero constantes en el guion. Ver §9 |
| "**Ejecutar Plan de Acción**" que redacta memorandos bancarios vinculantes | Es teatro de LLM, y `PRODUCTO.md` §1 dice lo contrario: *el agente no opina, simula*. Además es trabajo que no ataca ningún criterio del enunciado | Se degrada a un **borrador trazable** de cierre, opcional, con cada cifra nacida de `/simulate` (§4) |
| Enriquecer por **NIF contra Exa** buscando insolvencias | Imposible **por construcción**: el cruce contraparte↔empresa es 0,0 % y el dataset es sintético, así que no existe huella real que Exa pueda indexar. Demo garantizada de fallar | Exa se reasigna a **contexto sectorial/macro del peer set**, nunca a la ficha de una empresa del dataset (§4) |
| "**Pasaporte de Solvencia Verificado**" con hash criptográfico | `PRODUCTO.md` §4 lo dice: los bancos consumen ECAI/CIRBE/Informa, no sellos. El hash suena a blockchain decorativa | Se reencuadra como **el dossier bancario único, siempre actualizado y con caducidad** (§4) |
| Olvidaba **simetría (dos caras), grupo y anticipación honesta** | Son un obligatorio y dos bonus del enunciado, y son justo donde el motor actual es fuerte | Se convierten en los actos 3, 4 y 7 (§3) |

**La idea central de la v2:** el WOW no está en construir más cosas, está en **proyectar lo
que ya está construido** y no se estaba enseñando.

---

## 1. Las dos formas de morir en una demo (y la regla madre)

1. **Un número fabricado.** Basta una cifra que no salga del motor para que el jurado deje de
   mirar el producto y empiece a buscar el error. Con un miembro del equipo de Embat en la
   sala, la probabilidad de que ocurra es alta.
2. **Un artefacto que huele a GPT.** Un memorando legal impecable pero sin traza al dato se
   lee como "esto lo ha escrito un LLM en 30 segundos", no como "este producto ejecuta".

> **Regla madre, escrita en la pared:** *todo número lo pone el motor, toda afirmación tiene
> una fuente, y lo que enseñamos ya existe y se puede señalar en el código.*

---

## 2. Lo que ya está construido y la v1 no usaba

Esto no hay que inventarlo: está en `algorythm/` y se puede abrir en pantalla si alguien
pregunta. Es la munición del WOW.

| Ya existe | Dónde | Qué habilita en la demo |
| :--- | :--- | :--- |
| **La paradoja del mes 24, resuelta numéricamente**: a niveles casi idénticos (65 vs 68), la trayectoria separa las dos empresas | `algorythm/test_score_engine.py:141` (`test_named_opposite_trajectories_overcome_similar_final_levels`) | Acto 1 sin inventar nada |
| **Descomposición exacta**: `score = Σ contribuciones`, y `Δscore = Σ Δbloques` con error 0, **incluido el recorte en los bordes** (`clipping_points`) | `score_engine.py:241-247`, test `test_score_range_finiteness_and_exact_waterfall` (`test_score_engine.py:19`) | Acto 2: el "por qué" es el propio modelo, no un SHAP |
| **Momentum simétrico y con puerta de persistencia**: sube y baja igual, y un mes suelto no lo activa | `bounded_momentum` (`score_engine.py:103`), tests `:105` y `:111` | Actos 3 y 4: dos caras y *bache ≠ deterioro* |
| **Estado de datos insuficientes**: `is_prior` marca la empresa como "scoring pendiente" en vez de emitir un número falso | `score_engine.py:252`, test `:43` | El 32 % de empresas con <12 meses no rompe la demo (§3, acto 1) |
| **Caja observada vs inferida**: `cash_known` distingue el saldo que se ve del que se supone | `score_engine.py:168-181` | Honestidad de la pata de liquidez en el acto 2 |

Si el jurado pregunta "¿esto es real o un mock?", la respuesta es un `git` abierto en el
proyector y un test que corre en vivo.

---

## 3. Los siete actos WOW

Cada acto está atado a un bloque de evaluación del enunciado §7. No se recita: se **hace**
en pantalla mientras se habla.

### Acto 1 · La paradoja del mes 24 — pantalla partida con interruptor
**Qué se ve.** Northbrook y Velasco, 24 puntos de trayectoria. Un interruptor llamado
**"Modo Bureau"** oculta el histórico y enseña solo el mes 24: Velasco (68) parece más
sólida que Northbrook (65). Al apagarlo y activar **"Modo X-Ray"**, aparecen las dos
trayectorias y el punto exacto en que el monitor marcó el cambio.
**Bloque que puntúa.** Trayectoria + generalización (Bloque 1) y es el gancho.
**Frase.** *"Informa puntúa con un balance de hace 15 meses. Aquí las dos valen lo mismo.
Con el rastro de ayer, una va a más y la otra empezó a torcerse hace meses."*
**Regla de integridad.** **No se dice "Velasco está quebrada"** (dato sintético, RF-B12.6).
Se dice: *"nuestro score y sus drivers divergen, y aquí está el mes en que lo vimos"*.
El interruptor es un componente visual; las dos series salen del mismo motor.

### Acto 2 · El porqué que suma exacto — la cascada
**Qué se ve.** Para la empresa elegida, una cascada que arranca en los bloques base
(liquidez, cobros, deuda), suma momentum y crecimiento, resta fragilidad y **muestra el
recorte como una barra más**, y cierra exactamente en el score. Debajo, la misma cascada del
delta: `Δscore = Σ Δbloques`, y la suma coincide (error 0 por construcción).
**Bloque que puntúa.** Explicación (Bloque 3).
**Frase.** *"No hay caja negra: el score es aditivo y la explicación es el modelo mismo. Por
eso no verá un beeswarm de SHAP — verá la aritmética que mueve el número."*
**Regla de integridad.** Sale de `liquidity_points`, `collections_points`, `debt_points`,
`momentum_points`, `growth_points`, `fragility_points` y `clipping_points`
(`score_engine.py:241-246`). Nada se recalcula en el front.

### Acto 3 · Las dos caras — el mismo motor hacia arriba y hacia abajo
**Qué se ve.** Dos empresas del panel, una que mejora y otra que se deteriora, con las
mismas palancas y el mismo motor. El momentum de la que sube es positivo y el de la que baja
es negativo (test `:105`).
**Bloque que puntúa.** Las dos caras (Bloque 1), que es obligatorio.
**Frase.** *"Un detector de quiebras a secas no vale. La misma señal que premia a la que
mejora castiga a la que se tuerce."*
**Aviso honesto (ver §7).** El término de **crecimiento es unilateral** (`max(x, 0)`) y la
**fragilidad solo resta**; el recorte a 0–100 también puede romper la simetría. La simetría
se enseña sobre **momentum + validación (RF-B13.6)**, y si el CA de simetría no está verde se
dice en el pitch, no se esconde.

### Acto 4 · La anticipación, medida en serio
**Qué se ve.** El número de meses de anticipación **reportado a una tasa de falsas alarmas
fijada**: *"mediana de N meses a 1 alerta por empresa-año en las sanas"*, contra un baseline
tonto (alertar el mismo mes que se ve = 0 meses). Cambio de régimen por CUSUM sobre el
residuo interanual, definido **antes** de mirar resultados.
**Bloque que puntúa.** Anticipación + estabilidad (Bloque 2, bonus) — y es el criterio que el
especialista de datos de Embat va a comprobar.
**Frase.** *"Sin fijar la tasa de falsas alarmas, cualquier lead time se infla. Este es el
nuestro, y se puede reconstruir."*
**Regla de integridad.** Se mide **solo sobre las 373 empresas con 24 meses** (29 %,
`informe_exploracion.md` §1) y se dice. El test del control exige `lead_months >= 3`
(`test_score_engine.py:129`); ojo, ese test importa `algorythm.validate_score`, que **no está
en el árbol** (§7).

### Acto 5 · El what-if en euros — de "sé que estás mal" a "esto es lo que ganas"
**Qué se ve.** Seleccionar una empresa, aplicar palancas del catálogo cerrado
(`reducir_dso(días)` · `ampliar_dpo(días)` · `refinanciar` · `bajar_utilización_línea` ·
`descuento_pronto_pago`…) y ver en milisegundos **score nuevo, delta de score, caja liberada
y puntos básicos**, calculados por **contrafactual real**: se modifica el input y se
**recomputa el pipeline entero**, no se extrapola la derivada local (RF-B8.2).
**Bloque que puntúa.** Producto (Bloque 3) y es el diferenciador central: *Experian Boost
para la tesorería*, que en B2B no existe (`PRODUCTO.md` §3).
**Frase.** *"No le decimos al CFO que reduzca el DSO: le decimos cuántos euros libera y
cuántos puntos gana. El número lo pone el motor, no el agente."*
**Regla de integridad.** **Las dos patas se muestran separadas y etiquetadas** (RF-B9.5):
primero **caja liberada** (aritmética: ΔDSO × facturación diaria) y después **coste de
financiación** (estimación: curva score→tipo, con su dispersión o se retira). Nadie puede
confundir las dos.

### Acto 6 · El dossier bancario en el móvil del jurado — el QR
**Qué se ve.** Un QR grande en pantalla. El jurado escanea y abre en su teléfono el **dossier
financiero de la empresa**: score, trayectoria, drivers del último cambio, posición
percentilada anónima frente al sector y fecha de corte, con link **caducable**.
**Bloque que puntúa.** Producto + artesanía (Bloque 3) y es el cierre tangible.
**Frase.** *"No es un sello de confianza: es el dossier que hoy montáis ocho veces al año
para ocho bancos, una sola vez y siempre actualizado. Aquí Embat monetiza."*
**Regla de integridad.** **Nada de "verificado" ni de hash criptográfico** (§0). La URL es
pública y real; el contenido es **precomputado y determinista** para el caso de demo, y hay
**PDF/captura de respaldo** si falla el wifi (`REQUISITOS.md` B13-contingencia, RNF-7).

### Acto 7 (opcional, si Quirce lo tiene) · La filial que arrastra al grupo
**Qué se ve.** La vista de grupo: consolidado 71, pero la filial portuguesa saca 38 y arrastra
el número. Al hacer clic se ve el desglose por filial.
**Bloque que puntúa.** Comprador (Bloque 3): es la conversación que Embat tiene cada día y la
razón de ser de multi-entidad (`PRODUCTO.md` §4, RF-B6.3).
**Frase.** *"El benchmark contra el peer anónimo de los 250 grupos solo lo puede construir
quien los agrega a todos. Vosotros ya tenéis el dato. Lo que no tenéis es la nota."*
**Regla de integridad.** La eliminación intragrupo es **aproximada** (por categoría
`transfer`, RF-B1.13) y se declara. Si no está implementada a tiempo, **no se improvisa en
vivo**: cae y se queda en el guion escrito.

---

## 4. Los tres componentes de la v1, revisados

### 4.1 "Ejecutar Plan de Acción" → **Borrador trazable** (opcional, cierre)
Se mantiene como **detalle de cierre de 10 segundos**, nunca como acto central. El agente
**no redacta libremente**: elige y parametriza una palanca del catálogo, y el borrador
(p. ej. la propuesta de descuento por pronto pago) se ensambla con los términos financieros
que devuelve `/simulate`. Se etiqueta en pantalla como **"borrador generado desde las cifras
del motor"**. Nada de "vinculante", nada de memorandos legales: eso activa exactamente la
duda que queremos evitar (§1).

### 4.2 "Pasaporte de Solvencia Verificado" → **Dossier bancario único con caducidad**
Mismo QR, mismo golpe visual, sin las afirmaciones que `PRODUCTO.md` ya prohíbe. Se quita el
"hash criptográfico de integridad" y se sustituye por **trazabilidad real**: fecha de corte,
de qué ficheros del dataset sale cada bloque y versión de configuración (RNF-8). El código
hash, si se quiere conservar, se presenta como **sello de reproducibilidad** (hash de
`score_engine.py` + `score_data.py`, que `calc_score.py` ya calcula en
`source_hashes()`), no como certificación de solvencia.

### 4.3 "Enriquecimiento Exa por NIF" → **Contexto sectorial/macro (o se cae)**
Buscar por NIF es imposible: no hay cruce y el dato es sintético. Uso honesto y aun así
vistoso: cuando el motor detecta un peer set entero deteriorándose, Exa trae **prensa
económica real del sector** para poner contexto macro en el panel — *"el peer set está
torciéndose y esto coincide con X publicado"* — siempre etiquetado como **contexto externo,
no dato de la empresa**. Si no aporta, se retira: no es un requisito del track, es un extra
de patrocinador.

---

## 5. Especificación técnica de soporte

El motor ya produce los paneles aditivos (`calc_score.py` → `score_panels.npz`). La API solo
los sirve. Contrato alineado con `REQUISITOS.md` B7 (congelado en 2 h; nadie espera).

```text
GET  /score/{entity_id}?month=   → { score, nivel, tendencia, estado, confianza,
                                     drivers[{feature, contribución, valor, p_peer}],
                                     trayectoria[24], códigos_razón[] }
GET  /group/{group_id}           → { consolidado, filiales[] }
POST /simulate {entity_id, palancas:[{id, magnitud}]}
                                 → { score_nuevo, delta_score, caja_liberada_eur,
                                     delta_bps, eur_año }
GET  /alerts?desde=              → [{ entity_id, severidad, mes_detección,
                                      meses_anticipación, drivers_movidos[] }]   ← con tasa de
                                                                                  falsas alarmas
GET  /passport/{token}           → dossier público caducable (acto 6)
POST /action/generate            → borrador trazable (opcional; cada término viene de
                                   /simulate en el request, ver §4.1)
```

**Reglas de la capa API:** determinista (misma entrada → misma salida, RNF-1); errores con
forma útil (entidad inexistente, mes fuera de rango, palanca inaplicable, RF-B7.6/B8.5);
**modo offline** con fixture de respuestas grabadas para correr la demo sin red (RF-B7.7);
scores **precomputados y cacheados** para que `/score` y `/simulate` vayan por debajo de 1 s
(RF-B7.5).

**Ejemplo de `/simulate` (valores de relleno; el real lo pone el motor):**
```json
{
  "entity_id": "ES_BXXXXXXXX",
  "palancas": [{"id": "reducir_dso", "magnitud": {"dias": 12, "clientes": ["CP_1","CP_2"]}}]
}
```
```json
{
  "score_nuevo": "<salida del motor>",
  "delta_score": "<salida del motor>",
  "caja_liberada_eur": "<ΔDSO × facturación diaria, aritmética>",
  "delta_bps": "<estimación: etiquetada como tal en pantalla>",
  "eur_año": "<producto de las anteriores>"
}
```

---

## 6. Guion cronometrado para el pitch (2:30)

**Confirmar antes la duración real** con la organización: el enunciado §10 dice 2:30; el
research de Quirce planifica 5 min. El guion se cierra para la duración confirmada.

| Tiempo | Acto | Narrativa y acción en pantalla |
| :--- | :--- | :--- |
| **0:00 – 0:30** | **1. La paradoja** | Pantalla partida. Modo Bureau: *"aquí las dos valen 65 y 68; cualquier banco aprobaría a la misma".* Modo X-Ray: *"con el rastro diario, una va a más y la otra se tuerce. Y aquí está el mes en que lo vimos."* |
| **0:30 – 0:55** | **2. El porqué** | Cascada que suma exacto hasta el score. *"Esto no es un SHAP: es la aritmética del modelo. Por eso el agente no opina, simula."* |
| **0:55 – 1:15** | **3 y 4. Dos caras y anticipación** | La que sube y la que baja con el mismo motor. Luego el número honesto: *"mediana de N meses a 1 falsa alarma por empresa-año, contra baseline de 0."* |
| **1:15 – 1:50** | **5. El what-if en euros** | Aplicar palanca → `score_nuevo`, `caja_liberada`, `bps`, €/año. *"Las dos patas separadas: esta es aritmética, esta es estimación."* |
| **1:50 – 2:15** | **7 (o 6). El grupo / el QR** | Si hay grupo: *"el grupo saca 71 pero la filial arrastra"*. Luego el QR: *"escanéelo: el dossier bancario de la empresa, en su móvil."* |
| **2:15 – 2:30** | **Cierre (K Fund / Embat)** | *"Embat ya tiene el workflow de 400 corporaciones. Con este motor no solo ven moverse el dinero: se convierte en el sitio donde se decide el crédito. El dueño del score es la empresa."* |

**Regla del guion.** Los huecos `N`, `X`, `Y` se rellenan con lo que devuelva el motor en el
**ensayo**, nunca se fijan a mano. Si un número cambia entre ensayo y directo, el guion no se
reescribe: se dice el del motor.

---

## 7. Avisos técnicos a cerrar antes del sábado por la noche

| Aviso | Evidencia | Acción |
| :--- | :--- | :--- |
| **`algorythm/validate_score.py` no está en el árbol** y el test de anticipación lo importa | `test_score_engine.py:130` importa `algorythm.validate_score.stress_control`; solo hay `__pycache__/validate_score...pyc` | Commitearlo o el acto 4 no es reproducible y el test cae |
| **El ERP solo se calcula como snapshot a 2026-09-01** y está desactivado por defecto | `calc_score.py:26-29` (`erp_snapshot=False`, `'disabled_without_verified_direction_and_historical_states'`) | No enseñar drivers de DSO/retraso de pago **antes** de sep-2026 como si fueran mensuales. Si el acto 1 quiere DSO en el mes 18, es trabajo de B1 |
| **Simetría parcial**: crecimiento unilateral `max(x,0)`, fragilidad solo resta, recorte 0–100 | `score_engine.py:221-233` | Montar el CA de simetría (RF-B13.6) antes de vender "dos caras"; si sale mal, matizarlo en el acto 3 |
| **Los ficheros del benchmark (`score_v2.py`, `quant_analysis.py`…) citados en `__pycache__` no están versionados** | `algorythm/benchmark/__pycache__/*` sin fuentes | Confirmar qué es la versión buena antes de que el jurado abra el repo |
| **La demo en vivo no puede depender de red** | RNF-1, RF-B7.7 | Fixture offline + PDF/captura de respaldo del dossier y del resultado de `/simulate` |

---

## 8. Riesgos de demo y mitigación

| Riesgo | Mitigación |
| :--- | :--- |
| Se dice una cifra que no sale de `/simulate` | Regla madre (§1). El front solo pinta lo que devuelve la API; cero literales |
| El QR no carga (wifi del aula) | Dossier precomputado + PDF de respaldo + URL alternativa; probado en el proyector |
| Se afirma "quiebra/deterioro real" sobre dato sintético | RF-B12.6: decirlo **nosotros** antes: *"el score mide coherencia interna, no leyes de impago reales"* |
| El número de anticipación se infla | Reportarlo siempre con la tasa de falsas alarmas y el baseline tonto (§3, acto 4) |
| El grupo no está listo el domingo | Es opcional: cae del guion sin tocar el resto; nunca se improvisa en directo |
| Exa falla o devuelve ruido | Es contexto externo y opcional; se retira sin afectar a los actos 1–6 |
| Se dice "Embat no tiene X" sin comprobarlo | RF-B12.11: Embat ya calcula DSO/DPO/aging. El hueco es la **nota unificada + trayectoria + what-if en euros** |

---

## 9. Reglas de integridad (no negociables)

1. **Cero cifras hardcodeadas.** Todo número en pantalla viene de `/score`, `/simulate` o
   `/alerts`. Los huecos del guion se rellenan en ensayo.
2. **Una sola fuente de verdad.** El front no recalcula nada: pinta. Si dos pantallas
   muestran cifras distintas, es un bug, no una narrativa.
3. **Nada de "quiebra", "impago real" ni "verificado"** sobre datos sintéticos. Se declara
   que el dataset es sintético en pantalla y en el pitch (RNF-7, RF-B12.6).
4. **La anticipación siempre con tasa de falsas alarmas y baseline.** Sin eso, el requisito
   no está cumplido (`CA-B5`).
5. **El agente no opina, simula.** Elige y parametriza palancas del catálogo cerrado; no
   inventa cifras. El borrador de §4.1 se etiqueta como borrador.
6. **El dossier no es un sello.** Es el documento único que hoy se monta ocho veces.
7. **Lo que no está, no se enseña.** Si un acto no está verde a las 22:00 del sábado, cae del
   guion; no se demuestra a medias en directo.

---

## 10. Checklist de 60 segundos antes de subir al escenario

- [ ] Demo abierta en la URL pública, no en `localhost`.
- [ ] Modo offline cargado y PDF/capturas de respaldo a mano.
- [ ] Caso Northbrook/Velasco elegido **entre las 373 empresas con 24 meses** y verificado.
- [ ] `/simulate` devolviendo los mismos números que en el último ensayo (determinismo).
- [ ] El número de anticipación con su tasa de falsas alarmas a la vista.
- [ ] QR probado desde un móvil real en la sala.
- [ ] Frase de apertura y cierre memorizadas; el resto improvisado sobre lo que se ve.
