# Producto · Qué construimos encima del score y a quién se lo vendemos

**Alcance:** el producto, el comprador y la narrativa.
El algoritmo vive en [`research/algo_research_pedro.md`](research/algo_research_pedro.md).
**Última actualización:** 2026-09-18 (rev. 2, con el dataset explorado — ver
[`research/informe_exploracion.md`](research/informe_exploracion.md))

---

## 0. Cómo encaja con el brief del algoritmo

El brief de Pedro define **el motor**: features, nivel, tendencia, estados, explicación.
Este documento define **lo que se monta encima** y cierra las tres discrepancias que
había entre los dos textos:

| Discrepancia | Resolución |
| --- | --- |
| ¿ML supervisado (EBM/LightGBM) o score aditivo por reglas? | **Manda el brief: reglas.** Sin etiqueta no hay entrenamiento posible, solo ajuste de 5-6 pesos contra el leaderboard. Ver §6 |
| El research de Carlos (Claude, Gemini, ChatGPT) y de Quirce recomienda **GBDT + SHAP** | **Resuelto por el dato (18-sep): el dataset no trae ningún target.** GBDT solo si el script de scoring revela una etiqueta. Donde sí coinciden todos: nada de SHAP crudo en pantalla |
| ¿Módulo de grupo, núcleo u opcional? | **Opcional para el leaderboard, núcleo para el producto.** Ver §4 |
| ¿Cómo se mide la anticipación? | La del brief, **añadiendo control de falsas alarmas**. Ver §4 |
| Quirce propone **"vigilancia de clientes"** como producto | **Imposible tal como se planteó**: las contrapartes no cruzan con ninguna empresa (0,0 %). Queda la versión pequeña: quién *te* paga cada vez más tarde. Ver §4 |

---

## 1. TL;DR

Construimos **el score de salud financiera que ningún TMS europeo tiene**, y encima un
**dashboard con un agente que simula mejoras contra nuestro propio motor**.
Comprador: **Embat**. Se lo vendemos con su propia tesis —
_"workflow ownership earns transaction ownership"_ — que hoy solo ejecutan por pagos.

**El principio de arquitectura, y la frase del pitch:** el algoritmo es la única fuente
de verdad. **El agente no opina, simula**: toda propuesta pasa por `/simulate` antes de
llegar a pantalla.

---

## 2. El comprador es Embat

| Hecho | Consecuencia |
| --- | --- |
| ICP = mid-market **50–500 M€**, multi-entidad, multi-divisa | No es una pyme anónima: **no necesita un sello de confianza**. Necesita negociar mejor con sus 8 bancos |
| ~400 clientes, Serie B 30 M€ (may-2026, Cathay), ~150 personas | Tienen dinero y presión de producto |
| Ya calcula DSO/DPO, aging y exposición a contrapartes, y TellMe ajusta previsiones por comportamiento de pago (research ChatGPT-Carlos §3) | **Las señales las tienen.** Lo que no tienen es la nota que las resume, su trayectoria y el what-if. Ese es el hueco, y **no se afirma nada más sin comprobarlo en embat.io** |
| **Cero menciones públicas** a un score de salud financiera unificado, crédito o financiación embebida | Hueco declarado, no línea existente |
| Ningún TMS europeo publica un score (Agicap, Kyriba, Nomentia, Tesoralia) | Terreno libre dentro de su categoría |
| Defacto ya hace lending embebido B2B por API (>1.200 M€, <27 s) | No proponemos que monten un banco: que originen y el riesgo lo ponga un tercero |

**El argumento más fuerte ante el jurado:** el benchmark contra el peer set anónimo de los
250 grupos **solo lo puede construir quien agrega a todos**. Es un efecto red de datos que
Embat ya tiene y no monetiza.

---

## 3. Por qué hay hueco — las cifras del pitch

**El retardo de los bureaus es la grieta.** Informa D&B puntúa con cuentas depositadas en
el Registro Mercantil: cierra 31-dic → se aprueba hasta 30-jun → se deposita hasta 30-jul
→ publica en otoño. **El input financiero arrastra 8–18 meses** (media 12–14; un score
consultado en marzo se apoya en cuentas de hace **15 meses**). A diario solo se mueven
RAI/ASNEF/EBE, BORME y Paydex: **el balance, no.** Experiencia de pago registrada: solo
~300.000 de ~3,2 M de empresas españolas.

> **La frase:** _"Informa te puntúa con un balance de hace 15 meses. Nosotros, con el
> movimiento de ayer."_

**Matiz honesto, y lo decimos nosotros antes de que lo pregunten:** el cash-flow
**complementa** al bureau, no lo sustituye. FinRegLab 2019: solo flujo de caja da AUC
0,592–0,725; **combinado con el score tradicional, 0,758 frente a 0,720 de FICO solo**.
FinRegLab 2025 (424.546 obs.): **+3,0 pp de aprobaciones a igual riesgo**. Intuit
QuickBooks Capital, el caso pyme más parecido: **K-S 0,437 con XGBoost vs 0,410** del
scorecard tradicional. Posicionamiento: **no matamos a Informa, le añadimos los 15 meses
que le faltan** — y se lo damos a la empresa, no al prestamista.

**Nadie vende el what-if.** Único hallazgo mundial: Experian Business Interactive Score
Planner (US), y **no traduce puntos a coste de financiación**. Nav da "key factors" sin
simulador. D&B CreditSignal: alertas direccionales sin el número. CreditHQ puntúa a
terceros, no a ti. Los simuladores que mapean score → tipo → € son **todos de consumo**.

**El open banking scoring se vende al prestamista, nunca al empresario.** Plaid Beacon es
antifraude; LendScore va al lender. Codat (Accounting Score, ene-2026): sin what-if, al
lender. Validis, Bud, Tink, Ozone, Uplinq: infraestructura B2B2B. **Cero productos donde
el dueño del score sea la empresa.**

Precios de referencia: Iberinform 8–16 €/informe (packs 540–1.140 €/año) · Informa
30–60 €/informe · rating solicitado Inbonis 500–1.500 €.

---

## 4. Lo que entregamos: tres actos

**Acto 1 — El motor.** Score mensual explicable, **a nivel filial y consolidado de grupo**.
_"El grupo saca 71, pero la filial portuguesa saca 38 y arrastra al consolidado."_ Es la
conversación que Embat tiene con sus clientes cada día, y por eso el módulo de grupo
(brief §12) es **opcional para el leaderboard pero obligatorio para el producto**: multi-
entidad es la razón de ser de Embat. Mecanismo con precedente (IEEE-CIS Fraud): agregados
group-by por entidad y, en post-proceso, la predicción de la entidad como media ponderada
de sus miembros. Antes de agregar, eliminar flujos intragrupo — de forma **aproximada**
(por categoría `transfer`), porque las contrapartes no cruzan entre empresas.

**Acto 2 — El simulador.** Cada recomendación con su delta de score **y** su delta de
euros: _"cobra 12 días antes a estos 5 **clientes** → +6 pts → −35 bps → 14.000 €/año."_
Es *Experian Boost para la tesorería*, y en B2B no existe (§3).

**Acto 3 — El pack de negociación bancaria.** Score + trayectoria + drivers + benchmark
sectorial, en un link con caducidad. No es un sello de confianza —los bancos consumen
ratings ECAI, CIRBE e Informa, no distintivos gráficos—: es **el dossier que hoy montas
ocho veces**, una sola vez y siempre actualizado. Aquí Embat monetiza.

**Transversal — El monitor.** El agente es **proactivo, no reactivo**: no espera a que
abras el dashboard. _"Velasco Industrial lleva 3 meses torciéndose; lo vimos en el mes 19,
cuatro meses antes de que se notara. Esto es lo que se movió."_

### Diferenciadores que probablemente nadie más tenga

1. **Anticipación medida con honestidad.** La definición del brief (§9) es buena, pero le
   falta una pieza: **sin fijar la tasa de falsas alarmas el lead time se infla
   trivialmente**. Reportar _"mediana de N meses a 1 alerta por empresa-año en las sanas"_.
   El especialista de datos de Embat lo va a preguntar.
2. **Nivel grupo**, no solo empresa.
3. ~~Grafo de contrapartes~~ **Descartado por el dato**: cruce contraparte↔empresa 0,0 %.
   Sustituto realista y aun así inédito en TMS: **cobros por cliente** — la tendencia del
   retraso de cada cliente *hacia ti*, sobre tus propias facturas (98,7 % con contraparte).
   No puntúa al cliente; enseña quién te está pagando cada vez más tarde.
4. **Bache vs. deterioro** con reglas defendibles en un slide (brief §6.5).
5. **Explicación como descomposición exacta del score aditivo**, no un beeswarm de SHAP.

---

## 5. Arquitectura y reparto

**Principio:** el algoritmo es la única fuente de verdad. El agente **no opina, simula**.

```
┌─ NÚCLEO ────────────────┐
│  Carlos                 │
│  núcleo algorítmico     │──┐
│                         │  │    Pedro              Quirce             Hugo
│  Antonio                │  ├──► capa intermedia ──► agentes ────────► producto,
│  arquitectura + fórmula │──┘    orquestación        → producto/front   front,
└─────────────────────────┘       de mejoras                            narrativa
```

Las flechas son **dependencia de datos, no orden de trabajo**. Nadie espera a nadie: se
congela el contrato y se mockea (ver abajo).

| Quién | Posee | Del brief |
| --- | --- | --- |
| **Carlos** | Pipeline de features, percentiles congelados por peer, nivel N(t), envíos al leaderboard. **Dueño de la métrica** | Fases 1-3, 6 |
| **Antonio** | Arquitectura del servicio (que el núcleo sea llamable), research de fórmula (pesos, sensibilidad, validación), tendencia y estados, **y la curva score → tipo de interés**. **Dueño del despliegue de la API** | Fases 4, 7, 9 + §6.4 |
| **Pedro** | Capa intermedia: catálogo de palancas, `/simulate`, orquestación de mejoras, monitor proactivo. **Dueño del contrato** entre ejes | Fases 5, 8 |
| **Quirce** | Traducción de agentes a producto: qué propone el agente, cómo se presenta, vistas del dashboard. **Dueño del despliegue del front** | — |
| **Hugo** | Diseño de producto, front, narrativa, guion, ensayo, vídeo de respaldo. **Manda sobre el alcance** | — |

### Tres riesgos de este reparto, y su mitigación

- **Pedro escribió el brief del algoritmo pero no implementa el núcleo.** Es el mayor
  riesgo de traspaso del fin de semana. Media hora el viernes, Pedro → Carlos y Antonio,
  recorriendo el brief entero. A partir de ahí el brief es la especificación y las dudas
  se resuelven contra el documento, no por chat.
- **Pedro es el cuello de botella de la cadena**: depende del núcleo y bloquea a Quirce.
  Si el viernes por la noche no hay `/score` real, que monte `/simulate` sobre un stub con
  reglas tontas y siga con el catálogo. El agente no debe descubrir su integración el
  sábado por la tarde.
- **Hugo está en front y en narrativa a la vez.** El domingo por la mañana tiene que estar
  ensayando, no programando. Quirce debe poder sostener el front en solitario desde el
  sábado por la noche.

> El despliegue tiene dos dueños y ambos desde el viernes: Antonio la API, Quirce el
> front. _"Un notebook que solo corre en vuestro portátil no cuenta"_ está en el enunciado.

#### Contrato, congelado en las 2 primeras horas

Todos mockean contra esto; nadie espera al núcleo.

```
GET  /score/{entity_id}?month=   → { score, nivel, tendencia, estado, confianza,
                                     drivers[{feature, contribución, valor, p_peer}],
                                     trayectoria[24], códigos_razón[] }
GET  /group/{group_id}           → { consolidado, filiales[] }
GET  /palancas?entity_id=        → [{ id, nombre, es_aplicable, motivo_rechazo, parametros_defecto }]
POST /simulate                   → { score_nuevo, delta_score, caja_liberada_eur,
                                     delta_bps, eur_año }
POST /action/generate            → { document_type, recipient, subject, body_text, financial_terms }
GET  /passport/{token}           → { valid, company_name, score, trajectory[], verification_hash }
GET  /alerts?desde=              → [{ entity_id, severidad, mes_detección,
                                     meses_anticipación, drivers_movidos[] }]
```

`nivel`, `tendencia` y `estado` van separados porque el brief (§6.6) los exporta por
separado y el reto no prioriza ninguno sobre otro.

### Catálogo de palancas (Patrón Strategy · OCP)

Implementado bajo interfaz polimórfica `IPalanca` (`es_aplicable`, `aplicar(Tablas, Params)`):
`PalancaReducirDSO` · `PalancaAmpliarDPO` · `PalancaRefinanciar` · `PalancaBajarUtilizacionLinea` ·
`PalancaReducirConcentracion` · `PalancaSustituirFactoring` · `PalancaRecortarOpex` · `PalancaDescuentoProntoPago`

El agente **elige y parametriza**; el número lo pone siempre `/simulate`. Tras la simulación,
habilita **ejecución en 1 clic** (`POST /action/generate`) generando el documento contractual
o memorando bancario formal para cerrar la transacción. Hace la demo determinista y operativa.

### Dos reglas de implementación que no se negocian

- **Contrafactual real, no gradiente.** Recomputar las features con el input modificado y
  volver a puntuar. Con un score aditivo esto es barato — es re-ejecutar el pipeline.
  Extrapolar desde la derivada local miente en cuanto el movimiento cruza un decil de la
  tabla de percentiles congelada.
- **Un solo algoritmo.** El score de reglas del brief es el score, también el que se
  envía al leaderboard. Si aparece una variante mejor, se sustituye entera; no se
  mantienen dos motores con dos narrativas.

### El puente a euros, en dos patas separadas

1. **Caja liberada** = Δ DSO × facturación diaria. Aritmética pura, indiscutible. Va primero.
2. **Coste de financiación**: ajustar la curva _score → tipo medio observado_. Ojo:
   `debt_schedule_config.csv` solo trae **87 tipos de 40 empresas**, insuficiente. La fuente
   es el **tipo implícito** = intereses pagados en banco (`interest_charge`) / saldo vivo,
   disponible en cientos de empresas. _"No es una suposición nuestra: es lo que pagan las
   empresas de este dataset a este nivel de score"_. Si tampoco da señal, esta pata se
   retira de la demo y queda solo la caja liberada.

---

## 6. El leaderboard: qué aplica y qué no

**Corrección respecto a versiones anteriores de este documento.** Las recetas de
competiciones tipo Amex Default (miles de features agregadas, LightGBM DART) **presuponen
una etiqueta de entrenamiento**. Si el dataset no la trae, no son aplicables y el brief
tiene razón: la entrega es el score de reglas. Decisión en la primera hora del viernes.

| Lo que revele el script de scoring | Qué hacemos |
| --- | --- |
| Hay columna objetivo en train | Sonda de Spearman feature a feature. Si 2-3 features explican >0,9, el target es una fórmula: recuperarla. Entonces sí aplica GBDT sobre agregados con ventanas 30/60/90/180/365 d |
| Solo hay feedback del leaderboard | **Reglas puras.** Ajuste de 5-6 variantes de pesos (brief §6.7). No hay más presupuesto: más iteraciones es sobreajustar a 60-80 empresas |
| No está claro | Reglas, y preguntar a los ingenieros del aula |

**Estado 18-sep, dataset en mano:** ninguno de los nueve ficheros trae columna objetivo.
Salvo que el script de scoring diga otra cosa, **estamos en la fila 2: reglas puras.** Y el
propio dato manda otras cuatro cosas que el brief no preveía: features **as-of** (en facturas
no pagadas `payment_date` es un placeholder igual al vencimiento), dirección de factura por
**signo** de `amount`, saldos históricos **reconstruidos** hacia atrás desde `balances.csv`, y
DSCR con servicio de deuda leído del **banco** (el cuadro de amortización cubre el 7 % de los
préstamos). Detalle en el informe de exploración.

En los dos casos: **validar por empresa** (`GroupKFold` por `group_id`) + corte temporal.
Y mejoras de CV por debajo de **0,005 no correlacionan** con el leaderboard — regla de
parada para Carlos.

---

## 7. Riesgos y qué NO hacer

- **No optimizar el leaderboard hasta el domingo.** Dos tercios de la nota no son la
  métrica; ellos lo dicen: _"un modelo sencillo con un producto claro encima nos interesa
  más"_. Basta estar en el tercio alto.
- **No apoyar el pitch en FIDA.** No está adoptada, y el mandato del Consejo (dic-2024)
  eliminó justo la categoría de datos de solvencia de empresas. Usar derecho vigente (§8).
- **Riesgo estratégico, y lo nombramos nosotros primero:** Tillful acabó absorbida por Nav
  (2023) y Fluidly apagada dentro de OakNorth (2023). El score de empresa **tiende a
  degenerar en herramienta del prestamista**. La decisión de diseño que lo evita: **el
  dueño del score es la empresa**, y por eso el acto 2 va antes que el acto 3.
- **Ojo con el leak.** En 3 de 7 competiciones análogas el resultado lo decidió un leak o
  un truco de métrica. Si aparece uno: usarlo para el leaderboard, **jamás para la
  narrativa**, y decirlo en voz alta.
- **No enseñar un beeswarm de SHAP** delante del jurado.
- **No decir "Embat no tiene X" sin haberlo mirado.** El jurado es Embat. Su producto ya
  calcula DSO/DPO, aging y deterioro de contrapartes; lo que no tiene es la nota unificada.
- **No contar los 24 meses como si fueran de todos.** Solo el 29 % de las empresas tiene
  historia completa; el 32 % tiene menos de 12 meses. La anticipación se mide donde se puede
  y se dice.
- **Dato sintético**: no afirmar leyes de impago del mundo real. El score mide coherencia
  interna. Decirlo antes de que lo pregunten.

---

## 8. Para el pitch

- Usar **Northbrook Foods (45→65) y Velasco Industrial (82→68)**, los nombres de su propio
  enunciado. Ellos plantearon la historia; nosotros la cerramos.
- La frase: _"Vosotros ya tenéis el dato. Lo que no tenéis es la nota — y sin nota, el
  workflow no se convierte en transacción."_
- Cerrar con el pack bancario: es donde se ve el dinero.
- Elegir Northbrook y Velasco **entre las 373 empresas con 24 meses completos**; son las
  únicas en las que la trayectoria se ve entera.
- Frase de apertura alternativa (research de Quirce, con fuente): _"El 71 % de los
  responsables financieros rechazaría una IA que no se explica, por precisa que sea. Por eso
  no hemos construido un score: hemos construido el porqué."_
- **Confirmar la duración del pitch**: el enunciado dice 2:30; el research de Quirce
  planifica 5 min.
- Diseño de la demo con el sistema visual de Embat (marino `#050b2c` + aguamarina, dos
  pesos tipográficos): el jurado la verá como suya. Tokens en el research de Quirce.

**Viento de cola regulatorio (derecho vigente español, no promesas):**

- **Ley 5/2015 + Circular BdE 6/2016**: el banco está obligado a avisar con 3 meses de
  antelación antes de cancelar o reducir financiación a una pyme, y a entregarle su
  _Información Financiera-PYME_ **con su calificación crediticia**. Gancho: _"la ley ya te
  da derecho a saber tu nota; nosotros te damos la que puedes mover"_.
- **RD 238/2026** (factura electrónica con estados de pago en 4 días): el comportamiento de
  pago entre empresas pasa a ser dato sistemático y casi en tiempo real. Es el combustible
  del grafo de contrapartes — **no es una idea de hackathon, es lo que va a haber dentro de
  18 meses.**

---

## 9. Primeros 30 minutos del viernes

1. **Traspaso del brief: Pedro → Carlos y Antonio, media hora.** A partir de ahí el
   brief es la especificación.
2. **El contrato de §5 en una pizarra**, aunque devuelva datos falsos.
3. **Las preguntas al aula**: unidad del test (empresa o grupo), qué compara el
   leaderboard, formato de salida, si el script de scoring trae etiqueta, y cuánto dura el
   pitch. La del grafo ya no hace falta: no hay.
4. **Leer el script de scoring** y resolver la tabla de §6.
5. **La exploración de §6.1 ya está hecha** (`research/informe_exploracion.md`). Se lee en
   el traspaso, no se repite.
