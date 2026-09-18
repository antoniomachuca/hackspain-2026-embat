# Research: ChatGPT · Carlos

**Reto:** X-Ray (Embat) · HackSpain 2026 · 18–20 sep, ETSIT UPM
**Fuente:** ChatGPT (investigación de mercado + estrategia técnica)
**Recopilado por:** Carlos León
**Fecha:** 2026-09-18

---

Sí. He estado mirando el mercado actual y creo que el reto tiene bastante más profundidad de la que parece a primera vista. La forma correcta de entenderlo no es **"haz un credit score"**, sino:

> **Convertir el flujo operativo diario de una empresa en una estimación continua de su estado financiero, su dirección y su riesgo futuro; explicar por qué cambia y, después, convertir esa señal en decisiones accionables.**

Es casi un problema de **observabilidad financiera**: los movimientos bancarios, facturas, deuda y comportamiento de pago son la telemetría; el score es el "health metric"; las alertas son el monitoring; la explicación es el root-cause analysis; y el producto final son las acciones que tomas con esa información.

A fecha de **18 de septiembre de 2026**, hay productos que hacen partes muy parecidas, pero la combinación exacta que plantea Embat tiene una oportunidad bastante clara.

---

# 1. Qué problema os está poniendo realmente Embat

No quieren predecir simplemente:

> "¿Esta empresa quebrará?"

De hecho dicen explícitamente que **no va de predecir quiebras**.

Quieren estimar algo más parecido a una variable latente:

**Financial Health(t)**

que no observas directamente pero que intentas inferir a partir de:

**caja + generación de cash + cobros + pagos + deuda + financiación + concentración + comportamiento temporal.**

Y hay dos dimensiones distintas:

| Dimensión                  | Ejemplo                             |
| -------------------------- | ----------------------------------- |
| **Nivel**                  | La empresa hoy está en 68/100       |
| **Momentum / trayectoria** | Está cayendo 4 puntos por trimestre |

El dibujo de Northbrook y Velasco está hecho precisamente para que entendáis esto.

Una empresa:

**82 → 68**

y otra:

**45 → 65**

pueden acabar casi en el mismo lugar, pero representan situaciones completamente distintas.

La información importante no es únicamente:

`score_t`

sino:

`score_t + slope + persistence + acceleration`

Es decir:

**cómo está + hacia dónde va + desde cuándo + a qué velocidad.**

---

# 2. Hay una ambigüedad importante en el enunciado

Yo preguntaría esto a los ingenieros de Embat **antes de modelar demasiado**.

En una parte dicen:

> 250 empresas × 24 meses

pero después dicen:

> 1.286 empresas agrupadas en 250 grupos empresariales.

Eso cambia bastante el problema.

Porque podríais estar prediciendo:

`company_id`

o:

`group_id`

Y además un grupo puede tener hasta **24 sociedades**.

También falta algo fundamental en lo que habéis pegado: **qué es exactamente el ground truth que usa el leaderboard**.

Las preguntas que yo haría ahora mismo a Embat son:

1. **¿La unidad que se puntúa es `company_id` o `group_id`?**
2. **¿Qué target tenemos en train?** ¿Score 0–100, categoría, evento, ranking…?
3. **¿El test contiene empresas nuevas de grupos conocidos o grupos completamente nuevos?**
4. **¿Se evalúa solo septiembre de 2026 o los 24 meses?**
5. **¿Cuál es exactamente la métrica del leaderboard?**
6. **¿El objetivo representa salud actual o riesgo futuro a X meses?**
7. **Cuando piden anticipación, qué consideran exactamente "evento" o "cambio"?**

Especialmente la primera y la tercera determinan cómo debéis hacer validación. Si tenéis dos filiales del mismo holding, una en train y otra en validation, podéis conseguir un resultado artificialmente bueno.

---

# 3. Qué está haciendo Embat hoy

Esto es interesante porque permite entender por qué han elegido este reto.

Embat ya no es simplemente un dashboard de caja. Su producto público actual conecta bancos y ERPs, consolida caja, hace forecasting, conciliación, pagos, deuda y gestión de riesgo. Su web habla ya de **500+ equipos financieros**, conectividad con **15.000+ instituciones financieras** y un agente llamado TellMe. ([Embat][1])

Y lo más relevante: Embat **ya calcula DSO/DPO, analiza comportamiento real de pago, aging, exposición a contrapartes y detecta deterioros en clientes antes de que aumente el vencido**. También gestiona deuda y mete los vencimientos en la previsión de caja. ([Embat][2])

TellMe además ya ajusta previsiones según cómo pagan realmente las contrapartes, categoriza movimientos y detecta desviaciones. ([Embat][3])

Mi lectura del reto es, por tanto:

**Embat ya tiene la telemetría. Le falta convertir toda esa telemetría en una representación compacta del estado financiero de la propia empresa.**

No he encontrado públicamente en su producto actual un **"Embat Financial Health Score" unificado de la compañía** equivalente al reto.

Y eso explica bastante bien el hackathon.

---

# 4. El producto que más deberíais estudiar: Codat

Hay un competidor/análogamente importantísimo que os recomiendo estudiar porque básicamente os está enseñando qué features usar.

En enero de 2026 Codat lanzó su **Credit Model**.

Combina:

* datos bancarios,
* datos contables,
* credit score,
* cash-based P&L,
* deuda,
* cuentas a cobrar,
* cuentas a pagar,
* concentración de clientes,
* puntualidad de cobro,
* puntualidad de pago.

Y está explícitamente orientado a **underwriting de SMEs y dynamic risk monitoring**. ([Codat Docs][4])

Su documentación es todavía más útil. Su modelo calcula cosas como:

* proforma cash runway,
* riesgos y fortalezas principales,
* deuda y calendario de pagos,
* AR aging,
* AP aging,
* customer concentration,
* payment punctuality,
* supplier concentration,
* alertas por thresholds.

([Codat Docs][5])

Es probablemente **la referencia pública más parecida al problema que os ha planteado Embat**.

Pero hay una diferencia estratégica preciosa:

**Codat se lo vende principalmente al lender para evaluar al borrower.**

Embat puede construirlo desde la perspectiva contraria:

**el CFO viendo su propia empresa y actuando sobre ella.**

Eso os da una narrativa de producto bastante potente.

---

# 5. Qué existe ya alrededor de esto

El mercado se puede dividir aproximadamente así:

| Tipo                           | Ejemplos                       | Qué hacen                                                     | Diferencia con vuestro reto                                  |
| ------------------------------ | ------------------------------ | ------------------------------------------------------------- | ------------------------------------------------------------ |
| Credit bureaus                 | D&B, Creditsafe                | Credit score, failure score, payment behaviour, alertas       | Mucho dato externo y relativamente "bureau-like"             |
| Trade credit                   | Coface, Allianz Trade          | Probabilidad de impago, límites de crédito, payment behaviour | Evalúan sobre todo contrapartes                              |
| Open banking risk              | CRIF, Codat                    | Transacciones → KPIs → score → early warning                  | Muy cercano técnicamente                                     |
| Consumer cashflow underwriting | Plaid/Experian, Nova Credit    | Bank transactions → riesgo                                    | Principalmente personas/consumer                             |
| Treasury                       | Embat, Kyriba, Trovata, Agicap | Caja, forecasting, pagos, deuda                               | Normalmente no condensan todo en un health score empresarial |

Dun & Bradstreet, por ejemplo, tiene Failure Score, Delinquency Score y PAYDEX, con tendencias históricas y explicaciones; PAYDEX resume comportamiento de pagos de los últimos 12–24 meses. ([Dun & Bradstreet][6])

Coface ofrece scoring, probabilidad de impago a 12 meses, payment experience, monitoring y cambios históricos del riesgo. ([Coface][7])

CRIF ya comercializa explícitamente **dynamic KPI and score calculation**, indicadores de cash flow y liquidez y early-warning systems usando datos transaccionales de Open Banking. ([Crif][8])

Y en el lado treasury, plataformas como Kyriba ya hacen forecasting mediante IA, escenarios y stress-testing de liquidez. ([Kyriba][9])

Así que hacer simplemente:

> "un score 0–100 con un dashboard"

no sería especialmente novedoso.

---

# 6. Dónde está realmente la oportunidad

Aquí veo el hueco más interesante:

### De "visibility" a "decision intelligence"

Actualmente Embat puede decir:

> Tienes €2,1 M en caja.
> Este cliente está pagando 12 días tarde.
> Tienes €600k de deuda venciendo en 5 meses.

Vuestro producto podría decir:

> **Tu salud financiera ha caído de 78 a 67 en cuatro meses.**
>
> El 61% de la caída viene de deterioro de cobros y el 24% del incremento en utilización de líneas de crédito.
>
> Si el comportamiento actual continúa, entrarás en zona de riesgo en aproximadamente tres meses.
>
> Cobrar estas tres facturas y refinanciar este vencimiento elevaría tu buffer de liquidez de 1,7 a 2,6 meses.

Ahí ya no tienes un dashboard.

Tienes un **sistema de decisión para el CFO**.

---

# 7. Cómo construiría yo el score

Construiría primero una tabla:

```text
company_id | month | features... | target
```

Con unas ~30.000 observaciones máximas:

`1.286 × 24 = 30.864`

Eso es importante: **no tenéis un dataset enorme**.

Yo no empezaría con Transformers ni LSTMs.

Empezaría con:

**CatBoost / LightGBM / XGBoost.**

Los datos son tabulares, heterogéneos, hay missing values, interacciones no lineales y relativamente pocos sujetos.

Después probaría modelos temporales más sofisticados solamente si mejoran claramente el backtest.

---

# 8. Las seis familias de señales que creo que más importarán

Yo conceptualizaría el score así:

$$
Health_t =
f(
Liquidity,
CashGeneration,
Receivables,
Payables,
Debt,
Concentration,
Momentum
)
$$

### Liquidez

No miréis simplemente cuánto dinero tiene la empresa.

Mirad cosas como:

`cash / monthly_outflows`

Es decir, cuántos meses podría aguantar.

También:

* mínimo de caja,
* días cerca de cero,
* volatilidad,
* cash buffer,
* frecuencia con que necesita financiación.

### Generación real de caja

Separad los flujos operativos de cosas como financiación o movimientos intercompany.

Una empresa puede estar recibiendo muchísimo dinero porque:

**está pidiendo deuda.**

Eso no implica necesariamente que esté mejorando.

El indicador interesante es más parecido a:

`operating inflows - operating outflows`

y su tendencia.

---

# 9. Cobros: probablemente una de las señales más fuertes

Aquí tenéis muchísimo valor en `invoices.csv`.

Calcularía:

**DSO efectivo**

pero también:

`payment_date - due_date`

por factura.

Después:

* mediana de retraso,
* p90 del retraso,
* % pagado en plazo,
* % 30+,
* % 60+,
* % 90+,
* saldo vencido / facturación,
* evolución del retraso,
* concentración por cliente.

La literatura sobre SMEs respalda bastante esta intuición: los retrasos de cobro están asociados con mayor incertidumbre de cash flow y peores condiciones de acceso a financiación. ([ScienceDirect][10])

Y empresas como Embat, Codat, D&B, Allianz y Coface ya utilizan comportamiento real de pago como una señal fundamental de riesgo. ([Embat][11])

---

# 10. Los pagos a proveedores contienen una señal muy interesante

Aquí hay una sutileza que puede diferenciar un modelo bueno.

Si una empresa empieza a pagar proveedores más tarde:

**su caja puede mejorar temporalmente.**

Si miráis únicamente saldo bancario, parece sana.

Pero puede estar financiándose involuntariamente a costa de sus proveedores.

Por eso yo crearía algo como:

`DPO_actual - DPO_historico`

y cruzaría esa señal con liquidez.

Por ejemplo:

**caja ↓ + DPO ↑ + deuda utilizada ↑**

es muchísimo más preocupante que:

**caja ↓**

aisladamente.

Esa combinación de señales es exactamente lo que ayuda a distinguir:

**bache vs deterioro estructural.**

---

# 11. Deuda

`debt_products.csv` y `debt_schedule_config.csv` pueden ser de las mayores fuentes de señal.

Features que probaría:

**utilisation**

$$
\frac{outstanding}{granted}
$$

**debt / monthly inflows**

**intereses / operating cashflow**

**debt service / operating cashflow**

y especialmente:

**vencimientos próximos 3/6/12 meses.**

También:

* velocidad a la que aumenta la deuda,
* frecuencia de disposiciones,
* líneas casi agotadas,
* factoring creciente,
* nuevos préstamos,
* coste medio ponderado de financiación.

Una empresa que pierde caja pero tiene una línea prácticamente intacta está en una situación distinta de una empresa con la misma caja y el 98% de sus líneas utilizadas.

---

# 12. Concentración: puede ser muy predictiva

Con `counterparty` podéis calcular:

$$
HHI = \sum_i share_i^2
$$

tanto para clientes como para proveedores.

Además:

`top_customer_share`

`top_3_customer_share`

`top_supplier_share`

Y algo todavía mejor:

**dependencia de clientes + deterioro de su comportamiento de pago.**

Ejemplo:

> Tu mayor cliente representa 38% de entradas y durante los últimos tres meses ha pasado de pagar +3 días a +17 días.

Eso tiene muchísima más interpretación empresarial que un feature abstracto de ML.

---

# 13. Una idea bastante potente: reconstruir el histórico de balances

Aquí puede haber una pequeña joya en el dataset.

Solo os dan `balances.csv` a **1 de septiembre de 2026**.

Pero si:

* cada transacción está ligada a una cuenta,
* tenéis todas las transacciones del periodo,
* y el saldo final corresponde exactamente a ellas,

podéis reconstruir hacia atrás:

$$
Balance_t =
Balance_{final}
-
\sum_{k>t} Transaction_k
$$

Y por tanto obtener:

**saldo diario o mensual durante los 24 meses.**

Eso os permitiría calcular:

* daily minimum cash,
* days with low liquidity,
* average liquidity,
* cash buffer,
* drawdown desde máximos,
* runway histórico.

Validaría primero que la identidad contable cuadre, porque puede haber cuentas parciales, transacciones fuera de ventana o productos cuyo saldo no sea reconstruible.

Pero si funciona, es una fuente de features muy buena.

---

# 14. Cuidado enorme con leakage temporal

Esto es probablemente uno de los mayores peligros de la competición.

Imagina una factura:

```text
issued: 2025-01-05
due:    2025-02-05
paid:   2025-05-18
```

Cuando calculéis el score de febrero de 2025:

**no podéis utilizar que fue pagada en mayo.**

Aunque `payment_date` ya aparezca en la fila final del CSV.

Tenéis que construir cada snapshot **as-of month t**.

Exactamente igual con:

* estado final de una factura,
* outstanding final,
* reconciliation status,
* debt balance final,
* cualquier campo actualizado posteriormente.

Todo feature debería responder a:

> ¿Habría conocido Embat esta información ese día?

Si no, es leakage.

---

# 15. Otro peligro: leakage entre filiales

Si existen:

```text
Grupo ACME
 ├── ACME Spain
 ├── ACME France
 └── ACME Italy
```

y Spain está en train mientras France está en validation, probablemente estaréis viendo indirectamente el mismo negocio.

Yo haría la validación por:

**`group_id` completo.**

Algo del estilo:

`GroupKFold(group_id)`

Y, si podéis, además un backtest temporal.

La validación más dura sería aproximadamente:

> empresas de grupos nunca vistos + últimos meses.

Si vuestro sistema funciona ahí, seguramente generalizará bastante bien al test oculto.

---

# 16. Cómo resolver "bache o caída"

No intentaría resolver esto solo con smoothing.

Usaría tres conceptos:

**magnitud + persistencia + confirmación.**

Por ejemplo, una caída de caja durante un mes puede ser ruido o estacionalidad.

Pero si ocurre:

```text
cash buffer       ↓
DSO               ↑
overdue invoices  ↑
credit utilisation↑
operating CF      ↓
```

durante tres meses consecutivos, el sistema debería aumentar muchísimo su confianza.

Podríais tener:

```text
Health score: 68
Trend: ↓
Confidence deterioration: 87%
```

Y utilizar EWMA/CUSUM/change-point detection para detectar cambios de régimen.

---

# 17. Yo separaría score y momentum internamente

Aunque entreguéis un único score:

```text
68 / 100
```

internamente mantendría:

```text
Health level      68
Momentum          -11
3M forecast       61
Confidence        84%
```

Esto resuelve mucho mejor las seis preguntas de Embat.

Northbrook podría aparecer:

```text
65
↑ +12 momentum
```

y Velasco:

```text
68
↓ -14 momentum
```

A simple vista se entiende inmediatamente por qué dos scores parecidos no significan lo mismo.

---

# 18. Para la anticipación haría un segundo modelo

Esta parte puede daros bastantes puntos.

Además del modelo:

`health_t`

entrenaría algo tipo:

$$
P(health_{t+3} < health_t - X)
$$

Es decir:

> probabilidad de deterioro material durante los próximos tres meses.

Y lo mismo para mejora.

Entonces podéis demostrar:

> "Nuestro monitor señaló deterioro en marzo. El cambio material se produjo en junio. **Lead time: 3 meses**."

Las métricas del demo pueden ser:

**median lead time**

**% cambios detectados antes**

**false alerts**

Esto responde exactamente a la parte del reto sobre anticipación.

---

# 19. Para la explicación no uséis simplemente "SHAP"

Usaría SHAP por debajo.

Pero delante del usuario mostraría **conceptos financieros**.

Por ejemplo:

### 68 ↓ 6 puntos este mes

**Cobros -4,1**

Los clientes tardan 9 días más en pagar que hace seis meses.

**Deuda -2,7**

La utilización de líneas ha pasado del 61% al 79%.

**Generación de caja +1,6**

Los cobros recurrentes han aumentado un 7%.

Eso es muchísimo mejor que:

> `feature_37 = +0.134 SHAP`.

Y para responder:

> "¿por qué cambió este mes?"

compararía las contribuciones de:

`t`

contra:

`t-1`.

Eso os permite generar literalmente una waterfall:

```text
74
-4 collections
-3 debt
+2 operating cash flow
-1 concentration
-----------
68
```

Muy demo-friendly.

---

# 20. El producto que yo construiría

Creo que el producto más coherente para Embat sería algo tipo:

# **Embat X-Ray**

### Financial Health & Early Warning Copilot

No intentaría hacer un marketplace de crédito completo durante el hackathon.

El usuario sería:

**CFO / Head of Treasury / Treasury Manager de un cliente de Embat.**

La pantalla principal tendría:

**Financial Health 68/100 ↓**

**Early warning: deterioro detectado hace 2 meses**

Luego:

**por qué**

> Collections −5
> Debt pressure −3
> Cash generation +2

Después:

**qué va a pasar**

> Si continúa el comportamiento actual, health score estimado en 3 meses: 61.

Y finalmente:

**qué hacer**

> Cobrar estas cuatro facturas
> Refinanciar este vencimiento
> Disponer esta línea
> Reducir el pago anticipado a estos proveedores

Eso encaja perfectamente con la dirección actual de TellMe: Embat describe su AI como un agente que analiza datos financieros y propone o ejecuta acciones dentro del flujo de tesorería. ([Embat][12])

---

# 21. Y añadiría un "what-if" porque os puede ganar la demo

Poned tres sliders:

```text
Top customer pays +15 days
Revenue -10%
Interest rates +100 bps
```

Y recalculáis:

```text
Current health       68
Scenario health      56

Liquidity runway:
2.8 → 1.6 months
```

Ahora el score deja de ser simplemente descriptivo.

Se convierte en:

**una herramienta para tomar decisiones.**

Kyriba ya está empujando bastante el scenario planning de liquidez, lo cual confirma que este workflow tiene demanda empresarial real. ([Kyriba][9])

---

# 22. Vuestra diferenciación frente a lo que ya existe

Esta es probablemente la historia que yo contaría al jurado.

**D&B / Coface / Creditsafe**

> Nos dicen cómo nos ve el mundo exterior.

**Codat / CRIF**

> Ayudan al lender a decidir si financiarnos.

**Treasury platforms**

> Nos dicen cuánto dinero tendremos.

**Embat X-Ray**

> **Entiende nuestra salud financiera en tiempo real, detecta el cambio antes de que aparezca en las cuentas y nos dice qué hacer para corregirlo.**

Además Embat tiene algo que los credit bureaus no tienen:

**la fuente primaria de los datos.**

Ve directamente:

* bancos,
* ERP,
* facturas,
* deuda,
* pagos,
* contrapartes.

Eso puede hacer que el score sea mucho más vivo.

---

# 23. Incluso podéis convertirlo después en un "Financial Passport"

Como segunda diapositiva de expansión de producto, no como MVP.

La empresa podría decir:

> "Quiero financiación."

Y en vez de mandar:

* PDF de cuentas,
* extractos,
* Excel,
* aging,
* deuda,
* forecast,

a ocho bancos diferentes, comparte:

**Embat Financial Passport**

con:

```text
Health 81
Trend ↑
12m history
Liquidity
Debt capacity
Payment behaviour
Verified bank + ERP data
```

Y los bancos compiten por financiarla.

Eso convierte el producto B2B SaaS en:

**SaaS + embedded finance.**

Además encaja con la dirección que Embat está describiendo públicamente para Open Finance: combinar historial de pagos, deuda, liquidez y comportamiento de cobros para obtener financiación más personalizada. ([Embat][13])

Pero lo presentaría como **fase 2**, no intentaría construirlo durante el fin de semana.

---

# 24. La arquitectura conceptual que presentaría

Podéis reducir toda la solución a:

```text
BANKS ──────────┐
                │
ERP / INVOICES ─┼──→ FINANCIAL SIGNALS
                │         │
DEBT ───────────┘         ↓
                   HEALTH ENGINE
                         │
              ┌──────────┼──────────┐
              ↓          ↓          ↓
           SCORE      EXPLAIN    FORECAST
              │          │          │
              └──────────┼──────────┘
                         ↓
                   ACTION ENGINE
                         ↓
            Alert / Simulate / Execute
```

Eso cuenta mucho mejor la historia que:

> "hemos hecho un XGBoost".

---

# 25. Qué haría yo durante el hackathon

El orden sería este:

1. **Aclararía con Embat target, unidad de scoring y leaderboard.** Después construiría inmediatamente el dataset `company × month` completamente point-in-time para evitar leakage.
2. Haría un EDA específico de **cash, invoice delay, debt utilization, customer concentration y tendencia**. Nada de cien gráficas; buscar qué variables parecen explicar el target.
3. Montaría tres baselines: score simple interpretable, LightGBM/CatBoost y modelo con features temporales. Validación siempre por `group_id`.
4. Añadiría features de `1m / 3m / 6m / 12m`: nivel, slope, volatility, acceleration y percentile respecto al propio histórico.
5. Solo después metería features más sofisticadas: reconstrucción de balances, concentración, intercompany y network/counterparty behaviour.
6. Construiría explicabilidad agrupando SHAP en seis dominios financieros y calcularía específicamente **"why changed vs last month"**.
7. Entrenaría un modelo auxiliar de deterioro/mejora a 3 meses para poder demostrar anticipación.
8. Finalmente pondría todo en una demo sencilla: **timeline → explicación → early warning → what-if → acciones**.

Hay una cosa que yo evitaría: gastar la mitad del hackathon construyendo un agente LLM espectacular. **El LLM debería explicar y convertir señales en acciones; no debería ser el motor del score.**

---

## Lo que me parece más importante de toda la investigación

El reto **ya existe como categoría comercial**. Codat, CRIF, D&B, Coface, etc. demuestran que hay mercado para transformar comportamiento financiero en scoring y early warning. Codat, de hecho, está sorprendentemente cerca del dataset y del problema de Embat. ([Codat Docs][5])

Por tanto, no intentaría vender al jurado que habéis "inventado el credit scoring".

La oportunidad sería decir:

> **"Todos estos scores terminan en un informe para alguien que decide sobre la empresa. Embat ya está dentro de la empresa, viendo cada euro moverse en tiempo real. Nosotros convertimos eso en un sistema que detecta la trayectoria financiera, explica qué la está moviendo y permite al CFO actuar antes de que el problema aparezca en sus cuentas."**

Creo que esa es una interpretación bastante fuerte del track.

**Siguiente paso sugerido:** con los CSV a mano (idealmente el ZIP entero y `data_dictionary.md`) se puede ir al siguiente nivel: inspeccionar de verdad el dataset y decidir **qué features concretas sacar de cada tabla, qué leakage hay, cómo construir la tabla company-month, cómo hacer la validación y cuál sería el primer modelo para atacar el leaderboard**.

---

## Referencias

[1]: https://www.embat.io/treasury-management "All-in-One Treasury Management System | Embat"
[2]: https://www.embat.io/financial-risk-management "Financial Risk Management for Corporate Treasury | Embat"
[3]: https://www.embat.io/artificial-intelligence-finance "TellMe: Artificial Intelligence in finance | Embat"
[4]: https://docs.codat.io/updates/260107-credit-model/ "Lending: introducing Credit Model report | Codat Docs"
[5]: https://docs.codat.io/lending/premium-products/credit-model-overview "Credit model overview | Codat Docs"
[6]: https://www.dnb.co.uk/products/dnb-credit-insights.html "D&B Credit Insights"
[7]: https://biz.coface.com/businessinformation-faq "iCON by Coface - FAQ"
[8]: https://www.crif.com/business/solutions/loan-origination/open-banking-solutions/ "CRIF Open Banking Solutions"
[9]: https://www.kyriba.com/use-cases/cash-forecasting/ "AI-Powered Cash Forecasting for Precise Liquidity Insights — Kyriba"
[10]: https://www.sciencedirect.com/science/article/pii/S0264999324002530 "The impact of late payments on SMEs' access to finance — ScienceDirect"
[11]: https://www.embat.io/contactos "Gestión de contrapartes para equipos de tesorería | Embat"
[12]: https://www.embat.io/blog/ai-agents-in-finance "What AI Agents Can Do in Finance Today | Embat"
[13]: https://www.embat.io/es/blog/diferencia-open-banking-vs-open-finance "Diferencia entre Open Banking y Open Finance | Embat"
