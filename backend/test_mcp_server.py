"""
Pruebas del servidor MCP (backend/mcp_server.py).

El cliente se conecta al servidor en memoria, sin red: lo que se comprueba es
que las herramientas existen, que aceptan identificadores cortos y, sobre todo,
que devuelven los mismos números que los endpoints REST equivalentes.
"""

import json

import pytest
from fastapi.testclient import TestClient
from mcp.client import Client

from backend.main import app

rest = TestClient(app)

HERRAMIENTAS = {
    "resumen_cartera", "buscar_empresas", "alertas",
    "ficha_empresa", "historia_empresa", "episodios_empresa", "comparables_empresa", "facturas_empresa",
    "grupo", "flujos_intragrupo",
    "que_pasaria_si", "palancas", "simular_palancas", "prevision_estructural",
}

EMPRESA = "COMP_0010"


def _datos(result):
    """structuredContent si lo hay; si no, el JSON del primer bloque de texto."""
    if result.structured_content:
        return result.structured_content
    return json.loads(result.content[0].text)


@pytest.mark.anyio
async def test_lista_las_catorce_herramientas():
    async with Client(app.state.mcp) as c:
        tools = await c.list_tools()
    nombres = {t.name for t in tools.tools}
    assert HERRAMIENTAS <= nombres, HERRAMIENTAS - nombres
    # Cada herramienta lleva descripción: es lo que lee el modelo para elegir.
    assert all(t.description for t in tools.tools)


@pytest.mark.anyio
async def test_ficha_coincide_con_rest():
    async with Client(app.state.mcp) as c:
        r = await c.call_tool("ficha_empresa", {"empresa": "10"})   # forma corta
    d = _datos(r)
    ref = rest.get(f"/api/companies/{EMPRESA}").json()
    assert d["company_id"] == EMPRESA
    assert d["score"] == ref["score"]
    assert d["state"] == ref["state"]
    assert d["waterfall"] == ref["waterfall"]
    assert d["delta_3m"] == ref["delta_3m"]


@pytest.mark.anyio
async def test_historia_recortada_pero_fiel():
    async with Client(app.state.mcp) as c:
        r = await c.call_tool("historia_empresa", {"empresa": EMPRESA, "meses": 24})
    d = _datos(r)
    ref = rest.get(f"/api/companies/{EMPRESA}/history?months=24").json()
    assert len(d["history"]) == len(ref["history"])
    assert [p["score"] for p in d["history"]] == [round(p["score"], 2) for p in ref["history"]]
    assert set(d["history"][0]) == {"mes", "score", "base_health", "state", "momentum"}


@pytest.mark.anyio
async def test_que_pasaria_si_coincide_con_rest():
    async with Client(app.state.mcp) as c:
        r = await c.call_tool("que_pasaria_si", {"empresa": EMPRESA, "inyeccion_eur": 25000})
    d = _datos(r)
    ref = rest.post("/api/whatif", json={"company_id": EMPRESA, "injection_amount": 25000}).json()
    assert d["projected_score"] == ref["projected_score"]
    assert d["recommended_product"] == ref["recommended_product"]
    assert "executive_message" not in d


@pytest.mark.anyio
async def test_resumen_cartera_y_busqueda():
    async with Client(app.state.mcp) as c:
        resumen = _datos(await c.call_tool("resumen_cartera", {"top": 3, "por_segmento": 2}))
        busqueda = _datos(await c.call_tool("buscar_empresas", {"estado": "torciendose", "limite": 5}))
    assert resumen["total_companies"] == 1286
    assert len(resumen["top_score"]) == 3
    assert {s["key"] for s in resumen["segments"]} == {"APOSTAR", "VIGILAR", "ACOMPANAR"}
    assert len(busqueda["items"]) <= 5
    assert all(i["state"] == "TORCIENDOSE" for i in busqueda["items"])


@pytest.mark.anyio
async def test_empresa_inexistente_devuelve_error_legible():
    async with Client(app.state.mcp) as c:
        r = await c.call_tool("ficha_empresa", {"empresa": "COMP_9999"})
    d = _datos(r)
    assert d["status"] == 404
    assert "COMP_9999" in d["error"]


def test_mcp_montado_en_la_api():
    """El endpoint existe y responde al protocolo (initialize por HTTP sin sesión)."""
    with TestClient(app) as c:      # con lifespan: arranca el gestor de sesiones
        r = c.post(
            "/mcp/",
            headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "test", "version": "0"}}},
        )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["serverInfo"]["name"] == "X-Ray · Embat"
