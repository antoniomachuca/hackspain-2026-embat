# Decisiones de producto · fuente para agentes

Documento de conocimiento interno. Lo leen agentes (y humanos que implementan o explican el sistema). No es un pitch. Si un README, un brief o una slide discrepan del código o de este contrato, **gana lo implementado + este documento**. Las fórmulas del score viven en [`MATEMATICA.md`](MATEMATICA.md); aquí solo se referencia qué superficie las consume y qué **no** puede recalcular el front.

**Maestro de alcance (seis preguntas):** [`PRODUCTO-MAESTRO.md`](PRODUCTO-MAESTRO.md) — prevalece sobre [`PRODUCTO.md`](PRODUCTO.md) y [`REQUISITOS.md`](REQUISITOS.md) en lo que se contradiga.  
**Comprador, hueco y narrativa (contexto):** [`PRODUCTO.md`](PRODUCTO.md).  
**Demo / integridad de cifras:** [`.agents/factorwow.md`](../.agents/factorwow.md).  
**Front (rutas y modos):** `front/components/shell.tsx`, `front/lib/cartera.ts`, `front/components/ficha-empresa.tsx`.  
**API:** `backend/routes/` (`companies`, `stats`, `simulate`, `palancas`, `graph`, `forecasts`, `alerts`).  
**Palancas (contrato de dominio):** `research/capa_intermedia_mejoras.md`, `research/capa_intermedia_decisiones.md`, `docs/respuestas_a_pedro.md`.  
**Marcas en trayectoria:** `research/dos_puntos_trayectoria.md`, `algorythm/EPISODIOS.md`.  
**Anillo bache/tendencia (front):** `research/guia_front_reparto_bache_tendencia.md`.  
**Abanico estructural (front):** `forecasting/GUIA_FRONT_ESTRUCTURAL.md`.

---

## 0. Principio madre

1. **El algoritmo es la única fuente de verdad.** El front **pinta**. No recalcula score, waterfall, anillo de reparto, abanico estructural ni ΔS de palancas.
2. **El agente no opina, simula.** Toda propuesta de mejora pasa por `POST /api/simulate` (recompute) antes de pantalla. El what-if heurístico (`POST /api/whatif`) es legacy del bot; **no** es el contrato de producto.
3. **Cero cifras hardcodeadas** en UI o guion. Si falta dato, se oculta el bloque o se abstiene; no se inventa un número “para que se vea bien”.
4. **Dato sintético.** No se afirma quiebra, impago real ni “verificado” sobre empresas del dataset. El score mide coherencia interna.
5. **No decir “Embat no tiene X”** sin haberlo comprobado. Embat ya calcula DSO/DPO/aging; el hueco es **nota unificada + trayectoria + what-if en euros**.

Si un agente tiene que elegir entre subir métrica del leaderboard y que la demo abra sin fallos: **gana la demo** (enunciado: un modelo sencillo con producto claro encima interesa más).

---

## 1. Comprador y qué se vende

| Pregunta | Decisión cerrada |
| :--- | :--- |
| ¿A quién se vende? | **Embat** (TMS mid-market, multi-entidad). No a la pyme anónima como buyer primario del pitch. |
| ¿Qué no tiene Embat (hueco declarado)? | Score de salud **unificado**, trayectoria leíble, what-if que mueva la misma \(f\). No “falta de DSO”. |
| ¿Sello / pasaporte criptográfico? | **No.** Bancos consumen ECAI/CIRBE/Informa. Producto = **dossier bancario** (score + trayectoria + drivers + corte), caducable; hash solo como reproducibilidad de código, no certificación de solvencia. |
| ¿Dueño del score? | **La empresa** (acto what-if antes que pack para el prestamista). Evita degenerar en herramienta solo del lender. |
| ¿Leaderboard vs producto? | Misma \(f\). Módulo de **grupo**: opcional para leaderboard, **núcleo de producto** (Embat es multi-entidad). |
| ¿Vigilancia de clientes (contraparte↔empresa)? | **Imposible** (cruce 0,0 %). Sustituto: quién *te* paga cada vez más tarde (tus facturas). |

Tres actos de valor (PRODUCTO.md): (1) motor + ficha/cartera, (2) simulador, (3) pack de negociación. Transversal: monitor proactivo (Telegram/email), no solo dashboard reactivo.

---

## 2. Dos audiencias, un motor

El shell distingue modo **`embat`** y modo **`empresa`** (`front/components/shell.tsx`).

| Audiencia | Entrada | Qué ve |
| :--- | :--- | :--- |
| **Embat** (cartera) | `/`, `/embat/[id]`, `/grupos`, `/grupo/[id]` con base `/embat`, `/grafo` | KPIs de 1.286 clientes, segmentos Apostar/Vigilar/Acompañar, ficha con lectura de cartera encima |
| **Empresa** (módulo X-Ray) | `/[company_id]`, `/empresa/[id]`, `…/grupo` sin prefijo embat | Solo a sí misma: score, trayectoria, palancas, su grupo |

Misma ficha (`FichaEmpresa` con `vista: "embat" | "empresa"`): cambia copy (“Cliente …” vs nombre propio), CTAs y prefijos de links. No cambia el motor.

X-Ray se presenta **dentro** del catálogo de Embat (sección “Gestión de riesgos financieros”), no como app suelta sin contexto TMS.

---

## 3. Las seis preguntas → superficies

Maestro: [`PRODUCTO-MAESTRO.md`](PRODUCTO-MAESTRO.md). Mapeo operativo (qué hay / qué no inventar):

| # | Pregunta | Superficie de producto | Quién calcula |
| :--- | :--- | :--- | :--- |
| 1 | Quién está sano | Score grande en ficha; bandas `SOLIDA`/`INTERMEDIA`/`DEBIL`; cartera | Back (`calculate_scores` + `health_band`) |
| 2 | Quién está mejorando | Serie 24 meses; estados `MEJORANDO`/`RECUPERACION`; segmento Apostar | Back |
| 3 | Quién se tuerce | Estado `TORCIENDOSE`; punto rojo (detección); segmento Vigilar | Back (`classify_states`, episodios) |
| 4 | Bache o caída | Estado `BACHE` (ámbar) **y** anillo 30/70 del mes (reparto) | Back; front solo pinta. **No** son el mismo objeto |
| 5 | Por qué ha cambiado | Waterfall de puntos; drivers del episodio; texto de alerta | Back; LLM como mucho **redacta** a partir del JSON, no inventa Δ |
| 6 | Cuándo se vio venir | Punto hueco (perspectiva 6 m) + detección; N = meses hueco→rojo | Back (`outlook` / episodios). **No** PD. **No** `lead_months` inventado en vivo |

**PRODUCTO-MAESTRO** aún dice “comparar con el sector” y “probabilidad de subir/bajar”. En implementación:

- Peer/sector en el gráfico: cuartil de tamaño donde exista; **no** hay sector en el dataset (0 empresas con sector). No inventar CNAE.
- Cono de producto en ficha/home: **estructural** (cuenta → \(f\)), no “probabilidad calibrada de quiebra”. Laboratorio `/prevision` = otro artefacto (benchmark Ridge/Huber/etc.).

---

## 4. Mapa de rutas (front)

| Ruta | Rol |
| :--- | :--- |
| `/` | Cartera Embat: KPIs, histograma, trayectoria media, rankings, segmentos, tabla |
| `/embat/[company_id]` | Ficha cliente (vista Embat) |
| `/[company_id]` | Ficha empresa (módulo) |
| `/empresa/[id]` | Alias / escenarios según cableado actual |
| `/empresa/[id]/drivers` | Drivers |
| `/grupos`, `/grupo/[id]` | Holdings (base `/embat` o empresa) |
| `/grafo` | Flujos intra-grupo **inferidos** |
| `/comparar` | Lado a lado (Northbrook/Velasco si se eligen con 24 meses) |
| `/prevision` | Laboratorio de modelos del benchmark (no confundir con abanico estructural de ficha) |

Si falta artefacto o empresa `is_prior`: abstenerse / ocultar bloque. No rellenar con fixtures inventados en producción de demo salvo modo offline explícito (factorwow).

---

## 5. Segmentos de cartera (Embat)

Regla **duplicada a propósito** en SQL y TS; si se toca una, se toca la otra:

- Back: `SEGMENT_SQL` en `backend/routes/stats.py`
- Front: `front/lib/cartera.ts` → `segmentoDe`

| Segmento | Condición | Acción de producto |
| :--- | :--- | :--- |
| `APOSTAR` | `state_eligible` ∧ score ≥ 60 ∧ (`MEJORANDO` \| `RECUPERACION` \| Δ3m ≥ 10) | Candidata a línea / módulo |
| `VIGILAR` | `TORCIENDOSE` \| `DETERIORO` | Retención: ayudar antes de perder al cliente |
| `ACOMPANAR` | `BACHE` | Seguimiento; no actuar como si fuera deterioro |
| `null` | Resto (estable sin señal, pending, etc.) | Sin segmento de acción |

No es un modelo ML. No reordenar Apostar por ΔS de palancas de circulante.

---

## 6. Ficha: qué se muestra y en qué orden (contrato mental)

1. **Score** (grande) + banda + estado (anillo de estado ≠ anillo de reparto del mes).
2. **Trayectoria** con como máximo **dos marcas** (rojo = detección; hueco = perspectiva). Ver §7.
3. **Porqué** = waterfall / drivers del motor (no beeswarm SHAP).
4. **Ratios / operativa** (DSO, DPO, etc. cuando el endpoint los da; no inventar ERP histórico mensual si el snapshot está off).
5. **Palancas** = dos listas (salud vs circulante). Ver §8.
6. **Grupo** = consolidado + filiales; link a grafo si aplica.

Vista Embat añade encima: segmento, Δ3m, producto Embat con más efecto si está cableado. Vista empresa no habla de “cartera”.

---

## 7. Marcas en el gráfico de trayectoria

Contrato: `research/dos_puntos_trayectoria.md`, `algorythm/EPISODIOS.md`.

| Marca | Significado | Reloj | Reglas de UI |
| :--- | :--- | :--- | :--- |
| **Punto rojo** (relleno) | Monitor confirmó giro (`TORCIENDOSE`/`DETERIORO` o simétrico mejora) | \(t_{\mathrm{alerta}}\) | Marca principal |
| **Punto hueco** | Si no reviertes, a 6 meses \(\hat S\) ya es feo | \(t_{\mathrm{anticipación}}\) | Solo a la **izquierda** del rojo; mismo mes o después → **no pintar hueco** |
| Texto | Familia salud \| circulante | pie | Un texto, no un tercer punto |

- Nunca tres marcas. Nunca pintar \(\hat S_{t+6}\) como coordenada futura: el hueco se dibuja sobre la curva **observada** en \(t\).
- `outlook` es eje **paralelo** a `state`. No cambia el color del anillo de estado a naranja. No dispara alerta ALTA. No entra en TOP 5 de deterioro.
- `BACHE` es ámbar provisional; **no** es el rojo.
- Copy: hipótesis condicionada (“si esto sigue…”), **nunca** “quiebra en 6 meses” ni PD.
- `lead_months` en feed vivo = `null` salvo evento de laboratorio con oráculo. El N visible de ficha es `perspectiva.meses_antes_deteccion` (hueco → rojo), no un lead inventado.

---

## 8. Anillo bache / tendencia del mes

Contrato: `research/guia_front_reparto_bache_tendencia.md`, cálculo en `algorythm/score_decompose.py`.

| Decisión | Cerrada |
| :--- | :--- |
| ¿El front calcula el split? | **No.** Solo pinta `reparto` del history. |
| ¿Fallback a `repartir()` OLS? | **Prohibido** en camino API. Si no hay `reparto`, **ocultar** el anillo. |
| ¿Anillo + drivers? | Sí: 70/30 **y** hasta 3 drivers debajo. |
| Copy `kind` | `estructural` → «tendencia»; `coyuntural` → «bache». **Nunca** la palabra «estructural» al CFO. |
| ¿Página `/descomposicion`? | **No.** Vive en el bloque de previsión/trayectoria de ficha. |
| ¿Mezclar con estado `BACHE`? | **No.** Persistencia 3m ≠ composición del Δ del mes. |
| ¿Mezclar con \(\varphi=0{,}8\)? | **No.** |

Colores de referencia en guía: tendencia `#b083e8`, bache `#dfb631`.

---

## 9. Abanico / proyección en ficha (estructural)

Contrato: `forecasting/GUIA_FRONT_ESTRUCTURAL.md`.

| Superficie | Modelo | Nota |
| :--- | :--- | :--- |
| Home / ficha (`proyeccion`) | `structural_v2` (cuenta → `calculate_scores`) | Producto |
| `/prevision` | Artefactos del benchmark (Huber/Ridge/media…) | Laboratorio |

El front **no** porta `structural.py`. Pide series `alto` / `medio` / `bajo` de longitud 12 (meses futuros, sin el hoy). Si faltan, **no** inventar `momentum × 14` en demo seria; ocultar o degradar de forma explícita.

Mapeo: alto = optimistic (mejor para el score), medio = central, bajo = pessimistic. Ordenar por score tras puntuar caminos ( \(f\) no es monótona en flujos).

Lumps (cobros a golpes): el back ya puede usar mediana en central; el front no “arregla” revirtiendo a media larga.

---

## 10. Palancas y simulador

### 10.1 Contrato HTTP

```
GET  /api/palancas?company_id=
POST /api/simulate          → modo=contrafactual_de_corte, mes 23, model_version, warnings
GET  /api/simulate/rankings → sugerencias[] + opciones_circulante[]
```

- Mutar **solo el último mes** del extracto. Copy de pantalla: *«si el último mes del extracto hubiera sido así»*, **no** «proyección a 90 días».
- `delta_bps = null` (curva score→tipo **retirada**).
- `caja_liberada_eur` = circulante liberado, no beneficio; warning `caja_es_circulante_no_beneficio`.
- `is_prior` / score 50 exacto → **cero palancas** (`motivo_rechazo=sin_evidencia_score`).

### 10.2 Dos familias = dos rankings

| Pista | Lista | Ordena por | `delta_score` |
| :--- | :--- | :--- | :--- |
| Salud | `sugerencias[]` | ΔS de recompute | definido |
| Circulante | `opciones_circulante[]` | caja neta | **`null`** |

Concatenar y ordenar todo por ΔS es **bug de producto**: el motor premia DPO como liquidez; no se vende como “estar más sano”.

### 10.3 Honestidad de costes

- `adelantar_cobros` unifica descuento (`lineas[]`: facturas/clientes, días, tasa). Tasa 0 solo con supuesto tipado en UI.
- Confirming: fee; **no** bajar `expenses` (422 si E↓).
- Cobertura baja ≠ muerte de la palanca: `es_aplicable=false` + motivo.
- MVP demo (tres): adelantar cobros, recortar opex, refinanciar. Catálogo producto = más ancho; la demo elige subset.

### 10.4 Agente / borrador

El agente **elige y parametriza** del catálogo. El número lo pone `/simulate`. Si se genera documento (descuento, memo): etiquetar **borrador** ensamblado con cifras del motor, no “plan vinculante” ni memorando legal libre.

`/whatif` heurístico: no borrar (legacy Telegram); **no** usarlo en la demo de producto.

Checklist de implementación: `research/capa_intermedia_checklist.md`.

---

## 11. Grupo, contagio y grafo

| Pieza | Decisión de producto |
| :--- | :--- |
| Consolidado | \(0{,}65\cdot\bar S + 0{,}35\cdot\min\) en `GET /api/groups/{id}` (`stats.py`). Media aritmética, no ponderada por volumen. |
| Contagio | Penalización **informada** aparte si \(\min S < 40\); **no** restar en silencio del consolidado. |
| Filtro `transfer` al consolidar | Decisión de producto antigua; **no implementado**. No improvisar en vivo. |
| Grafo clientes entre empresas | **No** (cruce 0,0 %). |
| Grafo UI `/grafo` | Matching intra-grupo (mismo día, importe opuesto, ≥500 €, ≥2 coincidencias). Ruido declarado ~1,6 %. Enseña quién drena/sostiene; **no** contagia scores. |

---

## 12. Monitor, alertas y canales

- Alertas ALTA/MEDIA solo desde `NEGATIVE_STATES` (`TORCIENDOSE`, `DETERIORO`). `BACHE` y `outlook` no.
- Telegram: palancas + simulate + botones; no inventar Δ fuera del dominio.
- Email a la empresa en Torciéndose/Deterioro (Mailpit en local): gráfica de trayectoria, no PD.
- Cursor temporal / `model_version`: un bump de modelo no debe aparentar evento financiero.

---

## 13. Diseño visual (Embat-like)

Research: `research/producto_research_quirce.md`.

- ADN: marino `#050b2c` + aguamarina + blancos; **dos pesos** tipográficos, no cinco.
- La demo debe verse “como módulo Embat”, no como dashboard genérico de hackathon.
- Explicabilidad es razón de compra (71 % rechazaría IA sin explicación): el waterfall es producto, no adorno.

---

## 14. Demo e integridad (factorwow)

Reglas no negociables ([`.agents/factorwow.md`](../.agents/factorwow.md)):

1. Todo número en pantalla sale de `/score`, `/simulate`, `/alerts` o history/forecast API.
2. Una sola fuente: si dos pantallas discrepan, es bug.
3. Nada de “quiebra / impago real / verificado” sobre sintético; decirlo nosotros.
4. Anticipación siempre con tasa de FA y definición de evento; si no, no vender el número.
5. Lo que no esté verde el sábado noche **cae del guion**; no demostrar a medias.

Northbrook / Velasco: elegir entre empresas con **24 meses** completos cuando se enseñe la paradoja del mes 24.

Vídeo (`video/`): usa componentes del front; cifras de palancas vía `simular()`, no literales. Tres actos = motor / palancas / negocio (alineados a los tres bloques del enunciado).

---

## 15. Jerarquía documental (qué manda)

| Tema | Documento que manda | Notas |
| :--- | :--- | :--- |
| Seis preguntas / alcance UI mínimo | `PRODUCTO-MAESTRO.md` | Corto; puede estar por detrás del código en “sector” y “probabilidades” |
| Comprador, hueco, agente, leaderboard | `PRODUCTO.md` | Superado solo donde contradiga al maestro |
| Fórmulas y linaje del score | `MATEMATICA.md` | Código gana a whitepaper |
| Palancas / simulate | `capa_intermedia_*` + `respuestas_a_pedro.md` | Congelado |
| Dos puntos trayectoria | `dos_puntos_trayectoria.md` + `EPISODIOS.md` | Congelado |
| Anillo mes | `guia_front_reparto_bache_tendencia.md` | Front no calcula |
| Abanico ficha | `GUIA_FRONT_ESTRUCTURAL.md` | ≠ `/prevision` lab |
| Demo | `factorwow.md` | Integridad de cifras |

`REQUISITOS.md` y briefs antiguos pueden hablar de percentiles, `delta_bps`, grafo de clientes o gradiente: **stale** salvo que el código lo implemente. Cruzar con `MATEMATICA.md` y este archivo.

---

## 16. Mapa de archivos para no contradecir el producto

| Si vas a… | Lee primero | No hagas |
| :--- | :--- | :--- |
| Añadir pantalla / ruta | §2–4, `shell.tsx`, maestro | Segundo motor en el cliente |
| Pintar trayectoria / alertas | §7, episodios, estados | Tres marcas; PD; `lead_months` vivo inventado |
| Anillo 30/70 | Guía reparto | OLS `repartir()`; copiar “estructural” al CFO |
| Cono en ficha | Guía estructural | Usar JSON del lab `/prevision` como si fuera estructural; `momentum×14` |
| Palancas / UI simulate | §10, checklist capa intermedia | Una sola lista ordenada por ΔS; bps inventados; mutar historia |
| Cartera Embat | `cartera.ts` + `SEGMENT_SQL` | Cambiar un lado solo |
| Grupo / grafo | §11 | DebtRank; restar contagio oculto; fingir red de clientes |
| Copy / pitch / vídeo | factorwow + este §0 y §14 | Cifras de guion no salidas del motor |
| “Mejorar” el score desde front | `MATEMATICA.md` | Cualquier fórmula en TypeScript |

---

## 17. Lo que el producto no es (para no afirmarlo)

- No es un bureau ni un ECAI.
- No es vigilancia de contrapartes entre empresas puntuadas.
- No es un chatbot que “recomienda” sin `/simulate`.
- No es el laboratorio `/prevision` como historia principal de la ficha.
- No es un sello “verificado” con hash de marketing.
- No sustituye Informa; añade rastro continuo y what-if.
- No promete PD ni meses hasta quiebra en cartera real.

El contrato de producto es: **misma \(f\), dos audiencias, cifras solo del motor, honestidad de circulante, abstención cuando no hay evidencia.** El resto (fórmulas, umbrales, estructural) está en [`MATEMATICA.md`](MATEMATICA.md).
