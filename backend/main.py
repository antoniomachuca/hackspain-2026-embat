"""
Servicio API REST Backend Centralizado para X-Ray.

Construido con FastAPI + DuckDB (Fuente Única de Verdad).
Alimenta:
  - Frontend Next.js / React (Dashboard CFO, Ficha Ejecutiva, Simulador What-If)
  - Bot de Telegram (@XRAY_EMBA_BOT)
  - Integraciones de Tesorería B2B

Hackathon: HackSpain 2026 · Track Embat (UPM-ETSIT, Madrid).
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.calendar import calendar_fields
from backend.database import close_db_connection, get_db_connection
from backend.routes.alerts import router as alerts_router
from backend.routes.companies import router as companies_router
from backend.routes.forecasts import router as forecasts_router
from backend.routes.graph import router as graph_router
from backend.routes.stats import router as stats_router
from backend.routes.whatif import router as whatif_router
from backend.routes.simulate import router as simulate_router
from backend.routes.palancas import router as palancas_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización: verificar o abrir conexión compartida DuckDB
    con = get_db_connection()
    # El transporte HTTP del MCP necesita su gestor de sesiones vivo mientras
    # sirva la API. Se monta más abajo; aquí solo se arranca.
    async with app.state.mcp.session_manager.run():
        yield
    # Limpieza al apagar el servidor
    close_db_connection()


app = FastAPI(
    title="X-Ray API · Solvencia y Trayectorias de Caja B2B",
    description="""
    **X-Ray Backend Analítico Centralizado**  
    Fuente Única de Verdad (*Single Source of Truth*) sobre **DuckDB**.  
    
    ### Capacidades Principales:
    - **Cartera CFO (/api/companies):** Consulta y filtrado instantáneo de 1.286 empresas y 30k+ cortes mensuales.
    - **Ficha Ejecutiva (/api/companies/{id}):** Diagnóstico de solvencia, desglose Waterfall de puntos y alertas de liquidez.
    - **Serie Histórica (/api/companies/{id}/history):** Trayectoria temporal de 24 meses para Recharts.
    - **Gráfica PNG (/api/companies/{id}/chart):** Visualización vectorial renderizada en servidor.
    - **Simulador What-If (/api/whatif):** Modelado contrafactual de inyecciones de tesorería y anticipo de facturas.
    - **Feed de Alertas (/api/alerts):** Detección temprana de deterioros y riesgos de impago.
    - **KPIs Globales (/api/stats):** Métricas consolidadas de la cartera empresarial.
    - **Previsión estructural (/api/companies/{id}/prevision-estructural):** 12 meses de score en tres escenarios, proyectando cobros/gastos/deuda y aplicando el motor de score.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# -------------------------------------------------------------
# Configuración CORS (Permite localhost:3000 Next.js y orígenes de dev)
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Registro de Routers
# -------------------------------------------------------------
app.include_router(companies_router)
app.include_router(whatif_router)
app.include_router(simulate_router)
app.include_router(palancas_router)
app.include_router(alerts_router)
app.include_router(stats_router)
app.include_router(graph_router)
app.include_router(forecasts_router)

# -------------------------------------------------------------
# Servidor MCP: el núcleo como herramientas para el asistente
# -------------------------------------------------------------
from backend.mcp_server import build_mcp  # noqa: E402  (necesita la app con sus routers)

_mcp, _mcp_asgi = build_mcp(app)
app.state.mcp = _mcp
app.mount("/mcp", _mcp_asgi)


@app.get("/", tags=["General"])
def root():
    """Ruta raíz de bienvenida e índice de endpoints."""
    return JSONResponse(
        content={
            "name": "X-Ray Financial Health API",
            "hackathon": "HackSpain 2026 · Track Embat",
            "version": "1.0.0",
            "status": "online",
            "calendar": calendar_fields(),
            "docs": "/docs",
            "endpoints": {
                "companies": "/api/companies",
                "stats": "/api/stats",
                "calendar": "/api/calendar",
                "alerts": "/api/alerts",
                "whatif": "/api/whatif",
                "simulate": "/api/simulate",
                "palancas": "/api/palancas",
                "groups": "/api/groups",
                "prevision_estructural": "/api/companies/{id}/prevision-estructural",
                "health": "/api/health",
                "mcp": "/mcp",
            },
        }
    )
