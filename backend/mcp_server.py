"""
Servidor MCP de X-Ray: el núcleo y los datos de la cartera como herramientas.

Lo usa el asistente de la vista Embat (front/app/agente). Cada herramienta
llama a la propia API REST en proceso, por ASGI, sin pasar por la red: así el
agente ve exactamente los mismos números que la aplicación, con la misma
validación y la misma normalización de identificadores. Los resultados se
recortan aquí para no inflar el contexto del modelo.

Se monta en la FastAPI principal en /mcp (ver main.py). Transporte HTTP sin
sesión y con respuesta JSON: cada turno del agente abre un cliente nuevo.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import FastAPI
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

INSTRUCCIONES = (
    "Herramientas de X-Ray, el motor de salud financiera de Embat. Cubre 1.286 "
    "empresas (COMP_0001…COMP_1286) agrupadas en 250 grupos (GROUP_0001…) con 24 "
    "meses de historia. Todas las herramientas son de lectura o cálculo. Los "
    "identificadores admiten formas cortas: '773' y 'comp_773' valen por COMP_0773."
)

ESTADOS = "MEJORANDO, RECUPERACION, ESTABLE, BACHE, TORCIENDOSE, DETERIORO, EVALUACION_PENDIENTE"


def _r(v: Any, d: int = 2) -> Any:
    """Redondea floats; deja el resto como está."""
    return round(v, d) if isinstance(v, float) else v


def _fila_empresa(c: dict) -> dict:
    return {
        "company_id": c.get("company_id"),
        "group_id": c.get("group_id"),
        "erp": c.get("erp"),
        "score": _r(c.get("score")),
        "state": c.get("state"),
        "delta_3m": _r(c.get("delta_3m")),
        "momentum": _r(c.get("momentum"), 3),
        "state_eligible": c.get("state_eligible", True),
        **({"segment": c["segment"]} if c.get("segment") else {}),
    }


def _punto(h: dict) -> dict:
    return {
        "mes": str(h["as_of"])[:7],
        "score": _r(h["score"]),
        "base_health": _r(h.get("base_health")),
        "state": h.get("state"),
        "momentum": _r(h.get("momentum"), 3),
    }


def _drivers(ds: list | None, n: int = 3) -> list:
    return [
        {"field": d.get("field"), "delta_points": _r(d.get("delta_points")), "unit": d.get("unit")}
        for d in (ds or [])[:n]
    ]


def build_mcp(app: FastAPI) -> tuple[MCPServer, Starlette]:
    """Construye el servidor MCP sobre la API dada y devuelve (servidor, app ASGI)."""

    mcp = MCPServer(
        "X-Ray · Embat",
        instructions=INSTRUCCIONES,
        version="1.0.0",
    )

    transport = httpx.ASGITransport(app=app)

    async def _get(ruta: str, **params: Any) -> dict:
        limpio = {k: v for k, v in params.items() if v is not None}
        async with httpx.AsyncClient(transport=transport, base_url="http://xray", timeout=120) as c:
            r = await c.get(ruta, params=limpio)
        return _respuesta(r)

    async def _post(ruta: str, cuerpo: dict) -> dict:
        async with httpx.AsyncClient(transport=transport, base_url="http://xray", timeout=180) as c:
            r = await c.post(ruta, json=cuerpo)
        return _respuesta(r)

    def _respuesta(r: httpx.Response) -> dict:
        if r.status_code >= 400:
            try:
                detalle = r.json().get("detail", r.text)
            except Exception:
                detalle = r.text
            return {"error": detalle, "status": r.status_code}
        return r.json()

    # ── Cartera ──────────────────────────────────────────────────────────

    @mcp.tool(description=(
        "Resumen de toda la cartera Embat en el último corte: KPIs (score medio y mediano, "
        "clientes en mejora, en riesgo, alertas del mes), reparto por estado, histograma por "
        "tramos de diez puntos, trayectoria media de 24 meses, rankings (mejor score, más "
        "crecen, más caen) y los tres segmentos de acción: APOSTAR (sana y creciendo), VIGILAR "
        "(torciéndose o deterioro) y ACOMPANAR (bache). Úsala para preguntas globales."
    ))
    async def resumen_cartera(top: int = 5, por_segmento: int = 5) -> dict[str, Any]:
        d = await _get("/api/portfolio", top=max(1, min(top, 20)), per_segment=max(1, min(por_segmento, 20)))
        if "error" in d:
            return d
        return {
            "as_of": d["as_of"],
            "total_companies": d["total_companies"],
            "eligible_companies": d["eligible_companies"],
            "average_score": _r(d["average_score"]),
            "median_score": _r(d["median_score"]),
            "risk_companies_count": d["risk_companies_count"],
            "improving_companies_count": d["improving_companies_count"],
            "alerts_last_month": d["alerts_last_month"],
            "distribution_by_state": d["distribution_by_state"],
            "histogram": d["histogram"],
            "trajectory": [
                {"mes": str(t["as_of"])[:7], "average_score": _r(t["average_score"]), "median_score": _r(t["median_score"])}
                for t in d["trajectory"]
            ],
            "top_score": [_fila_empresa(c) for c in d["top_score"]],
            "top_growth": [_fila_empresa(c) for c in d["top_growth"]],
            "top_decline": [_fila_empresa(c) for c in d["top_decline"]],
            "segments": [
                {"key": s["key"], "label": s["label"], "action": s["action"], "count": s["count"],
                 "items": [_fila_empresa(c) for c in s["items"]]}
                for s in d["segments"]
            ],
        }

    @mcp.tool(description=(
        "Busca y filtra empresas de la cartera. Filtros opcionales: estado (" + ESTADOS + "), "
        "score mínimo y máximo, grupo (GROUP_xxxx), con_erp, texto (subcadena del identificador). "
        "ordenar_por: score, delta_3m, momentum, company_id, group_id, data_confidence_index. "
        "Devuelve como mucho 25 filas y el total que cumple el filtro."
    ))
    async def buscar_empresas(
        estado: Optional[str] = None,
        score_min: Optional[float] = None,
        score_max: Optional[float] = None,
        grupo: Optional[str] = None,
        con_erp: Optional[bool] = None,
        texto: Optional[str] = None,
        ordenar_por: str = "score",
        direccion: str = "desc",
        limite: int = 15,
    ) -> dict[str, Any]:
        d = await _get(
            "/api/companies",
            state=estado.upper() if estado else None,
            min_score=score_min, max_score=score_max,
            group_id=grupo, has_erp=con_erp, search=texto,
            order_by=ordenar_por, order_dir=direccion,
            limit=max(1, min(limite, 25)), offset=0,
        )
        if "error" in d:
            return d
        return {"total": d["total"], "items": [_fila_empresa(c) for c in d["items"]]}

    @mcp.tool(description=(
        "Feed de alertas del monitor. Filtros opcionales: severidad (ALTA, MEDIA, INFORMATIVA), "
        "estado del monitor, empresa, direccion (deterioration, improvement, neutral) y mes "
        "(YYYY-MM-DD del corte, p. ej. 2026-09-01). Cada alerta lleva sus tres factores de más peso."
    ))
    async def alertas(
        severidad: Optional[str] = None,
        estado: Optional[str] = None,
        empresa: Optional[str] = None,
        direccion: Optional[str] = None,
        mes: Optional[str] = None,
        limite: int = 15,
    ) -> dict[str, Any]:
        d = await _get(
            "/api/alerts",
            severity=severidad.upper() if severidad else None,
            state=estado.upper() if estado else None,
            company_id=empresa, direction=direccion, as_of=mes,
            limit=max(1, min(limite, 40)), offset=0,
        )
        if "error" in d:
            return d
        return {
            "total": d.get("total"),
            "items": [
                {
                    "alert_id": a["alert_id"], "company_id": a["company_id"], "group_id": a["group_id"],
                    "as_of": str(a["as_of"])[:10], "state": a["state"], "severity": a["severity"],
                    "direction": a["direction"], "score": _r(a["score"]), "delta_score": _r(a["delta_score"]),
                    "momentum": _r(a["momentum"], 3), "drivers": _drivers(a.get("drivers")),
                }
                for a in d.get("items", d.get("alerts", []))
            ],
        }

    # ── Empresa ──────────────────────────────────────────────────────────

    @mcp.tool(description=(
        "Ficha ejecutiva de una empresa en el último corte: score, estado, variación a tres "
        "meses, momentum, desglose aditivo del score (waterfall: liquidez, cobros, deuda, "
        "momentum, crecimiento, fragilidad), saldo bancario, facturas vencidas, DSO, DPO, días "
        "de caja, utilización de línea, última alerta, acción sugerida y resumen del episodio "
        "destacado. Es la primera herramienta para cualquier pregunta sobre una empresa concreta."
    ))
    async def ficha_empresa(empresa: str) -> dict[str, Any]:
        d = await _get(f"/api/companies/{empresa}")
        if "error" in d:
            return d
        eps = d.get("episodios") or []
        idx = d.get("episodio_destacado")
        destacado = eps[idx] if isinstance(idx, int) and 0 <= idx < len(eps) else None
        ultima = d.get("latest_alert")
        return {
            k: d.get(k) for k in (
                "company_id", "group_id", "currency", "country", "erp", "has_erp", "as_of",
                "score", "base_health", "state", "momentum", "delta_3m", "health_band",
                "data_confidence_index", "state_eligible", "waterfall", "total_balance",
                "overdue_invoices_count", "overdue_invoices_amount", "total_pending_amount",
                "suggested_action", "dso", "dpo", "dias_caja", "annual_revenue",
                "line_utilization", "customer_hhi", "daily_burn",
            )
        } | {
            "latest_alert": (
                {**{k: ultima[k] for k in ("as_of", "state", "severity", "direction", "score", "delta_score")},
                 "drivers": _drivers(ultima.get("drivers"))}
                if ultima else None
            ),
            "episodios_total": len(eps),
            "episodio_destacado": (
                {k: destacado.get(k) for k in (
                    "direccion", "estado", "deteccion", "cierre", "estado_deteccion", "score_deteccion",
                    "inicio_estimado", "estado_confirmacion", "meses_anticipacion", "familia", "texto",
                )}
                if destacado else None
            ),
        }

    @mcp.tool(description=(
        "Serie mensual del score de una empresa (por defecto 24 meses, hasta 48): score, salud "
        "base, estado y momentum por mes. Para trayectorias, tendencias y 'cuándo empezó'."
    ))
    async def historia_empresa(empresa: str, meses: int = 24) -> dict[str, Any]:
        d = await _get(f"/api/companies/{empresa}/history", months=max(1, min(meses, 48)))
        if "error" in d:
            return d
        return {"company_id": d["company_id"], "history": [_punto(h) for h in d["history"]]}

    @mcp.tool(description=(
        "Episodios de cambio de régimen de una empresa: cada deterioro o mejora detectado, con "
        "fecha de detección, inicio estimado, si fue bache o caída estructural (estado_confirmacion), "
        "cuántos meses se anticipó la perspectiva y las señales que lo explican. Incluye la "
        "historia de 24 meses para situarlos. Responde 'bache o caída' y 'cuándo se vio venir'."
    ))
    async def episodios_empresa(empresa: str) -> dict[str, Any]:
        ficha, hist = await _get(f"/api/companies/{empresa}"), await _get(f"/api/companies/{empresa}/history", months=24)
        if "error" in ficha:
            return ficha
        return {
            "company_id": ficha["company_id"],
            "episodios": ficha.get("episodios") or [],
            "episodio_destacado": ficha.get("episodio_destacado"),
            "perspectivas_sin_aviso": ficha.get("perspectivas_sin_aviso") or [],
            "history": [_punto(h) for h in hist.get("history", [])] if "error" not in hist else [],
        }

    @mcp.tool(description=(
        "Compara una empresa con sus pares: cuartil de tamaño al que pertenece, cuántas empresas "
        "hay en él y la mediana mensual del score del cuartil frente a la serie de la empresa."
    ))
    async def comparables_empresa(empresa: str) -> dict[str, Any]:
        peers, hist = await _get(f"/api/companies/{empresa}/peers"), await _get(f"/api/companies/{empresa}/history", months=24)
        if "error" in peers:
            return peers
        return {
            "company_id": peers["company_id"],
            "quartile": peers["quartile"], "label": peers["label"], "n_companies": peers["n_companies"],
            "peer_history": [{"mes": p["mes"], "mediana": _r(p["mediana"])} for p in peers["history"]],
            "history": [_punto(h) for h in hist.get("history", [])] if "error" not in hist else [],
        }

    @mcp.tool(description=(
        "Facturas del ERP de una empresa. estado opcional: overdue (vencidas), pending, paid. "
        "Devuelve totales de mora y pendiente y hasta 25 facturas."
    ))
    async def facturas_empresa(empresa: str, estado: Optional[str] = None, limite: int = 15) -> dict[str, Any]:
        d = await _get(f"/api/companies/{empresa}/invoices", status=estado, limit=max(1, min(limite, 25)), offset=0)
        if "error" in d:
            return d
        return {
            "company_id": d["company_id"], "total": d["total"], "overdue_count": d["overdue_count"],
            "total_pending_amount": _r(d["total_pending_amount"]),
            "invoices": [
                {k: _r(f.get(k)) for k in (
                    "invoice_id", "issue_date", "due_date", "paid_date", "total_amount",
                    "pending_amount", "status", "counterparty_id", "concept",
                )}
                for f in d["invoices"]
            ],
        }

    # ── Grupo ────────────────────────────────────────────────────────────

    @mcp.tool(description=(
        "Ficha de un grupo corporativo (GROUP_xxxx): score consolidado, penalización por contagio, "
        "mejor y peor sociedad, cuántas están en riesgo y la lista de sociedades con su score y estado."
    ))
    async def grupo(grupo: str) -> dict[str, Any]:
        d = await _get(f"/api/groups/{grupo}")
        if "error" in d:
            return d
        return {
            **{k: _r(d.get(k)) for k in (
                "group_id", "erp", "company_count", "average_score", "consolidated_score",
                "contagion_penalty", "worst_company_id", "worst_company_score", "best_company_id",
                "best_company_score", "risk_companies_count", "data_coverage_percentage",
            )},
            "companies": [_fila_empresa({**c, "group_id": d["group_id"]}) for c in d["companies"]],
        }

    @mcp.tool(description=(
        "Flujos de dinero entre sociedades de un grupo, inferidos del rastro bancario (mismo día, "
        "mismo importe, mismo grupo). Nodos con score y euros que entran y salen; aristas A→B con "
        "coincidencias, euros y última fecha."
    ))
    async def flujos_intragrupo(grupo: str, min_coincidencias: int = 2) -> dict[str, Any]:
        d = await _get(f"/api/graph/{grupo}", min_matches=max(1, min(min_coincidencias, 50)))
        if "error" in d:
            return d
        aristas = sorted(d["edges"], key=lambda e: -float(e.get("eur", 0)))[:40]
        return {
            "group_id": d["group_id"], "min_matches": d["min_matches"],
            "nodes": [
                {"company_id": n["company_id"], "score": _r(n["score"]), "state": n["state"],
                 "delta_3m": _r(n["delta_3m"]), "segment": n.get("segment"),
                 "eur_out": _r(n["eur_out"]), "eur_in": _r(n["eur_in"])}
                for n in d["nodes"]
            ],
            "edges": [
                {"source": e["source"], "target": e["target"], "matches": e["matches"],
                 "eur": _r(e["eur"]), "last_date": str(e["last_date"])[:10]}
                for e in aristas
            ],
            "edges_total": len(d["edges"]),
        }

    # ── Simulación ───────────────────────────────────────────────────────

    @mcp.tool(description=(
        "Simulador contrafactual: qué pasaría con el score de una empresa si recibe una inyección "
        "de circulante de inyeccion_eur euros. Sin importe, el motor calcula el tramo mínimo que la "
        "lleva a solvente (score ≥ 60). Devuelve score actual y proyectado, ganancia por bloque y "
        "el producto de Embat recomendado con su razonamiento."
    ))
    async def que_pasaria_si(empresa: str, inyeccion_eur: Optional[float] = None) -> dict[str, Any]:
        d = await _post("/api/whatif", {"company_id": empresa, "injection_amount": inyeccion_eur})
        if "error" in d:
            return d
        d.pop("executive_message", None)
        return {k: _r(v) for k, v in d.items()}

    @mcp.tool(description=(
        "Palancas recomendadas para subir el score de una empresa, ordenadas por ganancia: id de "
        "palanca, familia, puntos de score que aporta, caja que libera y parámetros (días, "
        "porcentaje, tipo de acuerdo). También la opción recomendada. Los ids sirven para simular_palancas."
    ))
    async def palancas(empresa: str) -> dict[str, Any]:
        d = await _get("/api/simulate/rankings", company_id=empresa)
        if "error" in d:
            return d
        campos = ("id", "familia", "label", "delta_score", "caja_liberada_eur", "eur_año", "days", "pct", "haircut", "agreement_type", "warnings")
        recorta = lambda s: {k: _r(s.get(k)) for k in campos if s.get(k) is not None}  # noqa: E731
        return {
            "company_id": d["company_id"], "as_of": d.get("as_of"), "modo": d.get("modo"), "n_sims": d.get("n_sims"),
            "sugerencias": [recorta(s) for s in (d.get("sugerencias") or [])[:8]],
            "opciones_circulante": [recorta(s) for s in (d.get("opciones_circulante") or [])[:5]],
            "recomendado": recorta(d["recomendado"]) if d.get("recomendado") else None,
        }

    @mcp.tool(description=(
        "Simula el efecto combinado de una o varias palancas sobre una empresa y devuelve el score "
        "antes y después, la caja liberada y los efectos. Cada palanca es un objeto con 'id' (de "
        "palancas o del catálogo: adelantar_cobros, reducir_dso, descuento_pronto_pago, recortar_opex, "
        "refinanciar, renegociar_interes, leasing_a_cuota_menor, ampliar_dpo, usar_confirming, "
        "ofrecer_pronto_pago_proveedor, bajar_utilizacion_linea, amortizar_linea_con_caja, "
        "disponer_linea, vender_inversiones, sustituir_factoring, reducir_concentracion, "
        "bajar_devoluciones) y parámetros opcionales: amount_eur, pct (0..1), days (7/15/30), "
        "haircut, agreement_type."
    ))
    async def simular_palancas(empresa: str, palancas: list[dict[str, Any]]) -> dict[str, Any]:
        d = await _post("/api/simulate", {"company_id": empresa, "levers": palancas})
        if "error" in d:
            return d
        return {
            "company_id": d["company_id"], "as_of": d.get("as_of"), "modo": d.get("modo"),
            "baseline": d["baseline"], "projected": d["projected"],
            "delta_score": _r(d.get("delta_score")), "caja_liberada_eur": _r(d.get("caja_liberada_eur")),
            "eur_año": _r(d.get("eur_año")), "warnings": d.get("warnings") or [],
            "levers": [{k: _r(v) for k, v in l.items() if k in ("id", "familia", "label", "amount_eur", "pct", "days", "delta_score", "caja_liberada_eur")} for l in (d.get("levers") or [])],
            "effects": (d.get("effects") or [])[:10],
        }

    @mcp.tool(description=(
        "Previsión estructural del score a 12 meses (hasta 24) en tres escenarios: alto (optimista), "
        "medio (central) y bajo (pesimista). Proyecta cobros, gastos y deuda y aplica el mismo motor "
        "de score. Incluye la historia para dibujar histórico y proyección juntos."
    ))
    async def prevision_estructural(empresa: str, meses: int = 12) -> dict[str, Any]:
        prev, hist = (
            await _get(f"/api/companies/{empresa}/prevision-estructural", meses=max(1, min(meses, 24))),
            await _get(f"/api/companies/{empresa}/history", months=24),
        )
        if "error" in prev:
            return prev
        return {
            **{k: _r(prev.get(k)) for k in ("company_id", "model", "status", "as_of", "meses", "current_score")},
            "alto": [_r(x) for x in prev.get("alto", [])],
            "medio": [_r(x) for x in prev.get("medio", [])],
            "bajo": [_r(x) for x in prev.get("bajo", [])],
            "history": [_punto(h) for h in hist.get("history", [])] if "error" not in hist else [],
        }

    asgi = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        # Corre detrás del dominio público de Railway y del proxy local de Next:
        # la protección contra DNS rebinding rechazaría esos Host.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return mcp, asgi
