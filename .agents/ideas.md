# Propuestas y Factores WOW · HackSpain 2026 (Reto Embat)

Documento estratégico de mejoras y factores WOW para la presentación final y defensa técnica ante el jurado (ingenieros de **Embat** e inversores de **K Fund**).

---

## 1. Diagnóstico del Estado Actual del Repositorio (Calificación: 9/10)

El proyecto cuenta con una base de artesanía técnica muy superior a la media de un hackathon de 36 horas:
* **Sin cifras inventadas ni mocks:** motor de scoring analítico real en NumPy (`algorithm/score_engine.py`) procesando paneles mensuales continuos sin *lookahead bias*.
* **Fuente única de verdad analítica:** base de datos columnar DuckDB de ~400 MB (`xray.duckdb`) con más de 30.000 cortes mensuales y agregaciones instantáneas (<10 ms).
* **Backend validado y probado:** FastAPI con 20/20 tests unitarios pasando en Pytest (`backend/test_backend.py`), cubriendo endpoints de empresas, histórico, ratios de circulante (DSO, DPO), benchmark de pares sectoriales, simulaciones contrafactuales y consolidación de grupos.
* **Frontend funcional y tipado:** Next.js 16 (App Router + Tailwind CSS) con páginas activas para dashboard (`/`), ficha 360° (`/empresa/[id]`), simulador what-if (`/empresa/[id]/escenarios`), comparador (`/comparar`), grupos corporativos (`/grupos`, `/grupo/[id]`) y laboratorio de previsión (`/prevision`).
* **Cumplimiento exhaustivo de las bases del track:**
  - *Bloque 1 (Si acierta):* Score bidireccional y simétrico (premia recuperaciones y castiga deterioros con filtros de persistencia temporal).
  - *Bloque 2 (Si llega a tiempo):* Clasificador de 6 estados analíticos que discrimina ruido puntual (`BACHE`) de caída estructural (`TORCIENDOSE` / `DETERIORO`).
  - *Bloque 3 (Si vale algo):* Explicabilidad aditiva matemática exacta (Waterfall con error cero) y cuantificación de impacto en euros (€ liberados en caja y bps de coste financiero).

---

## 2. Catálogo de Propuestas WOW para Ganar el Reto

Para alcanzar el 10/10 y distanciar el proyecto de cualquier competidor durante los 2:30 minutos de pitch, se plantean 4 mejoras tácticas de alto impacto visual y técnico:

---

### Propuesta 1 · El Interruptor "Modo Bureau vs Modo X-Ray" en el Comparador (`/comparar`) ⭐⭐⭐
> **Impacto:** Gancho demoledor para los primeros 30 segundos del pitch. Ataca directamente el Bloque 1 (Trayectoria) y el caso emblemático del enunciado (la paradoja del mes 24).

#### Concepto
En la pantalla de comparador interactivo (`/comparar`), donde se contrastan **Northbrook Foods** (sube de 45 a 65) y **Velasco Industrial** (cae de 82 a 68):
* Añadir un **toggle superior destacado**:
  1. **"Modo Bureau Tradicional (Informa / Balance anual)":**
     - Oculta la serie temporal de 24 meses.
     - Muestra únicamente la "foto fija" del mes 24: Velasco tiene 68 puntos y Northbrook tiene 65 puntos.
     - *Diagnóstico tradicional:* Velasco parece más solvente y de menor riesgo crediticio.
  2. **"Modo X-Ray (Embat / Rastro continuo en tiempo real)":**
     - Al accionar el interruptor, la interfaz despliega dinámicamente las dos curvas completas de 24 meses.
     - Se resalta con un marcador visual el punto de inflexión exacto (hace 4 meses) en el que Velasco cambió a estado `TORCIENDOSE`, mientras Northbrook consolidaba su estado de `RECUPERACION`.

#### Implementación Técnica
* **Front (`front/app/comparar/split.tsx`):**
  - Variable de estado `const [viewMode, setViewMode] = useState<'bureau' | 'xray'>('bureau')`.
  - En `'bureau'`, la gráfica muestra solo el último punto ($t=24$) en formato tarjeta fija con un banner informativo: *"Foto estática de balance: información con hasta 15 meses de retraso"*.
  - En `'xray'`, animación fluida con Recharts revelando las trayectorias divergentes, el badge del estado analítico oficial y el lead time de anticipación.

#### Guion en Vivo (Pitch)
> *"Cualquier scoring tradicional mira el balance del año pasado: ahí Velasco puntúa 68 y Northbrook 65. Parece mejor riesgo Velasco. Activamos Modo X-Ray: el rastro diario de tesorería demuestra que Northbrook va a más y Velasco empezó a hundirse hace 4 meses. En la foto fija eran idénticas; en el rastro son opuestas."*

---

### Propuesta 2 · Código QR para "Dossier Bancario Móvil en Directo" ⭐⭐⭐
> **Impacto:** Elimina el escepticismo del jurado ("eso sólo corre en vuestro portátil") y aporta un cierre comercial tangible para el Bloque 3 (Producto y Artesanía).

#### Concepto
En la cabecera de la ficha de empresa (`/empresa/[id]`), incorporar una acción principal: **"Generar Dossier Bancario Compartible"**.
* Al pulsarlo, se abre un modal con un **código QR de alta definición** y un enlace público temporal.
* Durante la presentación, se invita al jurado a escanear el QR con su teléfono móvil.
* El móvil del jurado carga instantáneamente la **versión ejecutiva responsive del dossier**:
  - Score actual y estado analítico oficial.
  - Indicadores clave de caja (DSO, DPO, días de liquidez).
  - Waterfall aditivo de drivers causales.
  - **Sello de integridad y reproducibilidad:** hash criptográfico SHA-256 de la versión del algoritmo y los datos de corte, garantizando auditoría contable.

#### Implementación Técnica
* Generación del código QR mediante componente SVG ligero (ej. `qrcode.react` o generador SVG sin dependencias externas pesadas).
* Enlace en local con túnel (ngrok / localtunnel / IP de red local) o URL de despliegue en Vercel.
* Ruta dedicada o vista optimizada para móvil (`/empresa/[id]` con diseño responsive que ya está estructurado con Tailwind CSS).

#### Guion en Vivo (Pitch)
> *"El CFO no quiere mandar ocho PDFs distintos a ocho bancos cada trimestre. Escanea este QR: es el dossier financiero único de la empresa, siempre al día, auditado con hash de reproducibilidad y accesible en el móvil del analista de riesgos en 1 segundo."*

---

### Propuesta 3 · Demostración en Vivo del Monitor Proactivo (Bot de Telegram) ⭐⭐
> **Impacto:** Conquista directamente el **Bonus oficial del Bloque 2 ("Monitor que avisa solo, sin que nadie pregunte")**.

#### Concepto
El repositorio ya dispone de la infraestructura de monitorización en `algorithm/score_monitor.py` y el bot `@XRAY_EMBA_BOT` (`algorithm/score_telegram_bot.py`, `telegram_notifier.py`).
* En lugar de limitar la demo a un dashboard web pasivo, dedicar 15 segundos a enseñar una notificación real de Telegram:
  - *"🚨 ALERTA X-RAY: Velasco Industrial SL"*
  - *"Cambio de régimen detectado: ESTABLE ➔ TORCIENDOSE"*
  - *"Lead time de anticipación: 4 meses frente al balance"*
  - *"Drivers causales (Desglose exacto):"*
    - *Alargamiento de cobro (DSO): -5.2 pts*
    - *Tensión en servicio de deuda: -3.1 pts*
    - *Pérdida de momentum: -2.4 pts*

#### Implementación Técnica
* Ejecutar el bot de Telegram o invocar una simulación de disparo con `telegram_notifier.py` sobre un canal/grupo de prueba creado para la demo.
* Mostrar la pantalla del móvil o una ventana auxiliar con la notificación llegando en tiempo real.

#### Guion en Vivo (Pitch)
> *"La tesorería no se vigila abriendo dashboards: el sistema avisa solo cuando una empresa se mueve de verdad. Aquí veis la alerta que saltó en Telegram en cuanto Velasco torció el gesto, desglosando los 10 puntos de caída factor a factor."*

---

### Propuesta 4 · Exportación de "Plan de Acción Financiero en 1-Clic" (PDF / Resumen CFO) ⭐⭐
> **Impacto:** Convierte el simulador What-If en una herramienta transaccional que el director financiero puede llevar inmediatamente a un comité o entidad bancaria.

#### Concepto
En la pantalla del simulador contrafactual (`/empresa/[id]/escenarios`):
* Tras manipular los sliders de palancas operativas (adelantar cobros, renegociar con proveedores, refinanciar pólizas), la plataforma calcula el nuevo score, los puntos ganados y la **caja liberada en euros**.
* Añadir un botón visible: **"📄 Exportar Plan de Optimización para Banco / CFO"**.
* Genera una vista de impresión limpia y profesional (`@media print` estilizada) con:
  1. Diagnóstico de partida y score actual.
  2. Palancas aplicadas con su impacto individualizado (€ de liquidez y $\Delta$ puntos de score).
  3. Previsión contrafactual tras la ejecución de las medidas.

#### Implementación Técnica
* Estilos CSS específicos `@media print` en Tailwind para ocultar barras de navegación y maquetar en formato DIN A4 horizontal o vertical.
* Ejecución mediante `window.print()` nativo del navegador, sin necesidad de librerías complejas de PDF en servidor.

---

## 3. Matriz de Priorización y Esfuerzo

| Propuesta | Esfuerzo de Código | Criterio del Track Impactado | Momento en el Pitch |
| :--- | :---: | :--- | :--- |
| **1. Interruptor Modo Bureau vs X-Ray** | ~20 min | Bloque 1 (Trayectoria) & Gancho inicial | **0:00 – 0:45 (Gancho)** |
| **2. QR Dossier Móvil en Vivo** | ~25 min | Bloque 3 (Producto y Artesanía) | **1:45 – 2:15 (Cierre)** |
| **3. Notificación Telegram en Directo** | ~15 min | Bloque 2 (Bonus Monitor Autónomo) | **0:45 – 1:15 (Anticipación)** |
| **4. Exportar Plan de Acción CFO** | ~20 min | Bloque 3 (Monetización y Caso de Uso) | **1:15 – 1:45 (What-If)** |

---

## 4. Conclusión y Recomendación

La combinación del **Interruptor Modo Bureau (Propuesta 1)** en el comparador y el **Código QR del Dossier Móvil (Propuesta 2)** en la ficha de empresa garantiza un arranque y un cierre de presentación con impacto memorable para el jurado, respaldado por la arquitectura sólida ya desplegada en DuckDB y FastAPI.
