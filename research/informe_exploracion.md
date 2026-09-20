# Informe de exploración del dataset (B0)

**Fecha:** 2026-09-18 · **Fuente:** los nueve ficheros de `dataset/` (2.526.598 movimientos,
897.894 facturas, 1.286 empresas, 250 grupos). Cifras calculadas, no estimadas.
Cumple RF-B0.3 y RF-B0.4 de [`REQUISITOS.md`](../docs/REQUISITOS.md).

---

## 1. Lo que decide el diseño

| Pregunta | Respuesta | Decisión que dispara |
| :--- | :--- | :--- |
| **¿Hay etiqueta / target en train?** | **No.** Ninguna columna de score, resultado ni evento en los nueve ficheros | Rama "solo feedback" de `PRODUCTO.md` §6: **score de reglas**. GBDT solo si el script de scoring revela un target (RF-B13.1) |
| **Unidad** | 1.286 `company_id` en 250 `group_id`; tamaño de grupo mediana 3, P75 7, máx 22 | Trabajar a nivel empresa; confirmar unidad del test en el aula |
| **País** | **82 % nulo**; el resto sucio (`ES`, `ESPAÑA`, `España`) | **Peer por país descartado.** Peer = cuartil de tamaño (cobros anualizados), opcionalmente × moneda EUR/otra |
| **Moneda** | EUR 89 %, GBP 3 %, USD 3 %, resto marginal | Conversión a EUR solo P2 |
| **Cruce contraparte↔empresa** | **0,0 %**. Ningún `counterparty_id` es `company_id`; ninguna contraparte aparece en ≥ 2 empresas (0,2 % en tx, 0,0 % en facturas) | **Sin grafo** (RF-B5.7 muere). Concentración solo con HHI sobre facturas |
| **Contrapartes disponibles** | Facturas: 98,7 % con contraparte. Movimientos: **9,8 %** | HHI de clientes y proveedores **desde `invoices`**, no desde banco |
| **Historia por empresa** | Mediana 18,4 meses. **415 empresas (32 %) con < 12 meses**; 10 con < 6. Solo **373 (29 %) tienen los 24 meses** | Ventana creciente desde el mes 6 es obligatoria, no opcional. Anticipación medible solo sobre las 373 completas |
| **Movimientos / semana** | Mediana 12,6 · P10 1,4 · P90 80 | Serie **mensual** |
| **Empresas con línea de crédito** | 206 (16 %) | Bloque de deuda: utilización pesa menos (regla §6.1 del brief) |

## 2. Dirección de las facturas (emitida vs recibida)

No hay columna de dirección. **El signo de `amount` la codifica**: cruzando 97.867 facturas
pagadas con su movimiento bancario (misma empresa, contraparte, importe, ±5 días), el signo
coincide en el **99,6 %**. Negativa → pago a proveedor (categorías `payment`, `utility`,
`bulk_payment`, `fee`, `tax`). Positiva → cobro de cliente.

- Mediana de empresa: solo el 28 % de sus facturas son emitidas. **67 empresas no tienen
  ninguna factura emitida** en el ERP → su cobro solo se ve por banco.
- Importe mediano: emitidas 1.214 €, recibidas 479 €.

## 3. `payment_date` no significa lo que parece — leakage confirmado

| status | n | `payment_date == due_date` | `payment_date` > 1-sep-2026 |
| :--- | ---: | ---: | ---: |
| paid | 660.299 | 52 % | 3,0 % |
| overdue | 192.556 | **96 %** | 2,8 % |
| pending | 29.717 | **98 %** | **88 %** |
| cancel | 13.699 | 81 % | 3,3 % |

En facturas no pagadas `payment_date` es un **placeholder igual al vencimiento**, no una
fecha de pago. Además: 29.089 facturas con pago anterior a la emisión, fechas con año 6913
o 5026 (5 filas), 3.958 `overdue` con vencimiento futuro.

**Regla as-of obligatoria (nuevo RF-B1):** en el mes *t*, una factura está viva si
`issuance ≤ t` y (`status ≠ paid` **o** `payment_date > t`); está vencida si además
`due < t`. `payment_date` solo se usa si `status == paid` y `issuance ≤ payment ≤ 2026-09-01`.
Sin esta regla, el DSO de febrero usa cobros de mayo.

Retraso real (solo `paid`): 33,9 % pagadas tarde, mediana 14 días, P90 91. Plazo
emisión→vencimiento mediano 11 días. Hay señal.

## 4. Saldos históricos: reconstruibles con reservas

`balances.csv` es una foto a 1-sep-2026. Reconstruyendo hacia atrás
(`saldo_t = saldo_final − Σ movimientos posteriores`) sobre 4.147 cuentas corrientes:

- Los movimientos **preceden** a la conexión del producto (mediana −36 días): el banco vuelca
  histórico al conectar. Solo el 17 % de cuentas arranca en sep-2024.
- **7,6 % de cuenta-mes** queda en negativo; **20 % de cuentas** lo tocan alguna vez. Son
  cuentas pequeñas (saldo final mediano 1.313 € vs 12.795 €) y el mínimo es ~0,7× el saldo
  final: descubiertos plausibles o movimientos faltantes, no un fallo sistemático.
- 2.808 productos con saldo y sin movimientos (préstamos, tarjetas, cuentas inactivas);
  123 con movimientos y sin saldo (1,8 % de filas).
- Solo el 68 % de cuentas corrientes tiene movimientos en ago/sep-2026.

**Decisión:** el runway se calcula sobre el saldo reconstruido **agregado por empresa**
(suma de corrientes), con marcador de calidad si alguna cuenta reconstruye en negativo.
Alimenta confianza, no riesgo.

## 5. Deuda: el cuadro de amortización no sirve, el banco sí

- **908 empresas (71 %) sin ningún producto de deuda** registrado.
- `debt_schedule_config`: **87 filas de 1.261 préstamos (7 %)**, 40 empresas. Inservible
  como denominador del DSCR.
- En cambio, los movimientos `debt_repayment` (23.044) e `interest_charge` (7.822) existen en
  **718 empresas (56 %)** — 480 de ellas sin préstamo registrado en `debt_products`.

**Decisión:** el servicio de deuda del DSCR se calcula **desde los movimientos bancarios**
(RF-B1.8 cambia de fuente). La curva score → tipo de interés (RF-B9.2) solo tiene 87 tipos
(mediana 3 %, rango 0–11 %): se enseña con su dispersión o se sustituye por tipo implícito
`interest_charge / outstanding`.

- Utilización de líneas (`outstanding/granted`, 466 líneas): mediana 0,45, **P75 0,97,
  P90 1,00**, 25 por encima de 1. Señal fuerte donde existe.

## 6. Cohorte y artefactos

- Empresas activas por mes: **439 en sep-2024 → 1.223 en mar-2026**. El volumen total de
  movimientos se multiplica ×4 por **onboarding**, no por negocio: dentro de cada empresa con
  24 meses completos el nº de movimientos es plano (ratio 1,0).
- Consecuencia: cualquier feature de "actividad" absoluta está sesgada; todo normalizado por
  empresa y por sus propios ingresos.
- Los casos Northbrook/Velasco de la demo deben salir de las **373 empresas con 24 meses**.

## 7. Calidad del dato para la capa de confianza

- `category` de movimientos: **25 % es `-`** (sin categoría). `collection` 22 %, `payment` 14 %.
- `accounting_status`: **62 % nulo**; `RECONCILIATION_COMPLETED` 21 %, `DISCARDED` 12 %.
  El "% conciliado" de la fórmula de confianza se calcula sobre los no nulos.
- `transactions.status`: 99,7 % `booked`. Descartar `pending`.
- `transfer` es el 5,9 % de movimientos; 171 préstamos `Other (customer-defined)` con pinta de
  intragrupo. Sin cruce de contrapartes, la eliminación intragrupo (RF-B1.13) solo puede ser
  **aproximada** (por categoría), y se declara así.

## 8. Tamaño de empresa (para el peer)

Cobros anualizados (`collection` + `bulk_collection` + `pos_settlement`): P10 54 k€ ·
mediana 1,66 M€ · P90 24,6 M€ · P99 614 M€. Cuatro cuartiles de ~321 empresas.
31 empresas sin cobros categorizados → peer global con etiqueta "peer limitado".

---

## Cambios que este informe fuerza en `REQUISITOS.md`

1. **RF-B2.1** peer = cuartil de tamaño (país descartado).
2. **Nuevo RF-B1** as-of point-in-time para facturas y deuda (P0). Es el hueco más grave.
3. **RF-B1.8** DSCR: denominador desde movimientos, no desde `debt_schedule_config`.
4. **RF-B1.2** runway sobre saldo reconstruido por empresa, con marcador de calidad.
5. **RF-B1.5** HHI desde `invoices`, dirección por signo de `amount`.
6. **RF-B1.1** ventana creciente desde el mes 6 pasa de "caso raro" a caso del 32 %.
7. **RF-B5.7** grafo eliminado; **RF-B1.13** intragrupo aproximado.
8. **RF-B9.2** curva score→tipo: 87 puntos, mostrar dispersión o usar tipo implícito.
9. **RF-B13.2** rama activa: reglas. GBDT solo si el script de scoring revela un target.
