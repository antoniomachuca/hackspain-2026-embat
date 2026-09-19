"""
Suite de Pruebas Automatizadas para el Backend FastAPI + DuckDB de X-Ray.
"""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verifica que el endpoint raíz responda correctamente."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["version"] == "1.0.0"
    assert "/docs" in data["docs"]


def test_health_check():
    """Verifica el endpoint de salud y conectividad de DuckDB."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "xray.duckdb" in data["database"]
    assert data["tables_count"] >= 5


def test_get_companies_default():
    """Verifica la lista paginada de empresas por defecto."""
    response = client.get("/api/companies?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1286
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["items"]) == 10

    first = data["items"][0]
    assert "company_id" in first
    assert "score" in first
    assert "state" in first
    assert "delta_3m" in first
    assert "liquidity_points" in first
    assert "collections_points" in first


def test_get_companies_filter_group_normalizes_short_ids():
    """El filtro de empresas acepta las mismas formas de grupo que su endpoint de detalle."""
    canonical = client.get("/api/companies?group_id=GROUP_0044&limit=100").json()
    for group_id in ("44", "GROUP44"):
        response = client.get(f"/api/companies?group_id={group_id}&limit=100")
        assert response.status_code == 200
        assert response.json()["total"] == canonical["total"]
        assert [item["company_id"] for item in response.json()["items"]] == [
            item["company_id"] for item in canonical["items"]
        ]


def test_get_companies_filter_state():
    """Verifica el filtrado de empresas por estado de riesgo."""
    response = client.get("/api/companies?state=DETERIORO&limit=20")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["state"] == "DETERIORO"


def test_get_companies_filter_score_range():
    """Verifica el filtrado por rango de puntuación."""
    response = client.get("/api/companies?min_score=40&max_score=60&limit=15")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert 40.0 <= item["score"] <= 60.0


def test_get_companies_search():
    """Verifica la búsqueda por subcadena."""
    response = client.get("/api/companies?search=0010")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    found = [it["company_id"] for it in data["items"]]
    assert "COMP_0010" in found


def test_get_company_detail():
    """Verifica la ficha ejecutiva completa de una empresa."""
    response = client.get("/api/companies/COMP_0010")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "COMP_0010"
    assert "waterfall" in data
    wf = data["waterfall"]
    assert "liquidity_points" in wf
    assert "collections_points" in wf
    assert "debt_points" in wf
    assert "fragility_points" in wf
    assert data["overdue_invoices_count"] >= 0
    assert data["total_pending_amount"] >= 0


def test_get_company_detail_normalized_id():
    """Verifica la normalización de identificador: '10' -> 'COMP_0010'."""
    response = client.get("/api/companies/10")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "COMP_0010"


def test_get_company_detail_not_found():
    """Verifica el código 404 para una empresa inexistente."""
    response = client.get("/api/companies/COMP_999999")
    assert response.status_code == 404


def test_get_company_history():
    """Verifica la serie temporal histórica de 24 meses."""
    response = client.get("/api/companies/COMP_0010/history?months=12")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "COMP_0010"
    assert data["months"] == 12
    assert len(data["history"]) == 12

    # Comprobar orden cronológico ascendente
    dates = [p["as_of"] for p in data["history"]]
    assert dates == sorted(dates)
    assert all(p.get("reparto") is not None for p in data["history"])


def test_get_company_history_reparto_aligned_and_scores_untouched():
    full = client.get("/api/companies/COMP_0010/history?months=24")
    assert full.status_code == 200
    data = full.json()
    assert data["months"] == 24
    history = data["history"]
    assert history[0]["as_of"].startswith("2024-10")
    assert history[-1]["as_of"].startswith("2026-09")
    assert history[-1]["score"] == pytest.approx(45.56, abs=0.05)
    assert history[0]["reparto"]["drivers"] == []
    assert history[0]["reparto"]["pct_tendencia"] == 0
    assert all(point["reparto"] is not None for point in history)
    assert any(point["reparto"]["drivers"] for point in history)

    cropped = client.get("/api/companies/COMP_0010/history?months=12").json()
    assert cropped["history"][0]["as_of"] == history[12]["as_of"]
    assert cropped["history"][0]["score"] == history[12]["score"]
    assert cropped["history"][0]["reparto"] == history[12]["reparto"]
    assert cropped["history"][0]["reparto"] != history[0]["reparto"]


def test_get_company_peers():
    """Verifica el benchmark de pares y mediana mensual de cuartil."""
    response = client.get("/api/companies/COMP_0010/peers")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "COMP_0010"
    assert data["quartile"] in (1, 2, 3, 4)
    assert data["n_companies"] > 0
    assert len(data["history"]) == 24
    assert data["history"][0]["mes"] == "2024-10"
    assert data["history"][-1]["mes"] == "2026-09"
    assert all("mediana" in p for p in data["history"])



def test_get_company_invoices():
    """Verifica el detalle de facturación ERP."""
    response = client.get("/api/companies/COMP_0010/invoices?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "COMP_0010"
    assert len(data["invoices"]) <= 5
    if data["invoices"]:
        inv = data["invoices"][0]
        assert "invoice_id" in inv
        assert "total_amount" in inv
        assert "pending_amount" in inv


def test_get_company_chart_png():
    """Verifica la generación de la imagen PNG de trayectoria."""
    response = client.get("/api/companies/COMP_0010/chart")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # Cabecera mágica de archivo PNG (\x89PNG\r\n\x1a\n)
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(response.content) > 10000


def test_whatif_simulation_with_amount():
    """Verifica la simulación contrafactual con monto explícito."""
    payload = {"company_id": "COMP_0010", "injection_amount": 35000.0}
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "COMP_0010"
    assert data["injection_amount"] == 35000.0
    assert data["delta_score"] > 0.0
    assert data["projected_score"] > data["current_score"]
    assert "recommended_product" in data
    assert "executive_message" in data


def test_whatif_simulation_auto_optimal():
    """Verifica la simulación con cálculo automático de inyección óptima."""
    payload = {"company_id": "COMP_0010"}
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_optimal_computed"] is True
    assert data["injection_amount"] > 0
    assert data["projected_score"] >= 55.0


def test_get_alerts():
    """Verifica el listado de alertas de riesgo."""
    response = client.get("/api/alerts?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["alerts"]) <= 10
    first = data["alerts"][0]
    assert "alert_id" in first
    assert "severity" in first
    assert "drivers" in first


def test_get_alerts_filter_severity():
    """Verifica el filtrado de alertas por severidad ALTA."""
    response = client.get("/api/alerts?severity=ALTA&limit=5")
    assert response.status_code == 200
    data = response.json()
    for a in data["alerts"]:
        assert a["severity"] == "ALTA"


def test_get_stats():
    """Verifica los KPIs globales de cartera ejecutiva."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_companies"] == 1286
    assert data["latest_as_of"] == "2026-09-01"
    assert "distribution_by_state" in data
    assert data["risk_companies_count"] > 0
    assert data["risk_percentage"] > 0.0
    assert data["total_transactions_count"] > 2000000
    assert data["total_invoices_count"] > 800000
    assert data["total_overdue_volume"] > 0


def test_get_groups():
    """Verifica el catálogo de grupos corporativos."""
    response = client.get("/api/groups")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["groups"]) > 0
    first = data["groups"][0]
    assert "group_id" in first
    assert "company_count" in first
    assert "average_score" in first
