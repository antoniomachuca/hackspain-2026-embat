"""HTTP palancas/simulate without building DuckDB."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.palancas import router as palancas_router
from backend.routes.simulate import router as simulate_router

app = FastAPI()
app.include_router(palancas_router)
app.include_router(simulate_router)
client = TestClient(app)


def test_get_palancas_comp_0010():
    res = client.get("/api/palancas", params={"company_id": "10"})
    assert res.status_code == 200
    data = res.json()
    assert data["company_id"] == "COMP_0010"
    ids = {p["id"] for p in data["palancas"]}
    assert "adelantar_cobros" in ids
    assert "ampliar_dpo" in ids
    cobros = next(p for p in data["palancas"] if p["id"] == "adelantar_cobros")
    assert cobros["es_aplicable"] is True
    assert "descuento_pronto_pago" not in ids
    assert "descuento_pronto_pago" in cobros["agreement_types"]
    refi = next(p for p in data["palancas"] if p["id"] == "refinanciar")
    assert refi["es_aplicable"] is False
    assert refi["motivo_rechazo"]


def test_get_palancas_unknown():
    res = client.get("/api/palancas", params={"company_id": "COMP_9999"})
    assert res.status_code == 404


def test_post_simulate_cobros():
    payload = {
        "company_id": "COMP_0010",
        "levers": [
            {"id": "adelantar_cobros", "amount_eur": 50000, "agreement_type": "presion_comercial"}
        ],
    }
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["delta_score"] > 0
    assert data["model_version"]
    assert data["modo"] == "contrafactual_de_corte"


def test_post_simulate_missing_agreement():
    payload = {"company_id": "COMP_0010", "levers": [{"id": "adelantar_cobros", "amount_eur": 1000}]}
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 422


def test_rankings_comp_0031():
    res = client.get("/api/simulate/rankings", params={"company_id": "COMP_0031"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert all(r["familia"] == "salud" for r in data["sugerencias"])
    assert all(r.get("delta_score") is None for r in data["opciones_circulante"])
    assert all(r["id"] != "descuento_pronto_pago" for r in data["sugerencias"])


def test_post_simulate_disjoint_lineas_ok():
    from algorythm.levers_objects import get_company_objects
    obj = get_company_objects("COMP_0004")
    ids = [str(inv["invoice_id"]) for inv in obj.ar_invoices if inv.get("invoice_id")][:2]
    assert len(ids) == 2
    payload = {
        "company_id": "COMP_0004",
        "levers": [{
            "id": "adelantar_cobros",
            "agreement_type": "presion_comercial",
            "lineas": [
                {"facturas": [ids[0]], "dias": 15, "tasa_descuento": 0},
                {"facturas": [ids[1]], "dias": 7, "tasa_descuento": 0.02},
            ],
        }],
    }
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 200
    assert res.json()["caja_liberada_eur"] > 0


def test_post_simulate_overlapping_lines_422():
    from algorythm.levers_objects import get_company_objects
    obj = get_company_objects("COMP_0031")
    counterparty = next(str(inv["counterparty_id"]) for inv in obj.ar_invoices if inv.get("counterparty_id"))
    payload = {
        "company_id": "COMP_0031",
        "levers": [{
            "id": "adelantar_cobros",
            "agreement_type": "presion_comercial",
            "lineas": [
                {"clientes": [counterparty], "dias": 15, "tasa_descuento": 0},
                {"clientes": [counterparty], "dias": 30, "tasa_descuento": 0.02},
            ],
        }],
    }
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 422
    assert res.json()["detail"]["error"] == "doble_conteo"
    assert res.json()["detail"]["resource_key"]
