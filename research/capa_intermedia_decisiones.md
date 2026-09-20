# Simulador de mejoras · Guía de decisiones (lenguaje llano)

**Para:** Pedro · **Fecha:** 2026-09-19 · **Rama:** `feat/capa-intermedia-mejoras`  
**Qué es este documento:** no es código. Es la hoja de decisiones *antes* de implementar. Está escrito para que lo pueda leer alguien que no programa.  
**Base técnica:** `research/capa_intermedia_mejoras.md` (§12–§13). Aquí no se inventan palancas nuevas; se explica qué significa lo que ya hay y **qué tienes que elegir**.

Al final hay un **cuestionario**. Tú respondes; con eso bajamos a implementar.

---

## 0. La metáfora de los tres ejes (todo el producto cabe aquí)

Imagina que el score es la **nota del colegio** de la empresa. El motor (Carlos/Antonio) ya sabe poner la nota mirando los movimientos del banco.

Tu capa intermedia es el **entrenador**: no inventa la nota; propone *entrenamientos* (palancas), simula qué pasaría, y ordena las propuestas.

Eso se parte en **tres ejes**:

| Eje | Pregunta de 15 años | Estado hoy |
| :---: | :--- | :--- |
| **1. Acción** | ¿Qué entrenamientos existen y cuándo se pueden hacer? | Bastante cerrado: catálogo + “solo si la empresa tiene el objeto” |
| **2. Modelado** | ¿Cómo fingimos el entrenamiento en los datos **sin mentir**? | **Aquí está el trabajo duro** (descuentos, acuerdos, costes) |
| **3. Búsqueda** | ¿Cuáles probamos primero y cuándo paramos? | A medias: hay rejilla y ranking, pero faltan reglas de “usar y tirar” vs “fijo” |

Si te pierdes, vuelve a esta tabla. Todo lo demás es detalle.

---

## 1. Eje 1 · Qué palancas son accionables (casi cerrado)

### 1.1 Qué es una “palanca”

Una palanca = una acción concreta que un CFO podría intentar:

- “Cobrar antes a estos clientes”
- “Recortar sueldos/utilities un poco”
- “Refinanciar para pagar menos cuota”
- “Pagar más tarde a proveedores”
- etc.

No es “sube el score”. Es un **acto del mundo real** que nosotros traducimos a números.

### 1.2 Cuántas hay (sin marearte)

Hay **más de tres** (las tres del pitch son solo el demo). En el catálogo de producto hay del orden de **~12–14 acciones con nombre**, construidas sobre **~9 tipos de cambio en los datos** (mutadores). Ejemplos:

| Nombre amigable | ¿Siempre posible? |
| :--- | :--- |
| Adelantar cobros | Solo si hay facturas de clientes pendientes |
| Descuento pronto pago | Igual + aceptas bajar un % del cobro |
| Recortar opex (salary/utility) | Solo si se ven esos gastos |
| Refinanciar / bajar intereses / leasing | Solo si hay servicio de deuda en el banco |
| Ampliar DPO (pagar más tarde) | Solo si hay facturas a proveedores |
| Confirming | Solo si la empresa tiene producto confirming |
| Línea (bajar uso / amortizar / disponer) | Solo si hay línea de crédito |
| Factoring → línea | Solo si hay factoring (pocas empresas) |
| Concentración de clientes | Solo si se ve el mix de clientes |
| Vender inversiones | Solo si hay inversión con saldo |
| Bajar devoluciones | Solo si hay muchos refunds |

**Regla de oro (ya decidida):** que una palanca solo aplique al 1,5 % de empresas **no** la mata. En esa ficha se ofrece; en las demás, `es_aplicable = false` con motivo. Como un menú: el plato de pescado existe aunque no todos lo pidan.

### 1.3 Dos familias (importante)

No todas las palancas son “hacer la empresa más sana”.

| Familia | Significado | Ejemplos |
| :--- | :--- | :--- |
| **Salud** | Mejora (o pretende mejorar) la nota de salud | Cobros, opex, refinanciar |
| **Circulante** | Mueve **caja en el tiempo** (timing), no necesariamente solidez | Pagar más tarde (DPO), confirming, disponer línea |

El motor a veces **premia** el circulante (porque “este mes salió menos dinero” parece liquidez). Un tesorero **no** llama a eso salud. Por eso hay **dos listas** en pantalla: sugerencias de salud vs opciones de caja. Mezclarlas y ordenar solo por “cuánto sube la nota” es hacer trampas.

### 1.4 Decisión del eje 1 (casi no hay)

**D1. ¿Congelamos el catálogo actual como “v1 producto” y no añadimos más nombres hasta después de la demo?**

| Opción | Pros | Contras |
| :--- | :--- | :--- |
| **A. Sí, congelar** | Menos superficie; implementable | Te puedes quedar corto en el pitch de “producto completo” |
| **B. Congelar núcleo + extras opcionales** | Núcleo = cobros/opex/refi (+ dto); extras con gate | Más código |
| **C. Seguir inventando palancas** | Creatividad | Diluye el tiempo; el eje 2 aún no está sólido |

**Crítica al modelo actual:** el catálogo es ancho en el papel, pero **el modelado (eje 2) de la mayoría aún es “esbozo”**. Tener 14 nombres sin reglas de coste es peor que 5 bien modelados.

**Recomendación de research (no obligatoria):** **B**.

---

## 2. Eje 2 · Cómo se modelizan en el dataset (el corazón)

### 2.1 Qué significa “modelizar” (con 15 años)

El dataset es un **diario de la empresa**: facturas, movimientos, deudas.

Simular = **hacer una fotocopia del diario**, cambiar algunas líneas *como si* hubiera pasado la acción, y volver a calcular la nota.

Ejemplo cobros:

1. Hay una factura de 10.000 € que el cliente aún no ha pagado.
2. La palanca dice: “cobra 15 días antes”.
3. En la fotocopia: esa factura deja de estar pendiente **y** aparece un cobro de 10.000 € (o 9.800 € si hay descuento del 2 %) en el último mes del extracto.
4. Se recalcula el score con esa fotocopia.
5. La diferencia = `delta_score` (ΔS).

Si no mueves el cobro en el banco y solo “bajas el DSO en un Excel”, el motor **no se entera**. Por eso “reducir DSO” de verdad es **adelantar cobros en los datos**.

### 2.2 La regla de honestidad (la más importante)

> **Nadie te hace un favor gratis.**

| Acción | En la vida real | En el simulador, si eres honesto |
| :--- | :--- | :--- |
| Cobrar antes | El cliente pide **descuento** (o pierdes margen / relación) | O bien cobras igual (poco realista) o cobras **menos** (descuento) |
| Pagar más tarde | El proveedor te cobra **más**, te quita descuento, o te corta suministro | No puedes solo “mover el pago” y decir “estoy más sano” |
| Confirming | El banco te cobra **prima/fee** | No puedes borrar el gasto al proveedor y ya |
| Refinanciar | Hay **comisión**, nuevo tipo, a veces carencia | No puedes bajar la cuota sin oferta escrita |
| Recortar opex | Menos gasto recurrente (pero riesgo operativo) | Solo salary/utility, no impuestos |

Si modelas el “gratis”, el score **sube** y el jurado (Embat) te destroza: *“esto no es tesorería, es magia”*.

### 2.3 El problema de la simetría DSO ↔ DPO (tu duda)

Lo que te han dicho es justo:

- **Cobrar antes gratis** suena falso → por eso existe (o debería existir siempre) el **descuento**.
- **Pagar más tarde gratis** también es falso → pero en el research antiguo a veces se trataba peor el DPO “como salud” y se dejaba más suave el cobro.

Eso es **asimetría de evidencia / de honestidad**, no de matemáticas:

| Cara | Acción | ¿Gratis en la vida? | ¿Cómo lo teníamos? | ¿Problema? |
| :--- | :--- | :--- | :--- | :--- |
| Cobros (DSO↓) | Cliente paga antes | Casi nunca | Id `descuento_pronto_pago` **o** `#1` sin tasa | `#1` sin tasa = el caso “gratis” |
| Pagos (DPO↑) | Tú pagas después | Casi nunca | Circulante + etiqueta | Aún se puede modelar **sin coste** |

**No es que DPO “valga” y DSO no.** Es que:

1. El motor **premia** retrasar pagos (parece más liquidez) → peligro de maquillaje.
2. Por eso DPO va a la lista **circulante**, no a “sugerencias de salud”.
3. Pero si el circulante tampoco lleva **coste**, sigue siendo un poco de magia… solo que no engorda el ranking de salud.

#### Decisiones de modelado DSO/DPO

**D2. Adelantar cobros sin descuento (`adelantar_cobros`, tasa = 0): ¿lo permitimos?**

| Opción | Qué implica | Pros | Contras |
| :--- | :--- | :--- | :--- |
| **A. Prohibir** | Solo existe cobro adelantado **con** descuento | Máxima honestidad | Pierdes el acto “cobré sin coste” (a veces real: presión comercial, contrato, grupo) |
| **B. Permitir pero etiquetar** | `#1` = “acuerdo sin descuento monetario” + supuesto en pantalla | Flexible | El jurado puede decir “gratis” |
| **C. Permitir solo con supuesto tipado** | Tipos: `grupo_intragrupo` / `presión_comercial` / `contrato_ya_firmado` / `descuento` | Honesto y rico | Más UI y más reglas |

**D3. Ampliar DPO: ¿qué coste mínimo exigimos?**

| Opción | Modelado | Pros | Contras |
| :--- | :--- | :--- | :--- |
| **A. Solo timing + etiqueta circulante** (status quo) | Mueves el pago; no tocas importe | Simple; ya no ordena por ΔS | Sigue siendo “gratis” en euros |
| **B. Coste explícito** | Al alargar, pierdes descuento de pronto pago de proveedor **o** pagas un recargo % | Simétrico a DSO | Hay que inventar la tasa (no está en el CSV) |
| **C. Solo con “acuerdo supuesto” tipado** | Como D2-C: sin número, pero tipo de acuerdo obligatorio | Menos magia que A | Sigue sin euro de coste |
| **D. Fuera del producto** | No se simula DPO | Cero riesgo de maquillaje | Pierdes un acto muy Embat (circulante) |

**Crítica fuerte:** si eliges D2-B (cobros gratis) y D3-A (DPO gratis), **sigues siendo asimétrico a favor de “timing mágico”**. La simetría honesta más limpia es: **D2-A o D2-C** + **D3-B o D3-C**.

### 2.4 Confirming (mismo espíritu)

Confirming ≠ “pago más tarde”. Es: **el banco paga al proveedor hoy; tú le debes al banco después + fee**.

Modelar mal = borrar el gasto (parece DPO) → el score sube por artefacto.  
Modelar bien = **no tocar** el pago al proveedor en el banco; añadir fee (y cuota si cae en el mes); la “caja que no salió” es un euro de circulante, **no** un +ΔS de salud (con la caja del motor apagada, ΔS de caja ni siquiera existe).

**D4. Confirming en v1: ¿entra o se deja para después?**

| Opción | Pros | Contras |
| :--- | :--- | :--- |
| **A. Entra con modelo fee (honesto)** | Producto completo; 70 empresas | Más código; fácil equivocarse |
| **B. Fuera de v1** | Menos riesgo | Menos “TMS real” |
| **C. Solo panel circulante con supuesto, sin tocar score** | Barato | Poco wow |

### 2.5 Cómo se escribe cada palanca en la fotocopia (mapa mental)

Piensa “¿qué lápiz uso en el diario?”:

| Palanca | Lápiz en los datos | Coste que debería aparecer |
| :--- | :--- | :--- |
| Adelantar cobros | Factura pendiente ↓ + cobro en el mes | 0 o descuento |
| Descuento pronto pago | Igual + cobro **menor** | % descuento (supuesto) |
| Recortar opex | Gastos salary/utility ↓ | Ninguno monetario inmediato (coste = riesgo operativo, narrativo) |
| Refinanciar | Cuota/interés recurrente ↓ | Comisión + nuevo tipo (oferta) |
| Ampliar DPO | Pagos a proveedor más tarde | ¿Recargo / pérdida de dto? ← **D3** |
| Confirming | Fee (+ deuda); **no** borrar pago | Prima |
| Línea / amortizar / disponer | Hoy: **solo euros en pantalla**, no cambian la nota | Interés / caja |
| Factoring→línea | Quitar cobro “fácil” del factoring + coste | Coste factoring vs línea |
| Concentración | Cambiar **quién** te compra (mix), no el número HHI a mano | Coste comercial (narrativo) |

### 2.6 Críticas al modelado “actual” (el del research)

1. **Demasiadas palancas con coste “supuesto” y pocas con coste obligatorio.** El jurado nota el patrón.
2. **El contrato simula solo el último mes** (“si agosto hubiera sido así”). Eso es honesto como *foto*, pero **malo** para acciones recurrentes (opex): un recorte de opex de verdad dura muchos meses; nosotros solo lo pintamos en uno → la nota se mueve poco y el momentum no se enciende.
3. **Caja del motor apagada:** varias palancas “de salud” de línea **no mueven la nota**. Están en el catálogo, pero `delta_score = null`. Eso confunde (siguiente sección).
4. **Evidencia desigual** (te lo explico en §5): a unas palancas les exigimos sonda + cobertura + coste; a otras les bastó “suena a Embat”.

---

## 3. Eje 3 · Qué probar primero, rejilla, ΔS, y cuándo parar

### 3.1 ¿Qué es `delta_score` (ΔS)? (simple)

1. Calculas la nota **antes** → por ejemplo 65.
2. Aplicas la fotocopia de la palanca.
3. Calculas la nota **después** → por ejemplo 68.
4. **ΔS = 68 − 65 = +3.**

No es una fórmula mágica aparte. Es **volver a pasar el mismo motor**.

Si la palanca no toca nada que el motor lea (ej. solo mueves “utilización” en un Excel y la caja está apagada), entonces:

- o no hay cambio → ΔS = 0  
- o **decidimos no mentir** → `delta_score = null` y solo mostramos euros.

**Eso es lo de “palancas de salud con ΔS nulo”:** no es que sean “de salud falsa”. Es que **hoy el motor no puede verlas**, así que no inventamos un +5. Mostramos “esto liberaría X € / bajaría Y de dispuesto” en el panel de circulante/tesorería, no como “tu nota sube”.

### 3.2 ¿Qué es la “rejilla”? (simple)

Imagina que no puedes probar “cualquier número de días” (1, 2, 3… 100) porque serían miles de simulaciones.

Entonces fijas **pocos botones**:

| Palanca | Botones de la rejilla (propuesta actual) | Analogía |
| :--- | :--- | :--- |
| Cobros | 7 / 15 / **30** días antes | Tres mandos: suave / medio / fuerte |
| Opex | 5 % / **10 %** menos | Dos mandos |
| Refi | 20 % / **40 %** menos cuota | Dos mandos |

Eso es la rejilla: **un menú discreto de intensidades**, no un optimizador continuo (no hay “gradiente” porque el motor tiene saltos y puertas).

Para una empresa concreta:

1. Miras qué palancas son aplicables (eje 1).
2. Por cada una, pruebas los botones de la rejilla (eje 3).
3. Cada botón = una simulación = un ΔS y/o unos euros.
4. Ordenas (salud por ΔS; circulante por euros).
5. Paras (reglas abajo).

**Ejemplo numérico (cobros):**  
Empresa con mucho pendiente. Pruebas 7, 15 y 30 días. Sales:

- 7 d → ΔS +0,8 · caja 76 k€  
- 15 d → ΔS +1,2 · caja 164 k€  
- 30 d → ΔS +1,4 · caja 328 k€  

Ojo: con el contrato de **un solo mes**, el 30 días **no** enciende “momentum” (hace falta persistir ≥2 meses). Sube un poco el nivel, no la trayectoria. Por eso no digas “cambio de régimen” con un botón de 30 días.

### 3.3 Usar-y-tirar vs fijo (tu intuición: correctísima)

Aquí hay un agujero real del modelo actual.

| Tipo | Idea | Ejemplos | Qué pasa en un solo mes |
| :--- | :--- | :--- | :--- |
| **Usar y tirar (one-shot / stock)** | Un euro de timing: lo adelantas una vez | Cobrar facturas ya emitidas; pagar más tarde **estas** facturas; vender una inversión | Bien representado en “último mes” |
| **Fijo / recurrente (flow)** | Cambias el régimen hacia delante | Recortar opex cada mes; nueva cuota de refi; nuevo comportamiento de cobro | **Mal** representado si solo mutas un mes: subestima el valor |

Analogía:  
- Usar y tirar = **adelantar la paga de este mes**.  
- Fijo = **subirte el sueldo todos los meses**.

Si ambos se simulan igual (solo agosto), el opex parece “poco potente” y el cobro puntual parece “el rey”, aunque a 12 meses el opex gane.

#### Decisiones one-shot vs recurrente

**D5. ¿Cómo distinguimos en producto?**

| Opción | Qué haces | Pros | Contras |
| :--- | :--- | :--- | :--- |
| **A. Solo etiqueta** | Campo `horizonte: one_shot \| recurrente` en UI | Barato | El número ΔS sigue siendo injusto para recurrentes |
| **B. Dos modos de simulación** | One-shot = mes 23; recurrente = aplicar el cambio a los **últimos 3 meses** (W3) con flag explícito “retrospectivo W3” | ΔS más justo para opex/refi | Reescribe más pasado (hay que etiquetarlo; ya lo vetamos como default) |
| **C. Score en un mes + “euros a 12 meses” aparte** | ΔS one-shot; para recurrentes inventas `eur_año` / impacto anual **sin** fingir ΔS multi-mes | Honesto con el motor actual | `eur_año` de opex es supuesto |
| **D. Inventar meses futuros** | Proyectar oct–dic | Ideal en teoría | El motor **no tiene** cola; otro algoritmo; vetado |

**Crítica:** el research congeló “contrafactual de corte = solo mes 23” por honestidad con el motor. Eso **choca** con opex/refi. Hay que elegir D5 conscientemente; no es un detalle.

**D6. ¿Cómo prioriza el agente one-shot vs recurrente?**

| Opción | Regla | Pros | Contras |
| :--- | :--- | :--- | :--- |
| **A. Primero recurrentes** | Opex/refi antes que cobros | Mejor historia de “cambio estructural” | Pueden mover poco el ΔS de 1 mes → parecen peores |
| **B. Primero one-shot** | Cobros primero | ΔS visible; demo WOW | Sesgo anti-estructural |
| **C. Por driver, luego tipo** | Si cae L por cobros → cobros; si quema opex → opex; empatados: recurrente gana a igual ΔS | Alineado a B10.1 | Hay que implementar la regla |
| **D. Dos rankings** | Lista “impacto inmediato” y “impacto estructural” | Claro para el CFO | Más UI |

### 3.4 Orden de búsqueda (qué lanzar primero)

Propuesta operativa (aún decidible):

```text
1. Filtrar aplicables (eje 1)
2. Separar salud vs circulante
3. Dentro de salud, anclar al driver que está mal (liquidez / cobros / deuda)
4. Probar rejilla de las 1–3 palancas ancladas
5. Circulante: solo si el usuario pide “caja”, o como panel secundario
6. Parar
```

**D7. Política de parada**

| Opción | Parar cuando… | Pros | Contras |
| :--- | :--- | :--- | :--- |
| **A. Top-k** | Tienes 3 sugerencias de salud ordenadas | Simple, demo | Puede gastar sims de más |
| **B. Umbral ΔS** | La siguiente mejora &lt; 0,5 pts | Ahorra | 0,5 es arbitrario |
| **C. Presupuesto de sims** | Máx. N simulaciones por empresa (ej. 12) | Acota latencia | Puede quedarse corto |
| **D. A+C** | Top-3 o N sims, lo que ocurra antes | Práctico | Hay que fijar N |

**Recomendación de research:** **D** con N≈12–15 (3 palancas × 3–5 botones) y top-3 en UI.

### 3.5 Rejilla: ¿está bien la de 7/15/30?

Es una **hipótesis**, no ciencia. Anclada a “DSO típico ~70 días”.

**D8. Rejilla de cobros**

| Opción | Rejilla | Crítica |
| :--- | :--- | :--- |
| **A. 7/15/30** (actual) | Fácil de explicar | 30 d en 1 mes no es “régimen” |
| **B. 7/15 solo** | Más honesta con 1 mes | Menos wow de euros |
| **C. % del pendiente** (10/25/50 %) | Mejor si DSO es raro | Menos intuitivo en días |
| **D. Por factura concreta** (top clientes) | Muy Embat / FactorWOW | Más ingeniería |

**D9. Rejilla opex / refi:** ¿5/10 y 20/40 se quedan?

Misma lógica: son botones, no óptimos. Puedes bajar a un solo botón por palanca en la demo.

---

## 4. “Estándares de evidencia desiguales” (qué significa, en cristiano)

Te lo han dicho en jerga. Significa:

> **No pedimos la misma prueba a todas las palancas.**

Ejemplos del propio research:

| Palanca | Qué exigimos | ¿Es justo? |
| :--- | :--- | :--- |
| Alisar calendario | Sonda numérica → ΔS &lt;1 pt → **fuera** | Estricto |
| Factoring | n=19 → **entra** con gate | Permisivo en cobertura |
| DPO | Etiqueta circulante, a veces sin coste | Permisivo en honestidad |
| Adelantar sin descuento | Aún permitido como `#1` | Permisivo en “gratis” |
| Caja/línea | ΔS null porque no tocamos la fórmula | Estricto (bien) |
| Confirming | Modelo fee exigente | Estricto |

“Evidencia desigual” = **regla distinta según el humor del documento**, no según un estándar escrito.

### Cómo arreglarlo (decisión)

**D10. Estándar mínimo para que una palanca entre en v1**

Propón (elige / modifica):

Una palanca entra en v1 solo si cumple **todos**:

1. **Objeto** en el dataset (gate A) con conteo publicado.  
2. **Mutación escrita** (qué campos cambian) en una frase.  
3. **Coste o supuesto tipado** obligatorio (nada “gratis silencioso”), **salvo** opex (coste = riesgo operativo declarado).  
4. **Familia** salud/circulante asignada.  
5. **Al menos una de:** (i) mueve un input que el motor ya lee → ΔS definido, o (ii) declara `delta_score=null` y solo euros.  
6. **Prohibido** entrar solo por “Embat vive de esto” sin 1–5.

| Opción | Pros | Contras |
| :--- | :--- | :--- |
| **A. Adoptar este estándar y recortar v1** | Coherencia; menos ataques del jurado | Menos nombres en el menú |
| **B. Dos velocidades** | Core con estándar A; lab con disclaimer | Complejidad |
| **C. Ignorar y seguir** | Rápido | Evidencia desigual sigue |

---

## 5. Cómo encajan ΔS nulo, rejilla y familias (dibujo mental)

```text
                    ¿La empresa tiene el objeto?
                              │
                    sí        │        no → no aparece / es_aplicable=false
                              ▼
                    ¿Qué familia es?
                     /         \
              SALUD             CIRCULANTE
                │                     │
     ¿El motor ve el cambio?     Ordenar por EUROS
           /        \            (ΔS no ordena;
          sí        no            puede ser null)
           │         │
      probar REJILLA  mostrar euros
      calcular ΔS     delta_score = null
      ordenar por ΔS
```

**Palancas “de salud” con ΔS null** = rama “no” del medio: están en el menú de producto, pero **hoy** solo cuentan una historia en euros (línea, inversiones) hasta que el núcleo encienda caja de verdad (y eso reescalaría notas: decisión de producto, no un cable silencioso).

---

## 6. Críticas globales al modelo actual (para que elijas con los ojos abiertos)

1. **Eje 1 fuerte, eje 2 flojo.** Sabemos *qué* botones hay; no hemos cerrado *qué coste lleva cada botón*.  
2. **Un mes para todo.** Castiga lo recurrente; favorece el one-shot.  
3. **Simetría DSO/DPO incompleta.** El cobro “gratis” y el pago “gratis” no están tratados con la misma dureza.  
4. **Dos pistas arreglan el ranking, no el modelado.** Sacan el DPO del podio de salud; no inventan el coste del proveedor.  
5. **Rejilla arbitraria pero útil.** Está bien como MVP de búsqueda; no la vendas como óptimo.  
6. **Catálogo ancho vs demo de 2:30.** Si implementas las 14, no llegas; si solo 3, el “producto completo” es humo. Hay que elegir un **core**.  
7. **Caja apagada.** Honesto con el motor; confuso en el catálogo (“salud” que no mueve S).

---

## 7. Qué propongo como “mapa de implementación” (sujeto a tus respuestas)

Orden sugerido **después** de que contestes el cuestionario:

1. Congelar **core v1** (nombres + costes).  
2. Implementar mutadores del core (cobros±dto, opex, refi; DPO si D3 lo permite).  
3. Rejilla + presupuesto de sims + top-3.  
4. Dos listas UI (salud / circulante).  
5. Extras (confirming, factoring, línea en euros) solo si sobra tiempo.  
6. Caja en score: **no** en este hackathon salvo decisión explícita con Antonio/Carlos.

---

## 8. Cuestionario · lo que necesito que me digas

Responde con letra (A/B/C…) y, si quieres, una frase. Con eso implementamos.

### Eje 1 · Acción
- **D1** Catálogo v1: ¿A congelar / B core+extras / C seguir ampliando?

### Eje 2 · Modelado
- **D2** Cobros sin descuento: ¿A prohibir / B permitir etiquetado / C solo con tipo de acuerdo?
- **D3** Coste de DPO: ¿A solo timing / B coste € / C acuerdo tipado / D fuera?
- **D4** Confirming v1: ¿A entra fee / B fuera / C solo circulante narrativo?

### Eje 3 · Búsqueda
- **D5** One-shot vs recurrente: ¿A etiqueta / B sim W3 para recurrentes / C euros anuales aparte / D futuro inventado?
- **D6** Prioridad: ¿A recurrentes primero / B one-shot primero / C por driver / D dos rankings?
- **D7** Parada: ¿A top-3 / B umbral ΔS / C presupuesto N / D A+C? (si D, ¿qué N?)
- **D8** Rejilla cobros: ¿A 7/15/30 / B 7/15 / C % pendiente / D por cliente?
- **D9** ¿Dejamos 5/10 opex y 20/40 refi o los simplificamos a un botón?

### Estándar
- **D10** ¿Adoptamos el estándar mínimo de §4 (A), dos velocidades (B), o seguimos (C)?

### Extra (si quieres cerrar ya)
- **D11** Core obligatorio de implementación (lista los ids). Propuesta por defecto:  
  `adelantar_cobros`, `descuento_pronto_pago`, `recortar_opex`, `refinanciar`, y (si D3≠D) `ampliar_dpo` en circulante.
- **D12** ¿La demo WOW sigue siendo solo cobros → euros en `COMP_0031`, o quieres enseñar también opex/refi sí o sí?

---

## 9. Glosario exprés

| Palabra | Significado llano |
| :--- | :--- |
| **Score / S** | La nota 0–100 de salud |
| **ΔS / delta_score** | Cuánto sube o baja la nota tras la fotocopia |
| **Palanca** | Un entrenamiento / acción concreta |
| **Mutador** | El “lápiz” técnico que cambia el diario |
| **Rejilla** | Los pocos botones de intensidad (7/15/30…) |
| **One-shot** | Efecto de una vez (usar y tirar) |
| **Recurrente** | Efecto que se mantiene mes a mes |
| **Circulante** | Dinero atrapado en plazos de cobro/pago |
| **es_aplicable** | “En esta empresa se puede / no se puede” |
| **Contrafactual de corte** | “¿Y si el último mes del extracto hubiera sido así?” |

---

Cuando respondas el cuestionario (aunque sea a medias), el siguiente paso es: **congelar las elecciones en este mismo archivo** y bajar a código del core.

---

## 10. Decisiones congeladas (Pedro · 2026-09-19) + respuestas a tus dudas

### 10.0 Tabla de veredictos

| Id | Tu elección | Qué significa en una frase |
| :--- | :--- | :--- |
| **D1** | **A** | Catálogo v1 congelado; si hace falta algo, se añade después. |
| **D2** | **C** | Cobrar antes **solo** con tipo de acuerdo; y hay que **proponer el número** (descuento u otro coste). |
| **D3** | **C** | Pagar más tarde **solo** con tipo de acuerdo; y hay que **proponer el número** (qué paga de más / qué pierde). |
| **D4** | **A** | Confirming entra con modelo fee honesto. |
| **D5** | **C** | ΔS = un mes; lo recurrente se cuenta aparte en **euros a 12 meses** (supuesto etiquetado). |
| **D6** | **D** | Dos rankings: impacto inmediato vs impacto estructural. |
| **D7** | **D** (ampliado) | Presupuesto alto de sims + top generoso por ranking; buscar intensidad “buena”, no solo 2 botones. |
| **D8** | **A + clientes opcionales** | Magnitud en días 7/15/30; `clientes[]` si hay AR. |
| **D9** | **5/10 % opex · 20/40 % refi** | Dos botones suave/fuerte. |
| **D10** | **A** | Estándar mínimo de evidencia para *modelar* cada palanca (no para borrarlas del menú). |
| **D11** | **Catálogo completo (~13–14)** | Se implementan todas las del catálogo congelado; gates `es_aplicable` por empresa. |
| **D12** | **Producto todo · demo después** | El producto trae el catálogo entero. Qué se enseña en el pitch WOW se decide más tarde. |

---

### 10.1 Tus decisiones vs las críticas de §2.6

| Crítica §2.6 | ¿Tus decisiones la arreglan? | Qué queda |
| :--- | :--- | :--- |
| **1. Demasiadas palancas con coste supuesto flojo** | **Sí, bastante.** D2C+D3C+D10A obligan tipo de acuerdo **y** número propuesto. Ya no vale “gratis silencioso”. | Hay que **inventar un método** para el número (abajo). Eso es trabajo, no magia. |
| **2. Un mes para todo (castiga lo fijo)** | **Parcial.** D5C no reescribe 3 meses; añade una **segunda cifra** (euros/año) para recurrentes. | El ΔS de opex seguirá viéndose “pequeño”. El ranking estructural (D6D) existe precisamente para no enterrar el opex. |
| **3. Simetría DSO/DPO** | **Sí, de diseño.** Las dos caras exigen acuerdo tipado + número. | Simetría de *reglas*; los *números* pueden diferir (cliente ≠ proveedor). |
| **4. Dos pistas ≠ modelado** | **Arreglado en modelado** (D2/D3), no solo en ranking. | — |
| **5–7** (rejilla, catálogo, caja) | D1A+D10A ayudan al catálogo; caja sigue apagada. | Línea: ver §10.3. |

#### ¿Se puede estudiar el cambio a largo plazo de lo fijo sin mucho lío?

**Sí, hay un camino barato (encaja con D5C)** y uno caro.

| Camino | Qué es | Lío | Honestidad |
| :--- | :--- | :--- | :--- |
| **Barato = D5C** | Simulas opex/refi **un mes** → ΔS chico. Además: `impacto_anual_eur ≈ 12 × Δgasto_mensual` (o × Δinterés). Etiqueta: *extrapolación lineal, no score a 12 meses*. | Bajo | Media: el euro anual es claro; no finge trayectoria |
| **Medio** | Misma fotocopia aplicada a **3 meses** solo para recurrentes, flag `retrospectivo_W3`, ΔS separado del default | Medio | Hay que decir “reescribimos el pasado reciente” |
| **Caro** | Inventar meses futuros | Alto | Vetado: el motor no tiene cola |

**Recomendación:** quédate en el **barato**. Con D6D enseñas:

- Ranking **inmediato:** ordenado por ΔS (one-shots brillan).  
- Ranking **estructural:** ordenado por `impacto_anual_eur` (opex/refi brillan), y el ΔS de 1 mes va de *acompaño*, no de juez.

Eso soluciona la crítica 2 **sin** reabrir el contrato de corte.

---

### 10.2 D2C + D3C · Cómo proponemos el número (la solución concreta)

Quieres: no solo “hay acuerdo”, sino **“te propongo pagar / descontar X a cambio de mover Y días”**. Eso es el producto.

#### Idea madre (igual en cobros y en pagos)

El dinero tiene un **alquiler**. Adelantar o retrasar N días vale, como mínimo, algo parecido a:

```text
alquiler ≈ importe × (tipo_mensual) × (días / 30)
```

Si no conocemos el tipo de la empresa, usamos un **tipo de referencia del dataset** (mediana de tipos del cuadro ~3 % anual ≈ 0,25 % al mes) o el tipo implícito de *esa* empresa si paga `interest_charge`.

Eso no es “el descuento comercial real”; es el **suelo económico**: por debajo, alguien está regalando dinero.

#### Cobros antes (D2C) · menú de tipos de acuerdo + número

Cada sugerencia lleva:

```text
tipo_acuerdo ∈ {
  descuento_pronto_pago,      # cliente acepta cobrar menos
  acuerdo_grupo,              # misma group_id / supuesto intragrupo
  presion_comercial,          # supuesto narrativo; coste = 0 € pero flagged
  contrato_ya_firmado         # supuesto; coste = 0 € pero flagged
}
```

**Solo `descuento_pronto_pago` inventa un %.** Los otros tres permiten tasa 0 pero **obligan** el tipo en pantalla (no es el `#1` mudo de antes).

**Cómo salen los botones de descuento** (propuesta v1):

1. Eliges intensidad de días (rejilla, §10.5).  
2. Calculas el **suelo**:
   ```text
   suelo_% ≈ tipo_ref_anual × (días / 365)
   ```
   Ejemplo: 3 % anual × 15/365 ≈ **0,12 %** del importe (muy poco).  
   En comercio real los descuentos son mayores (1/2/3 %) porque incluyen margen negociador, no solo el alquiler del dinero.
3. Por eso la rejilla de **descuento** no es el suelo, sino **anclas de mercado + suelo**:

| Botón | % descuento | Cuándo usarlo |
| :--- | ---: | :--- |
| Mínimo | `max(suelo, 0.5 %)` | “Lo más barato defendible” |
| Típico | `2 %` | Estándar tipo 2/10 net 30 |
| Agresivo | `3 %` | Solo si el ΔS/caja aún compensa tras el haircut |

4. Simulas cada par `(días, %)` → ves **caja neta** = pending adelantado × (1−%) y ΔS.  
5. Eliges el par que mejor cumple: mucho impacto **y** % no ridículo (regla de parada abajo).

**Crítica:** el 2 % es cultura financiera, no el CSV. Hay que etiquetarlo: *“ancla comercial habitual; no está en el dataset”*. El suelo sí puede salir del tipo del dataset.

**Si `tipo_acuerdo ≠ descuento`:** coste € = 0, pero `warnings` incluye el tipo; el agente **no** lo pone primero en salud salvo que no haya alternativa con descuento aplicable.

#### Pagos más tarde (D3C) · simétrico

```text
tipo_acuerdo ∈ {
  perder_descuento_proveedor,  # dejabas de pagar pronto y pierdes un %
  recargo_proveedor,           # te cobran un % / interés de demora
  acuerdo_negociado,           # supuesto; coste tipado obligatorio (aunque sea 0 + flag)
  confirming_en_su_lugar       # redirige a palanca confirming (D4A)
}
```

**Número propuesto:**

1. Misma lógica de suelo con días.  
2. Anclas: perder dto típico de proveedor **2 %**, o recargo **1–2 %**.  
3. En la fotocopia: o bien el pago se retrasa **y** el importe sale mayor (recargo), o el “ahorro” de caja se reduce por el dto perdido (coste oportunidad).  
4. Familia **circulante**: ordena por **caja neta** (euros liberados − coste), nunca por ΔS.

#### Regla de oro de “factible”

No basta el máximo ΔS. Para cada candidato:

```text
score_utilidad = impacto − λ × coste_relativo
```

Con `coste_relativo = descuento%` o `recargo%`, y λ elegido para que un 3 % no gane siempre a un 0,5 % salvo que el impacto sea brutal.

En v1, más simple y auditable:

1. Genera candidatos (días × % ancla).  
2. Tira los que dejen **caja neta ≤ 0** (pagas el dto y no ganas timing útil).  
3. Tira los que exijan % &gt; 3 % sin tipo `agresivo` explícito.  
4. Ordena salud por ΔS; circulante por caja neta.  
5. En cada ranking, marca el de **mejor ratio** `ΔS / %coste` o `caja_neta / %coste` como “recomendado”.

---

### 10.3 Línea / amortizar / disponer · qué es “euros en pantalla” y cómo sirven

#### Qué significa “euros en pantalla” (con 15 años)

El motor **no mira** el saldo de la cuenta ni el “cuánto tienes dispuesto de la línea” para poner la nota (hoy). Solo mira flujos: cobros, gastos, cuotas.

Entonces, si dices “amortiza 50.000 € de la línea”:

- En la vida real: baja la deuda y baja la caja.  
- En nuestro score hoy: **casi no se entera**, salvo que también bajes los **intereses** que salen cada mes.

“Euros en pantalla” = te mostramos la **aritmética del tesorero** sin fingir que la nota cambió:

| Campo | Ejemplo |
| :--- | :--- |
| `euros_movidos` | −50.000 € de caja / −50.000 € de dispuesto |
| `ahorro_interes_anual_eur` | si pagabas ~3 % → ~1.500 €/año |
| `delta_score` | **null** |
| `aviso` | *“Esto no mueve el score hasta que el motor vea caja; el valor es tesorería e intereses.”* |

No es un adorno inútil: es exactamente lo que un CFO mira en Embat (límites, dispuesto, coste).

#### Cómo hacer que **sirvan** (tres niveles)

| Nivel | Qué haces | ¿Mueve ΔS? | Esfuerzo |
| :--- | :--- | :--- | :--- |
| **1. Solo euros** (mínimo, ya decidido con caja off) | Panel circulante/tesorería: dispuesto, holgura, ahorro de interés estimado | No | Bajo |
| **2. Bajar interés recurrente** | Amortizar/desponer **también** reduce `interest_charge` futuro (o H) → eso **sí** ve el motor (pilar D) | Sí, un poco | Medio · **recomendado v1** |
| **3. Encender caja en el score** | Camino C del research: bump de versión, reescala 1.267 empresas | Sí, mucho | Alto · no en el hackathon salvo pacto |

**Propuesta concreta v1 para línea:**

- `disponer_linea` → solo euros + fee/interés (circulante).  
- `bajar_utilizacion` / `amortizar_linea_con_caja` → euros **y**, si hay `interest_charge` observado, simular **bajada proporcional de H** (mutador M3 acoplado). Así dejan de ser “null forever” y entran al ranking estructural por `ahorro_interes_anual` + ΔS pequeño.

**Crítica:** acoplar H es un supuesto (“al bajar el dispuesto, el interés cae ya”). Etiquétalo. Mejor eso que un botón muerto.

---

### 10.4 Búsqueda · D7 ampliado (intensidad + factibilidad)

No pienses solo “palanca sí/no”. Piensa **(palanca, intensidad, coste)**.

Espacio de búsqueda v1 (ejemplo cobros):

```text
días ∈ {7, 15, 30}           # o la rejilla que fijemos en D8
%dto ∈ {mínimo, 2%, 3%}      # solo si tipo = descuento
tipo_acuerdo ∈ {descuento, grupo, …}
```

Eso son del orden de **3 × 3 × 1 ≈ 9 sims** por palanca de cobros, no 3. Con opex/refi/DPO/confirming, un presupuesto de **40–80 sims por empresa** sigue siendo barato si cada sim es “recompute de un panel ya en memoria” (milisegundos–pocos segundos, no minutos).

**Parada propuesta (sustituye top-3 rígido):**

1. Presupuesto **N = 60** sims/empresa (subible).  
2. Por ranking (inmediato / estructural / circulante): guarda **top-10** o “todos si hay menos de 10”.  
3. Entre el top, marca 1 **recomendado** = mejor ratio impacto/coste.  
4. No explores % &gt; 3 % ni días &gt; 30 en v1 (techo de factibilidad).

“Dar con el valor adecuado” en v1 **no** es optimización continua (prohibida por el motor a saltos). Es: **rejilla densa + ratio + techos**. Si más adelante quieres fino, se añade una pasada local (7, 10, 12, 15…) alrededor del mejor botón.

---

### 10.5 D8 y D9 · tradeoffs con mucho detalle + propuesta

#### D8 · Cómo medir “adelantar cobros”

Hay cuatro filosofías. No son detalles: cambian el *producto*.

##### Opción A · Días fijos (7 / 15 / 30)

**Qué es:** “Cobra 15 días antes”, punto.

**Encaja con:** conversación de tesorería clásica (DSO en días). FactorWOW habla de días. Embat ya piensa en DSO.

| Pros | Contras |
| :--- | :--- |
| Lo entiende cualquier CFO en 2 segundos | 30 días ≠ mismo esfuerzo en una empresa con DSO 40 que en una con DSO 200 |
| Fácil de poner en la rejilla | En contrato de **1 mes**, 30 días es “mucho timing” metido en agosto: ΔS limitado, M=0 |
| Demo limpia | No dice *a quién* (salvo que añadas clientes aparte) |

**Cuándo es la mejor:** si el producto se vende como “what-if de DSO/circulante”.

##### Opción B · Solo 7 / 15 (sin 30)

Igual que A, pero más honesta con “un solo mes”.

| Pros | Contras |
| :--- | :--- |
| Menos teatro de “mes entero adelantado” | Menos wow de euros en pantalla |
| Menos candidatos | Puede quedarse corta en empresas con DSO enorme (`COMP_0031` ~194 d) |

##### Opción C · % del pendiente (10 / 25 / 50 %)

**Qué es:** “Cobra el 25 % de lo que te deben”, da igual cuántos días.

| Pros | Contras |
| :--- | :--- |
| Escala sola con el tamaño de AR | No es el idioma DSO |
| Muy estable entre empresas | Hay que traducir a días *después* para el copy |
| Encaja con “facturas concretas” | El coste-% descuento se aplica sobre un trozo, no sobre días |

**Cuándo es la mejor:** si el acto es “elige facturas / clientes”, no “mueve el DSO”.

##### Opción D · Por cliente / factura (top K)

**Qué es:** “Estos 5 clientes; estas facturas”.

| Pros | Contras |
| :--- | :--- |
| Es el producto Embat de verdad | Más ingeniería (selección, UI) |
| El descuento se negocia con *alguien* | Rejilla de días sigue haciendo falta por debajo |
| FactorWOW ya lo sueña | Para el hackathon puede comerse el tiempo del eje 2 |

**Cuándo es la mejor:** capa de producto encima de A o C; no sustituye la magnitud, la **ancla a contrapartes**.

#### Veredicto D8 (propuesta, no dogma)

**A (7/15/30) + D ligero:**  

- Magnitud base = **días** (idioma score/DSO).  
- Selección opcional de `clientes[]` si hay ≥5 AR (si no hay lista, “todos los pendientes”).  
- En copy: “15 días · clientes X,Y · descuento 2 %”.  
- Quitar 30 de la *recomendación por defecto* si quieres ser más honesto; dejarlo como botón “agresivo”.

**Por qué no solo C:** vuestro diferencial es trayectoria + DSO + what-if en **días/euros**, no “cobra un % del stock” a secas.  
**Por qué no solo D:** D sin A no tiene intensidad; D es el *quién*, A es el *cuánto tiempo*.

#### D9 · Opex y refi

Misma pregunta: ¿cuántos botones?

| Opción | Opex | Refi | Pros | Contras |
| :--- | :--- | :--- | :--- | :--- |
| **Un botón** | 10 % | 30 % | Ultra simple | Poco margen de “factible vs agresivo” |
| **Dos (actual)** | 5 / 10 % | 20 / 40 % | Suficiente para ratio | Arbitrario |
| **Tres** | 5 / 10 / 15 % | 15 / 25 / 40 % | Mejor curva impacto/coste | Más sims (baratas) |

Con D5C, el opex se juzga sobre todo por **euros/año** (`12 × recorte_mensual`), no por ΔS. Da igual 2 o 3 botones: el ranking estructural los ordena.

#### Veredicto D9 (propuesta)

**Dos botones, no uno:** 5/10 % opex y 20/40 % refi.  
Motivo: con D6D+D7 quieres enseñar “suave vs fuerte” y el ratio. Un solo botón mata esa historia. Tres botones aportan poco si N ya es holgado.

Si el share salary∪utility es &lt;5 % de gastos, el 10 % de opex es ruido → `es_aplicable` con umbral mínimo de euros/mes.

---

### 10.6 Alcance de producto v1 (D11 + D12)

**Producto:** se implementan **todas** las palancas del catálogo congelado (~13–14 ids / facades sobre los mutadores M1–M9+), cada una con gate `es_aplicable`, familia salud/circulante, y modelado según D2C/D3C/D4A/D10A (acuerdo tipado + número donde toque; ΔS o `null` explícito).

**D1A** = no inventar *nombres nuevos* fuera de ese catálogo. No = quedarse en tres palancas.

**D10A** = cada palanca del catálogo tiene que cumplir el estándar de *cómo* se modela (objeto, mutación, coste/acuerdo, familia). Si alguna no puede aún (p. ej. falta adaptador), sigue en el menú con `es_aplicable=false` o `delta_score=null` + euros — no se borra del producto.

**Demo WOW (D12):** se elige **después** qué subset enseñar en los 2:30. Candidatos naturales: cobros+euros (`COMP_0031`); opex/refi en ranking estructural; DPO/confirming en panel circulante. No condiciona el alcance de implementación.

### 10.6bis Core técnico de implementación (orden, no recorte)

Orden de construcción sugerido (todo acaba en el producto):

1. Mutadores + API `/palancas` `/simulate` + dos rankings.  
2. Cobros + descuento (D2C) + opex + refi.  
3. DPO (D3C) + confirming (D4A).  
4. Línea (euros + H↓ acoplado) + disponer.  
5. Factoring, concentración, devoluciones, pronto-pago proveedor, leasing/interés facades.  
6. Ensayo demo: elegir el subset WOW.

---

### 10.7 Estado del cuestionario

**Cerrado.** D8/D9 aceptados por la propuesta del §10.5; D11/D12 = catálogo completo + demo después.

---

## 11. Contrato con el motor · respuestas verificadas Carlos/Antonio (2026-09-19)

Fuente canónica en repo: [`respuestas_a_pedro.md`](../docs/respuestas_a_pedro.md). Congelado aquí lo que afecta a implementación.

### 11.0 Tabla rápida

| # | Pregunta | Veredicto |
| :---: | :--- | :--- |
| 1 | Firma `calculate_scores` + nombres de salida | **Congelados** (41 claves motor + 8 de `classify_states`) |
| 2 | Panel banco | `receipts` / `expenses` / `debt_service` / `gross_receipts` / `refunds` / `quality` / `funding_gap` / `hhi` (+ caja opc. off) |
| 3 | `debt_service` | Solo `debt_repayment` + `interest_charge` (flujo, no outstanding) |
| 4 | ERP / caja este fin de semana | **Off**; `cash_known=0` en artefactos oficiales |
| 5 | Encender ERP/caja | Score **y** simulate a la vez + bump `model_version` |
| 6 | Percentiles / peers | **No**; Hill/tanh univariado |
| 7 | Cómo obtener el panel empresa | `get_company_bank_slice` / `bank_inputs.npz` — **nunca** `load_bank_panel` por HTTP |
| 8 | Mutar solo mes 23 | **OK** (`as_of=2026-09-01`) |
| 9 | Mapa AR → receipts/gross/gap | **OK**; lo hace **nuestra** capa de palancas |
| 10 | Mutar opex / DPO en expenses | **OK** (`salary`∪`utility`; `payment`/`bulk_payment`) |
| 11 | Refi = bajar `debt_service` recurrente | **OK**; one-shot repayment **no** es mejora de D |
| 12 | Línea / caja off | Euros + `delta_score=null`; amortizar puede acoplar ↓H |
| 13 | ERP histórico mes a mes | **No**; snapshot solo 2026-09-01 |
| 14 | Quién monta HTTP | Antonio FastAPI; nosotros dominio (`simulate_levers`) — Opción A |
| 15 | `model_version` | Ya existe: `7c92ba879e37066fcbb1f8e3d3974026d370eb48f5c091238f31865bdcc684a8` |
| 16 | Fuente de verdad | DuckDB lectura; `/simulate` **rescorea** on the fly (~4 ms) |
| 17 | Fixtures demo | `COMP_0176`, `COMP_0122`, `COMP_0010`, `COMP_0805`, `COMP_0153` (+ `COMP_0031` euros) |

### 11.1 Gap técnico (importante)

En `main` el endpoint actual `POST /api/whatif` (`algorithm/score_whatif.py`) **no** llama a `calculate_scores`: proyecta ΔS con una heurística de inyección sobre puntos ya guardados.

Nuestra capa **sí** debe fotocopiar el panel bancario, mutar mes 23 y llamar a `calculate_scores` (+ `classify_states`). Eso exige `engine_results/bank_inputs.npz` + `get_company_bank_slice` (prometidos; se construyen en esta rama).

### 11.2 Fórmulas canónicas que implementamos

- Cobros / dto: `receipts[:,23] += X`; `gross_receipts[:,23] += X`; `funding_gap[:,23] = max(gap - X, 0)`.
- Opex / DPO: `expenses[:,23] = max(expenses[:,23] - ahorro, 0)` (solo sobre tramos opex o AP).
- Refi: `debt_service[:,23] = max(debt_service[:,23] * (1 - pct), 0)` (cuota recurrente).
- Respuesta `/simulate`: incluir `model_version` del manifest oficial.

### 11.3 Estado

**Contrato cerrado.** Implementación en curso: `bank_inputs` → mutadores → `simulate_levers` → enganche API Opción A.

