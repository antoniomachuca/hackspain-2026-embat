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
python3 algorythm/build_duckdb.py
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
| `GET` | `/api/stats` | KPIs globales: total analizado, tasa de riesgo, score medio/mediano y volumen en mora. |
| `GET` | `/api/groups` | Desglose por grupos corporativos y empresas vinculadas. |
| `GET` | `/api/companies/{id}/prevision-estructural` | 12 meses de score estructural (`alto` / `medio` / `bajo`). Proyecta cobros, gastos y deuda y aplica `calculate_scores`. No usa artefactos del benchmark. |
| `GET` | `/api/companies/{id}/forecast` | Puntos 1/3/6 meses del laboratorio (`forecasting/artifacts/forecasts.json`). No es el gráfico principal. |

---

## 4. Ejecución de la Suite de Pruebas

Para validar el 100% de los endpoints y contratos:
```bash
PYTHONPATH=. pytest backend/test_backend.py -v
```
