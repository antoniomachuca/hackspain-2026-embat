"""Detalle de empresa con episodios calculados al vuelo sobre el recorte del motor."""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_company_detail_includes_episodes():
    response = client.get("/api/companies/COMP_0005")
    assert response.status_code == 200
    data = response.json()
    assert len(data["episodios"]) >= 1
    assert data["episodio_destacado"] is not None
    ep = data["episodios"][data["episodio_destacado"]]
    for key in ("direccion", "estado", "deteccion", "estado_deteccion", "score_deteccion",
                "escaladas", "inicio_estimado", "referencia_base_health", "cambio_material",
                "criterio", "estado_confirmacion", "meses_anticipacion", "perspectiva",
                "senales", "familia", "texto"):
        assert key in ep
    assert data["trayectoria_marcas"]["deteccion"]["as_of"] == ep["deteccion"]
    assert data["perspectivas_sin_aviso"] == []
    assert data["parametros_episodios"]["material_delta"] == 10.0


def test_company_without_episodes_returns_empty():
    response = client.get("/api/companies/COMP_0001")
    assert response.status_code == 200
    data = response.json()
    assert data["episodios"] == []
    assert data["episodio_destacado"] is None
    assert data["trayectoria_marcas"]["deteccion"] is None


def test_missing_episodes_artifact_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("XRAY_RESULTS_DIR", str(tmp_path))
    response = client.get("/api/companies/COMP_0005")
    assert response.status_code == 200
    assert response.json()["episodios"] == []
