# X-Ray Backend · DuckDB + FastAPI

Microservicio analítico centralizado y **Fuente Única de Verdad (*Single Source of Truth*)** para la plataforma **X-Ray** (HackSpain 2026 · Track Embat).

---

## 1. Arquitectura

- **Motor Analítico:** [DuckDB](https://duckdb.org/) embebido en un único archivo binario: `xray.duckdb` (modo lectura multihilo para consultas en <5 ms).
- **Servidor Web:** [FastAPI](https://fastapi.tiangolo.com/) con [Uvicorn](https://www.uvicorn.org/).
- **Validación y Contratos:** Pydantic v2.
- **Visualización:** Matplotlib en memoria (`io.BytesIO`) para trayectorias de caja en PNG.
- **Simulación Contrafactual:** Integración directa con el motor `score_whatif.py`.

---

## 2. Puesta en Marcha Rápida

### 2.1. Instalar dependencias
```bash
pip install -r requirements.txt
# O directamente:
pip install duckdb fastapi uvicorn pydantic httpx requests
```

### 2.2. Construir / Refrescar la Base de Datos DuckDB
El script ingesta los 3,5 millones de registros (transacciones, facturas, scores y alertas) en ~7 segundos:
```bash
python3 algorithm/build_duckdb.py
```

### 2.3. Arrancar el Servidor FastAPI
```bash
uvicorn backend.main:app --reload --port 8000
```

### 2.4. Documentación Interactiva Swagger / OpenAPI
Una vez arrancado el servidor, abre en tu navegador:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. Catálogo de Endpoints REST

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Estado del servicio y mapa de rutas. |
| `GET` | `/api/health` | Verificación de conectividad con DuckDB y recuento de tablas. |
| `GET` | `/api/companies` | Cartera del CFO: lista paginada y filtrable de las 1.286 empresas con score, estado, $\Delta$ 3M y desglose Waterfall. |
| `GET` | `/api/companies/{id}` | Ficha ejecutiva: diagnóstico de solvencia, desglose de puntos, saldos bancarios y facturas vencidas. |
| `GET` | `/api/companies/{id}/history` | Serie temporal de 24 meses de score, base health y componentes para renderizado en Recharts. |
| `GET` | `/api/companies/{id}/invoices` | Detalle de facturas e impagos ERP para auditar la causa raíz de la mora. |
| `GET` | `/api/companies/{id}/chart` | Imagen PNG generada en servidor con la trayectoria de 24 meses y umbrales de solvencia. |
| `POST` | `/api/whatif` | Simulador contrafactual: proyecta el impacto de una inyección de circulante o calcula el tramo óptimo mínimo. |
| `GET` | `/api/alerts` | Feed de eventos y alertas de riesgo emitidas por el monitor de solvencia. |
| `GET` | `/api/stats` | KPIs globales: total analizado, tasa de riesgo, score medio/mediano y volumen en mora. Incluye `calendar` (agosto 2026 cerrado; 1-sep es foto de 1 día). |
| `GET` | `/api/calendar` | Tres relojes del dataset: `as_of`, `last_closed_month` (2026-08-01) y `partial_month` (foto 1-sep). |
| `GET` | `/api/graph` | Grupos con flujos internos detectados (`min_matches`, `limit`), ordenados por volumen. |
| `GET` | `/api/graph/{group_id}` | Nodos (sociedades con score, € que entran/salen) y aristas (A → B: `matches`, `eur`, `last_date`) de un grupo. Flujos inferidos: mismo día, mismo importe, mismo grupo. |
| `GET` | `/api/portfolio` | Cartera Embat en una llamada: KPIs, histograma, trayectoria media 24 m, rankings (`top_score`, `top_growth`, `top_decline`, solo `state_eligible`) y segmentos `APOSTAR` / `VIGILAR` / `ACOMPANAR` (regla determinista, `SEGMENT_SQL`). Parámetros `top` y `per_segment`. |
| `GET` | `/api/groups` | Desglose por grupos corporativos y empresas vinculadas. |
| `GET` | `/api/companies/{id}/prevision-estructural` | 12 meses de score estructural (`alto` / `medio` / `bajo`). Proyecta cobros, gastos y deuda y aplica `calculate_scores`. No usa artefactos del benchmark. |
| `GET` | `/api/companies/{id}/forecast` | Puntos 1/3/6 meses del laboratorio (`forecasting/artifacts/forecasts.json`). No es el gráfico principal. |

---

## 4. Servidor MCP para el asistente

La API monta en **`/mcp/`** (con barra final) un servidor MCP (`backend/mcp_server.py`, paquete `mcp>=2.2`) con catorce herramientas de lectura y cálculo: cartera, búsqueda, alertas, ficha, historia, episodios, comparables, facturas, grupo, flujos intragrupo, what-if, palancas, simulación de palancas y previsión estructural. Cada herramienta llama a la propia API en proceso, así que devuelve los mismos números que los endpoints REST. Lo consume el asistente de la vista Embat (`front/app/agente`); es interno, no un producto en sí.

Transporte HTTP sin sesión con respuesta JSON. Para verlo con el inspector de MCP:

```bash
npx @modelcontextprotocol/inspector --transport http --server-url http://127.0.0.1:8000/mcp/
```

Pruebas: `PYTHONPATH=. pytest backend/test_mcp_server.py -v`.

## 5. Ejecución de la Suite de Pruebas

Para validar el 100% de los endpoints y contratos:
```bash
PYTHONPATH=. pytest backend/test_backend.py -v
```
