"""Telegram presentation for palancas / simulate. Domain stays in levers_*."""

from __future__ import annotations

from typing import Any

from algorithm.levers_gates import evaluate_catalog
from algorithm.levers_search import recommend_levers


def palancas_keyboard(company_id: str) -> dict[str, Any]:
    cid = company_id.strip().upper()
    return {
        "inline_keyboard": [
            [
                {"text": "⚙️ Palancas", "callback_data": f"cb_pal:{cid}"},
                {"text": "🧪 Rankings", "callback_data": f"cb_rank:{cid}"},
            ],
            [
                {"text": "💡 What-If clásico", "callback_data": f"cb_whatif:{cid}"},
            ],
        ]
    }


def format_palancas_html(company_id: str, rows: list[dict[str, Any]]) -> str:
    salud = [r for r in rows if r.get('es_aplicable') and r.get('familia') == 'salud']
    circ = [r for r in rows if r.get('es_aplicable') and r.get('familia') == 'circulante']
    no = [r for r in rows if not r.get('es_aplicable')]
    lines = [
        f"⚙️ <b>Palancas · {company_id}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "<i>Contrafactual del último mes del extracto. No es proyección a 90 días.</i>",
        "",
        f"<b>Salud aplicables</b> ({len(salud)})",
    ]
    for row in salud:
        lines.append(f"• <code>{row['id']}</code>")
    lines.append("")
    lines.append(f"<b>Circulante aplicables</b> ({len(circ)})")
    for row in circ:
        lines.append(f"• <code>{row['id']}</code> <i>caja, no score</i>")
    if no:
        lines.append("")
        lines.append(f"<b>No aplicables</b> ({len(no)})")
        for row in no[:8]:
            lines.append(f"• <code>{row['id']}</code> — {row.get('motivo_rechazo')}")
        if len(no) > 8:
            lines.append(f"• … {len(no) - 8} más")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("Usa /simulate para rankings ΔS vs caja.")
    return "\n".join(lines)


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "nulo"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}"


def format_rankings_html(result: dict[str, Any]) -> str:
    cid = result.get("company_id", "")
    lines = [
        f"🧪 <b>Rankings palancas · {cid}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Sims: <code>{result.get('n_sims', 0)}</code> · {result.get('modo', '')}",
        "",
        "<b>Sugerencias de salud</b> (orden ΔS)",
    ]
    sugerencias = result.get("sugerencias") or []
    if not sugerencias:
        lines.append("<i>Nada que recomendar para la salud.</i>")
    for i, row in enumerate(sugerencias[:5], 1):
        rec = " ★" if result.get("recomendado") and result["recomendado"].get("id") == row.get("id") and i == 1 else ""
        label = row.get("label") or row.get("id")
        lines.append(
            f"{i}. {label}{rec}\n"
            f"   ΔS <b>{_fmt_delta(row.get('delta_score'))}</b> · "
            f"caja <code>{row.get('caja_liberada_eur', 0):,.0f} €</code>"
        )
    lines.append("")
    lines.append("<b>Opciones de circulante</b> (orden caja · ΔS nulo)")
    circ = result.get("opciones_circulante") or []
    if not circ:
        lines.append("<i>Sin opciones de caja.</i>")
    for i, row in enumerate(circ[:5], 1):
        label = row.get("label") or row.get("id")
        lines.append(
            f"{i}. {label}\n"
            f"   caja <code>{row.get('caja_liberada_eur', 0):,.0f} €</code> · ΔS nulo"
        )
    rec = result.get("recomendado")
    if rec:
        lines.append("")
        lines.append(f"★ Recomendada: <b>{rec.get('label') or rec.get('id')}</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("<i>No se reescribe 2024-09…2026-07. Δ momentum = 0.</i>")
    return "\n".join(lines)


def palancas_message(company_id: str) -> tuple[str, dict[str, Any]]:
    cid = company_id.strip().upper()
    rows = evaluate_catalog(cid)
    return format_palancas_html(cid, rows), palancas_keyboard(cid)


def rankings_message(company_id: str) -> tuple[str, dict[str, Any]]:
    cid = company_id.strip().upper()
    result = recommend_levers(cid)
    if not result.get("ok"):
        return f"❌ No pude rankear <code>{cid}</code>: {result.get('error')}", palancas_keyboard(cid)
    return format_rankings_html(result), palancas_keyboard(cid)
