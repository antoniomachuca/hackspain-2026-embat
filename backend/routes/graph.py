"""
Mapa de flujos intragrupo (X-Ray).

El dataset no trae quién paga a quién: los counterparty_id están anonimizados por
empresa y nunca se repiten entre dos empresas. Lo que sí se puede hacer es emparejar
una salida de A con una entrada de B, del mismo grupo, el mismo día y por el mismo
importe. Dentro del grupo eso ocurre 24 veces más que entre grupos distintos
(4,5 frente a 0,19 coincidencias por par posible), así que es señal, no casualidad.
Un par con ≥2 coincidencias tiene un 1,6 % de probabilidad de ser ruido; con ≥3, un 0,1 %.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.database import query_dicts, query_one
from backend.routes.stats import SEGMENT_SQL, normalize_group_id
from backend.schemas import (
    GraphEdge,
    GraphGroupSummary,
    GraphNode,
    GraphResponse,
    GraphSummaryResponse,
)

router = APIRouter(prefix="/api/graph", tags=["Flujos intragrupo"])

# Movimientos que pueden ser la pata de un traspaso entre sociedades. Se dejan
# fuera nóminas, impuestos, comisiones… y los importes pequeños, que son ruido.
_TX = """
    SELECT t.company_id, c.group_id, t.date, t.amount
    FROM transactions t JOIN companies c USING (company_id)
    WHERE abs(t.amount) >= 500
      AND t.category IN ('transfer', 'payment', 'collection', 'cash_settlement', '-')
"""

_EDGES = f"""
    WITH tx AS ({_TX}),
    pares AS (
        SELECT a.company_id AS origen, b.company_id AS destino, a.group_id, a.date, -a.amount AS importe
        FROM tx a
        JOIN tx b ON a.date = b.date AND a.amount = -b.amount
                 AND a.company_id <> b.company_id AND a.group_id = b.group_id
        WHERE a.amount < 0
    )
    SELECT group_id, origen, destino, count(*) AS n, sum(importe) AS eur, max(date) AS ultimo
    FROM pares
    GROUP BY group_id, origen, destino
"""


@router.get("", response_model=GraphSummaryResponse)
def get_graph_summary(min_matches: int = Query(2, ge=1, le=50), limit: int = Query(30, ge=1, le=250)):
    """Grupos con flujos internos detectados, ordenados por volumen. Para elegir qué grupo dibujar."""
    rows = query_dicts(f"""
        WITH aristas AS ({_EDGES})
        SELECT a.group_id,
               count(*) AS edges,
               count(DISTINCT a.origen) + 0 AS _o,
               (SELECT count(*) FROM companies c WHERE c.group_id = a.group_id) AS companies,
               sum(a.eur) AS eur,
               sum(a.n) AS matches,
               (SELECT round(avg(score), 1) FROM v_latest_company_scores s WHERE s.group_id = a.group_id) AS average_score,
               (SELECT min(score) FROM v_latest_company_scores s WHERE s.group_id = a.group_id) AS worst_score
        FROM aristas a
        WHERE a.n >= ?
        GROUP BY a.group_id
        ORDER BY eur DESC
        LIMIT ?;
    """, (min_matches, limit))
    total = query_one(f"""
        WITH aristas AS ({_EDGES})
        SELECT count(DISTINCT group_id) AS groups, count(*) AS edges, sum(eur) AS eur
        FROM aristas WHERE n >= ?;
    """, (min_matches,)) or {"groups": 0, "edges": 0, "eur": 0.0}
    return GraphSummaryResponse(
        min_matches=min_matches,
        groups_with_flows=int(total["groups"] or 0),
        total_edges=int(total["edges"] or 0),
        total_eur=round(float(total["eur"] or 0.0), 2),
        groups=[
            GraphGroupSummary(
                group_id=r["group_id"],
                companies=int(r["companies"]),
                edges=int(r["edges"]),
                matches=int(r["matches"]),
                eur=round(float(r["eur"]), 2),
                average_score=float(r["average_score"] or 0.0),
                worst_score=float(r["worst_score"] or 0.0),
            )
            for r in rows
        ],
    )


@router.get("/{group_id}", response_model=GraphResponse)
def get_group_graph(group_id: str, min_matches: int = Query(2, ge=1, le=50)):
    """Nodos (sociedades del grupo, con su score) y aristas (flujos inferidos A → B)."""
    gid = normalize_group_id(group_id)
    nodos = query_dicts(f"""
        SELECT company_id, score, state, health_band, state_eligible, delta_3m, {SEGMENT_SQL} AS segment
        FROM v_latest_company_scores WHERE group_id = ? ORDER BY company_id;
    """, (gid,))
    if not nodos:
        raise HTTPException(status_code=404, detail=f"Grupo '{gid}' no encontrado")

    aristas = query_dicts(f"""
        WITH aristas AS ({_EDGES})
        SELECT origen, destino, n, eur, ultimo FROM aristas
        WHERE group_id = ? AND n >= ?
        ORDER BY eur DESC;
    """, (gid, min_matches))

    salidas: dict = {}
    entradas: dict = {}
    for a in aristas:
        salidas[a["origen"]] = salidas.get(a["origen"], 0.0) + float(a["eur"])
        entradas[a["destino"]] = entradas.get(a["destino"], 0.0) + float(a["eur"])

    return GraphResponse(
        group_id=gid,
        min_matches=min_matches,
        nodes=[
            GraphNode(
                company_id=n["company_id"],
                score=round(float(n["score"]), 2),
                state=str(n["state"]),
                health_band=n.get("health_band"),
                state_eligible=bool(n["state_eligible"]),
                delta_3m=round(float(n["delta_3m"]), 2),
                segment=n.get("segment"),
                eur_out=round(salidas.get(n["company_id"], 0.0), 2),
                eur_in=round(entradas.get(n["company_id"], 0.0), 2),
            )
            for n in nodos
        ],
        edges=[
            GraphEdge(
                source=a["origen"], target=a["destino"],
                matches=int(a["n"]), eur=round(float(a["eur"]), 2), last_date=str(a["ultimo"]),
            )
            for a in aristas
        ],
    )
