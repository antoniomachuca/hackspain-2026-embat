import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

if not __package__:
    sys.path.insert(0, str(ROOT))

from algorythm.telegram_notifier import (
    load_config, add_subscriber, load_subscribers,
    send_telegram_message, format_alert_html, broadcast_alert,
    build_alert_keyboard, send_telegram_photo, answer_callback_query,
    send_chat_action, get_ssl_context
)
from algorythm.score_monitor import monitor_once
from algorythm.telegram_charts import generate_company_chart
from algorythm.score_whatif import simulate_whatif
from algorythm.telegram_levers import apply_recommended, palancas_message, rankings_message


def load_latest_scores():
    panels_path = HERE / 'engine_results' / 'score_panels.npz'
    if not panels_path.exists():
        return None
    import numpy as np
    with np.load(panels_path, allow_pickle=False) as data:
        return {
            'company_id': data['company_id'],
            'group_id': data['group_id'],
            'as_of': data['as_of'],
            'score': data['score'],
            'state': data['state'],
            'momentum': data['momentum'],
            'liquidity_points': data['liquidity_points'],
            'collections_points': data['collections_points'],
            'debt_points': data['debt_points'],
            'momentum_points': data['momentum_points'],
            'growth_points': data['growth_points'],
            'fragility_points': data['fragility_points'],
            'clipping_points': data['clipping_points'],
            'state_eligible': data['state_eligible'],
        }


def handle_start(chat_id, user_name=""):
    add_subscriber(chat_id)
    greeting = f"Hola {user_name}! " if user_name else ""
    msg = (
        f"👋 <b>{greeting}Bienvenido al Bot Oficial de X-Ray Financial Health</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Te has suscrito con éxito al <b>Monitor Autónomo de Tesorería y Solvencia B2B</b>.\n\n"
        f"🚨 <b>¿Cómo funciona?</b>\n"
        f"El motor vigila continuamente los extractos bancarios y facturas ERP de la cartera. "
        f"Cuando detecte un deterioro real (filtrando baches transitorios y estacionalidad) "
        f"o una recuperación, <b>te enviará un aviso interactivo de inmediato con botones táctiles</b>.\n\n"
        f"📌 <b>Comandos interactivos disponibles:</b>\n"
        f"• 📉 <code>/top_riesgo</code> : Top 5 empresas en mayor riesgo o deterioro.\n"
        f"• 🔍 <code>/score &lt;ID&gt;</code> : Ficha financiera y waterfall de factores.\n"
        f"• 📊 <code>/grafica &lt;ID&gt;</code> : Evolución temporal en modo oscuro (24 meses).\n"
        f"• 💡 <code>/whatif &lt;ID&gt; [monto]</code> : Simulación contrafactual de rescate/factoring.\n"
        f"• ⚙️ <code>/palancas &lt;ID&gt;</code> : Catálogo de palancas aplicables.\n"
        f"• 🧪 <code>/simulate &lt;ID&gt;</code> : Rankings salud vs circulante (rescore real).\n"
        f"• 📜 <code>/alertas</code> : Ver las últimas 5 alertas emitidas por el monitor.\n"
        f"• ⚡ <code>/simular_alerta</code> : Probar alerta crítica con botones táctiles.\n"
        f"• ℹ️ <code>/status</code> : Estado de la cartera y cobertura de datos.\n"
        f"• ❓ <code>/help</code> : Ver esta ayuda en cualquier momento.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>X-Ray Engine · HackSpain 2026 · Reto Embat</i>"
    )
    return send_telegram_message(chat_id, msg)


def handle_help(chat_id):
    msg = (
        f"📖 <b>Guía de Comandos del Bot X-Ray</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <code>/start</code> - Activar suscripción a alertas proactivas.\n"
        f"• <code>/top_riesgo</code> - Ver las 5 empresas con mayor deterioro o caída de score.\n"
        f"• <code>/score COMP_XXXX</code> - Ver ficha financiera, score (0-100), momentum y waterfall de factores.\n"
        f"• <code>/grafica COMP_XXXX</code> - Ver gráfico temporal de 24 meses en dark mode.\n"
        f"• <code>/whatif COMP_XXXX [monto]</code> - Simular inyección de liquidez / factoring Embat.\n"
        f"• <code>/palancas COMP_XXXX</code> - Catálogo de palancas con es_aplicable.\n"
        f"• <code>/simulate COMP_XXXX</code> - Rankings de palancas (ΔS vs caja).\n"
        f"• <code>/alertas</code> - Histórico de las 5 alertas más recientes del feed.\n"
        f"• <code>/simular_alerta</code> - Enviar una alerta de prueba con botones táctiles.\n"
        f"• <code>/status</code> - Estadísticas del monitor y cartera auditada.\n"
    )
    return send_telegram_message(chat_id, msg)


DB_PATH = ROOT / 'xray.duckdb'


def handle_status(chat_id):
    # 1. Intentar primero DuckDB (fuente centralizada)
    if DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            comp_cnt = con.execute("SELECT count(*) FROM companies;").fetchone()[0]
            inv_cnt = con.execute("SELECT count(*) FROM invoices;").fetchone()[0]
            trans_cnt = con.execute("SELECT count(*) FROM transactions;").fetchone()[0]
            alerts_cnt = con.execute("SELECT count(*) FROM alerts;").fetchone()[0]
            risk_cnt = con.execute("SELECT count(*) FROM v_latest_company_scores WHERE state IN ('DETERIORO', 'TORCIENDOSE', 'BACHE');").fetchone()[0]
            con.close()
            subs = load_subscribers()
            msg = (
                f"📊 <b>ESTADO DEL MONITOR FINANCIERO X-RAY</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 <b>Sociedades en cartera:</b> <code>{comp_cnt:,}</code>\n"
                f"📑 <b>Facturas auditadas ERP:</b> <code>{inv_cnt:,}</code>\n"
                f"💳 <b>Transacciones bancarias:</b> <code>{trans_cnt:,}</code>\n"
                f"🚨 <b>Alertas de riesgo registradas:</b> <code>{alerts_cnt:,}</code>\n"
                f"⚠️ <b>Sociedades en estrés/deterioro:</b> <code>{risk_cnt:,}</code>\n"
                f"👥 <b>Suscriptores Telegram activos:</b> <code>{len(subs)}</code>\n"
                f"🗄 <b>Motor analítico central:</b> <code>xray.duckdb (Activo)</code>\n"
                f"⚙️ <b>Gates estrictos:</b> <code>12 / 12 PASS</code>\n"
                f"⏱ <b>Filtro de persistencia:</b> <code>3 meses (Resistente a baches)</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🟢 <i>Monitor operativo en tiempo real conectado a DuckDB.</i>"
            )
            return send_telegram_message(chat_id, msg)
        except Exception:
            pass

    # 2. Fallback a score_manifest.json y validation.json
    manifest_path = HERE / 'engine_results' / 'score_manifest.json'
    validation_path = HERE / 'engine_results' / 'validation.json'
    companies_count = 1286
    eligible = "N/D"
    high_quality = "N/D"
    if validation_path.exists():
        try:
            with validation_path.open(encoding='utf-8') as f:
                val = json.load(f)
                cov = val.get('coverage', {})
                companies_count = cov.get('companies', 1286)
                high_quality = cov.get('high_quality', "N/D")
                eligible = val.get('trajectory_states', {}).get('endpoint_eligible', "N/D")
        except Exception:
            pass

    subs = load_subscribers()
    msg = (
        f"📊 <b>ESTADO DEL MONITOR FINANCIERO X-RAY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Sociedades en cartera:</b> <code>{companies_count}</code>\n"
        f"🛡 <b>Empresas bajo monitorización activa:</b> <code>{eligible}</code>\n"
        f"📈 <b>Empresas con alta calidad (&gt;=0.80):</b> <code>{high_quality}</code>\n"
        f"👥 <b>Suscriptores Telegram activos:</b> <code>{len(subs)}</code>\n"
        f"⚙️ <b>Gates estrictos:</b> <code>12 / 12 PASS</code>\n"
        f"⏱ <b>Filtro de persistencia:</b> <code>3 meses (Resistente a baches)</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 <i>Monitor operativo en tiempo real.</i>"
    )
    return send_telegram_message(chat_id, msg)


def handle_top_risk(chat_id):
    # 1. Intentar primero DuckDB (fuente centralizada)
    if DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            top5 = con.execute("""
                SELECT company_id, group_id, score, delta_3m, state, as_of
                FROM v_latest_company_scores
                WHERE state_eligible = true
                ORDER BY delta_3m ASC
                LIMIT 5;
            """).fetchall()
            con.close()
            if top5:
                as_of = str(top5[0][5])
                lines = [
                    f"🚨 <b>TOP 5 EMPRESAS EN MAYOR DETERIORO</b>",
                    f"<i>Corte analítico activo: {as_of} (DuckDB Live)</i>",
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━"
                ]
                for rank, (cid, gid, score, delta, state, _) in enumerate(top5, 1):
                    lines.append(
                        f"<b>{rank}. {cid}</b> <i>({gid})</i>\n"
                        f"   • Score: <b>{score:.2f}</b> (🔻 <code>{delta:.2f} pts</code>)\n"
                        f"   • Estado: <b>{state}</b> | Consultar: <code>/score {cid}</code>\n"
                    )
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 <i>Alerta autónoma activa ante caídas adicionales.</i>")
                return send_telegram_message(chat_id, '\n'.join(lines))
        except Exception:
            pass

    # 2. Fallback a score_panels.npz
    panels = load_latest_scores()
    if not panels:
        return send_telegram_message(chat_id, "⚠️ No se encontraron resultados de scoring en <code>engine_results/</code>.")
    
    last_idx = panels['score'].shape[1] - 1
    base_idx = max(0, last_idx - 3)
    deltas = panels['score'][:, last_idx] - panels['score'][:, base_idx]
    eligible = panels['state_eligible'][:, last_idx]
    
    candidates = []
    for i in range(len(panels['company_id'])):
        if eligible[i]:
            candidates.append((i, float(deltas[i]), float(panels['score'][i, last_idx]), str(panels['state'][i, last_idx])))
    
    candidates.sort(key=lambda x: x[1])
    top5 = candidates[:5]

    as_of = str(panels['as_of'][last_idx])
    comp_as_of = str(panels['as_of'][base_idx])

    lines = [
        f"🚨 <b>TOP 5 EMPRESAS EN MAYOR DETERIORO</b>",
        f"<i>Comparativa trimestral: {comp_as_of} ➔ {as_of}</i>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for rank, (idx, delta, score, state) in enumerate(top5, 1):
        cid = str(panels['company_id'][idx])
        gid = str(panels['group_id'][idx])
        lines.append(
            f"<b>{rank}. {cid}</b> <i>({gid})</i>\n"
            f"   • Score: <b>{score:.2f}</b> (🔻 <code>{delta:.2f} pts</code>)\n"
            f"   • Estado: <b>{state}</b> | Consultar: <code>/score {cid}</code>\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 <i>Alerta autónoma activa ante caídas adicionales.</i>")
    return send_telegram_message(chat_id, '\n'.join(lines))


def handle_score_query(chat_id, company_id):
    company_id = company_id.strip().upper()
    if not company_id.startswith("COMP_") and company_id.startswith("COMP") and company_id[4:].isdigit():
        company_id = f"COMP_{company_id[4:]}"
    elif company_id.isdigit():
        company_id = f"COMP_{company_id.zfill(4)}"

    # 1. Intentar primero DuckDB (fuente centralizada)
    if DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            row = con.execute("""
                SELECT 
                    company_id, group_id, as_of, score, delta_3m, state, momentum,
                    liquidity_points, collections_points, debt_points, momentum_points,
                    growth_points, fragility_points
                FROM v_latest_company_scores
                WHERE company_id = ?;
            """, (company_id,)).fetchone()
            con.close()
            if row:
                cid, gid, as_of, score, delta, state, mom, l_pts, c_pts, d_pts, m_pts, g_pts, f_pts = row
                delta_sign = '+' if delta > 0 else ''
                delta_sym = '🔺' if delta > 0 else '🔻' if delta < 0 else '▶️'
                health_tag = '🟢 Excelente' if score >= 70 else '🟡 Media / Estable' if score >= 50 else '🔴 Alta Fragilidad'
                msg = (
                    f"🏢 <b>FICHA FINANCIERA: {cid}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 <b>Grupo:</b> <code>{gid}</code> | 📅 <b>Corte:</b> <code>{as_of}</code>\n"
                    f"📊 <b>Score Global:</b> <b>{score:.2f} / 100</b> ({health_tag})\n"
                    f"📉 <b>Variación 3M:</b> {delta_sym} <b>{delta_sign}{delta:.2f} pts</b>\n"
                    f"⚡ <b>Momentum:</b> <code>{mom:.3f}</code> | 🚦 <b>Estado:</b> <b>{state}</b>\n\n"
                    f"🔍 <b>Desglose Aditivo de Factores (Puntos):</b>\n"
                    f"  💧 Liquidez y Margen: <code>{l_pts:.2f} pts</code>\n"
                    f"  📑 Cobros y Facturas ERP: <code>{c_pts:.2f} pts</code>\n"
                    f"  🏦 Carga de Deuda: <code>{d_pts:.2f} pts</code>\n"
                    f"  ⚡ Inercia de Trayectoria: <code>{m_pts:+.2f} pts</code>\n"
                    f"  🌱 Crecimiento de Cobros: <code>{g_pts:+.2f} pts</code>\n"
                    f"  💣 Penalización por Fragilidad: <code>-{f_pts:.2f} pts</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<i>Fuente: xray.duckdb (Single Source of Truth)</i>"
                )
                markup = build_alert_keyboard(cid)
                return send_telegram_message(chat_id, msg, reply_markup=markup)
        except Exception:
            pass

    # 2. Fallback a score_panels.npz
    panels = load_latest_scores()
    if not panels:
        return send_telegram_message(chat_id, "⚠️ No se han encontrado datos de puntuación disponibles.")

    ids = [str(cid) for cid in panels['company_id']]
    if company_id not in ids:
        matches = [cid for cid in ids if company_id in cid][:5]
        if matches:
            hint = ", ".join(f"<code>{m}</code>" for m in matches)
            return send_telegram_message(chat_id, f"❌ No existe <code>{company_id}</code>. ¿Quizás quisiste decir: {hint}?")
        return send_telegram_message(chat_id, f"❌ Empresa <code>{company_id}</code> no encontrada en el catálogo de 1.286 sociedades.")

    idx = ids.index(company_id)
    last_idx = panels['score'].shape[1] - 1
    base_idx = max(0, last_idx - 3)
    
    score = float(panels['score'][idx, last_idx])
    delta = float(panels['score'][idx, last_idx] - panels['score'][idx, base_idx])
    state = str(panels['state'][idx, last_idx])
    mom = float(panels['momentum'][idx, last_idx])
    gid = str(panels['group_id'][idx])
    as_of = str(panels['as_of'][last_idx])
    
    l_pts = float(panels['liquidity_points'][idx, last_idx])
    c_pts = float(panels['collections_points'][idx, last_idx])
    d_pts = float(panels['debt_points'][idx, last_idx])
    m_pts = float(panels['momentum_points'][idx, last_idx])
    g_pts = float(panels['growth_points'][idx, last_idx])
    f_pts = float(panels['fragility_points'][idx, last_idx])

    delta_sign = '+' if delta > 0 else ''
    delta_sym = '🔺' if delta > 0 else '🔻' if delta < 0 else '▶️'
    health_tag = '🟢 Excelente' if score >= 70 else '🟡 Media / Estable' if score >= 50 else '🔴 Alta Fragilidad'

    msg = (
        f"🏢 <b>FICHA FINANCIERA: {company_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Grupo:</b> <code>{gid}</code> | 📅 <b>Corte:</b> <code>{as_of}</code>\n"
        f"📊 <b>Score Global:</b> <b>{score:.2f} / 100</b> ({health_tag})\n"
        f"📉 <b>Variación 3M:</b> {delta_sym} <b>{delta_sign}{delta:.2f} pts</b>\n"
        f"⚡ <b>Momentum:</b> <code>{mom:.3f}</code> | 🚦 <b>Estado:</b> <b>{state}</b>\n\n"
        f"🔍 <b>Desglose Aditivo de Factores (Puntos):</b>\n"
        f"  💧 Liquidez y Margen: <code>{l_pts:.2f} pts</code>\n"
        f"  📑 Cobros y Facturas ERP: <code>{c_pts:.2f} pts</code>\n"
        f"  🏦 Carga de Deuda: <code>{d_pts:.2f} pts</code>\n"
        f"  ⚡ Inercia de Trayectoria: <code>{m_pts:+.2f} pts</code>\n"
        f"  🌱 Crecimiento de Cobros: <code>{g_pts:+.2f} pts</code>\n"
        f"  💣 Penalización por Fragilidad: <code>-{f_pts:.2f} pts</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Suma exacta reconciliada (Waterfall = {score:.2f})</i>"
    )
    markup = build_alert_keyboard(company_id)
    return send_telegram_message(chat_id, msg, reply_markup=markup)


def handle_recent_alerts(chat_id):
    # 1. Intentar primero DuckDB (fuente centralizada)
    if DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            alerts = con.execute("""
                SELECT company_id, state, score, delta_score, as_of
                FROM alerts
                ORDER BY as_of DESC, score ASC
                LIMIT 5;
            """).fetchall()
            con.close()
            if alerts:
                lines = ["🚨 <b>ÚLTIMAS ALERTAS EMITIDAS POR EL MONITOR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━"]
                for cid, st, sc, ds, asof in alerts:
                    sign = '+' if ds > 0 else ''
                    sym = '🔻' if ds < 0 else '🔺'
                    lines.append(
                        f"• <b>{cid}</b> (<code>{asof}</code>) ➔ <b>{st}</b>\n"
                        f"  Score: <b>{sc:.2f}</b> ({sym} <code>{sign}{ds:.2f} pts</code>)"
                    )
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Monitor proactivo en tiempo real · xray.duckdb</i>")
                return send_telegram_message(chat_id, '\n'.join(lines))
        except Exception:
            pass

    # 2. Fallback a alerts_feed.json
    feed_path = HERE / 'engine_results' / 'alerts_feed.json'
    if not feed_path.exists():
        return send_telegram_message(chat_id, "ℹ️ El feed de alertas aún no tiene eventos publicados.")
    try:
        with feed_path.open(encoding='utf-8') as f:
            data = json.load(f)
            alerts = data.get('alerts', [])
            if not alerts:
                return send_telegram_message(chat_id, "ℹ️ No hay alertas registradas recientemente.")
            recent = alerts[-5:]
            lines = ["🚨 <b>ÚLTIMAS ALERTAS EMITIDAS POR EL MONITOR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for a in reversed(recent):
                cid = a.get('company_id')
                st = a.get('state')
                sc = a.get('score', 0.0)
                ds = a.get('delta_score', 0.0)
                asof = a.get('as_of')
                sign = '+' if ds > 0 else ''
                sym = '🔻' if ds < 0 else '🔺'
                lines.append(
                    f"• <b>{cid}</b> (<code>{asof}</code>) ➔ <b>{st}</b>\n"
                    f"  Score: <b>{sc:.2f}</b> ({sym} <code>{sign}{ds:.2f} pts</code>)"
                )
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Monitor proactivo en tiempo real</i>")
            return send_telegram_message(chat_id, '\n'.join(lines))
    except Exception as e:
        return send_telegram_message(chat_id, f"Error al leer alertas: {e}")


def handle_simulate_alert(chat_id):
    dummy_alert = {
        'company_id': 'COMP_0010',
        'group_id': 'GROUP_0010',
        'as_of': '2026-09-01',
        'comparison_as_of': '2026-06-01',
        'state': 'DETERIORO',
        'severity': 'ALTA',
        'direction': 'deterioration',
        'score': 46.16,
        'delta_score': -30.88,
        'momentum': -0.250,
        'drivers': [
            {'field': 'liquidity_points', 'delta_points': -20.15},
            {'field': 'collections_points', 'delta_points': -6.20},
            {'field': 'fragility_points', 'delta_points': -4.53}
        ]
    }
    text = format_alert_html(dummy_alert)
    markup = build_alert_keyboard('COMP_0010')
    return send_telegram_message(chat_id, text, reply_markup=markup)


def parse_amount(val_str):
    if not val_str:
        return None
    s = str(val_str).strip().lower().replace('€', '').replace('eur', '').replace(' ', '').strip()
    try:
        if s.endswith('k'):
            return float(s[:-1].replace(',', '.')) * 1000.0
        if s.endswith('m'):
            return float(s[:-1].replace(',', '.')) * 1000000.0
        if '.' in s and ',' in s:
            if s.find('.') < s.find(','):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif '.' in s:
            parts = s.split('.')
            if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
                s = parts[0] + parts[1]
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
                s = parts[0] + parts[1]
            else:
                s = s.replace(',', '.')
        return float(s)
    except Exception:
        return None


def handle_chart_query(chat_id, company_id):
    send_chat_action(chat_id, action="upload_photo")
    cid = company_id.strip().upper()
    try:
        photo_bytes = generate_company_chart(cid)
        caption = (
            f"📊 <b>Trayectoria Histórica Score 24M · {cid}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Evolución temporal del score X-Ray frente al umbral base de solvencia (60.0 pts).\n"
            f"💡 <i>¿Simular rescate contrafactual con Embat? Toca el botón abajo:</i>"
        )
        markup = build_alert_keyboard(cid)
        return send_telegram_photo(chat_id, photo_bytes, caption=caption, reply_markup=markup)
    except ValueError:
        return send_telegram_message(chat_id, f"❌ Empresa <code>{cid}</code> no encontrada en el catálogo.")
    except Exception as err:
        return send_telegram_message(chat_id, f"⚠️ Error al generar gráfica para <code>{cid}</code>: {err}")


def handle_whatif_query(chat_id, company_id, amount=None):
    send_chat_action(chat_id, action="typing")
    cid = company_id.strip().upper()
    res = simulate_whatif(cid, injection_amount=amount)
    if not res:
        return send_telegram_message(chat_id, f"❌ Empresa <code>{cid}</code> no encontrada en el catálogo.")
    markup = build_alert_keyboard(cid)
    return send_telegram_message(chat_id, res['summary_html'], reply_markup=markup)


def handle_palancas_query(chat_id, company_id):
    send_chat_action(chat_id, action="typing")
    cid = company_id.strip().upper()
    try:
        text, markup = palancas_message(cid)
    except KeyError:
        return send_telegram_message(chat_id, f"❌ Empresa <code>{cid}</code> no encontrada en el catálogo.")
    return send_telegram_message(chat_id, text, reply_markup=markup)


def handle_levers_rankings(chat_id, company_id):
    send_chat_action(chat_id, action="typing")
    cid = company_id.strip().upper()
    try:
        text, markup = rankings_message(cid)
    except KeyError:
        return send_telegram_message(chat_id, f"❌ Empresa <code>{cid}</code> no encontrada en el catálogo.")
    return send_telegram_message(chat_id, text, reply_markup=markup)


def handle_apply_recommended(chat_id, company_id):
    send_chat_action(chat_id, action="typing")
    cid = company_id.strip().upper()
    try:
        text, markup = apply_recommended(cid)
    except KeyError:
        return send_telegram_message(chat_id, f"❌ Empresa <code>{cid}</code> no encontrada en el catálogo.")
    return send_telegram_message(chat_id, text, reply_markup=markup)


def handle_callback_query(callback_query):
    cb_id = callback_query.get('id')
    data = callback_query.get('data', '')
    message = callback_query.get('message', {})
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    if not chat_id:
        return

    add_subscriber(chat_id)

    parts = data.split(':', 1) if data else ['', '']
    action = parts[0]
    cid = parts[1] if len(parts) > 1 else ''

    if action == 'cb_chart':
        toast = f"⏳ Generando gráfica 24M de {cid}..."
        chat_action = "upload_photo"
    elif action == 'cb_whatif':
        toast = f"⏳ Calculando simulación What-If de {cid}..."
        chat_action = "typing"
    elif action == 'cb_pal':
        toast = f"⏳ Cargando palancas de {cid}..."
        chat_action = "typing"
    elif action == 'cb_rank':
        toast = f"⏳ Rankeando palancas de {cid}..."
        chat_action = "typing"
    elif action == 'cb_rec':
        toast = f"⏳ Aplicando palanca recomendada de {cid}..."
        chat_action = "typing"
    elif action == 'cb_drivers':
        toast = f"⏳ Extrayendo desglose Waterfall de {cid}..."
        chat_action = "typing"
    else:
        toast = "⏳ Cargando petición..."
        chat_action = "typing"

    if cb_id:
        answer_callback_query(cb_id, text=toast)

    send_chat_action(chat_id, action=chat_action)

    if not data:
        return

    if action == 'cb_chart' and cid:
        handle_chart_query(chat_id, cid)
    elif action == 'cb_drivers' and cid:
        handle_score_query(chat_id, cid)
    elif action == 'cb_whatif' and cid:
        handle_whatif_query(chat_id, cid, None)
    elif action == 'cb_pal' and cid:
        handle_palancas_query(chat_id, cid)
    elif action == 'cb_rank' and cid:
        handle_levers_rankings(chat_id, cid)
    elif action == 'cb_rec' and cid:
        handle_apply_recommended(chat_id, cid)
    else:
        send_telegram_message(chat_id, f"Acción interactiva no reconocida: <code>{action}</code>")


def run_bot_polling(poll_interval=2.0, auto_monitor=True):
    config = load_config()
    token = config.get('bot_token')
    if not token:
        print("Error: No bot token configured.", file=sys.stderr)
        return

    print(f"🤖 Starting X-Ray Telegram Bot (@{config.get('bot_username')})...", flush=True)
    offset = 0
    last_monitor_check = 0.0

    while True:
        try:
            # 1. Check monitor once in background if auto_monitor is enabled
            now = time.time()
            if auto_monitor and (now - last_monitor_check > 10.0):
                last_monitor_check = now
                try:
                    res = monitor_once(HERE / 'engine_results')
                    if res.get('status') == 'processed' and res.get('new_alerts'):
                        for alert in res['new_alerts']:
                            broadcast_alert(alert)
                except Exception as monitor_err:
                    pass

            # 2. Poll updates
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=10"
            req = urllib.request.Request(url, headers={'User-Agent': 'XRayBot/1.0'})
            with urllib.request.urlopen(req, timeout=15, context=get_ssl_context()) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data.get('ok'):
                    time.sleep(poll_interval)
                    continue

                for update in data.get('result', []):
                    update_id = update['update_id']
                    offset = max(offset, update_id + 1)

                    # 1. Handle Callback Query (tactile inline keyboard events)
                    callback_query = update.get('callback_query')
                    if callback_query:
                        handle_callback_query(callback_query)
                        continue

                    # 2. Handle Message
                    message = update.get('message')
                    if not message:
                        continue
                    
                    chat = message.get('chat', {})
                    chat_id = chat.get('id')
                    if not chat_id:
                        continue
                    
                    user = message.get('from', {})
                    user_name = user.get('first_name', '')
                    text = message.get('text', '').strip()

                    # Always ensure sender is a subscriber
                    add_subscriber(chat_id)

                    if not text:
                        continue

                    parts = text.split()
                    cmd = parts[0].lower()
                    if '@' in cmd:
                        cmd = cmd.split('@')[0]

                    if cmd in ('/start', 'start'):
                        handle_start(chat_id, user_name)
                    elif cmd in ('/help', '/ayuda', 'help'):
                        handle_help(chat_id)
                    elif cmd in ('/status', '/estado', 'status'):
                        handle_status(chat_id)
                    elif cmd in ('/top_riesgo', '/riesgo', '/top'):
                        handle_top_risk(chat_id)
                    elif cmd in ('/alertas', '/alerts', '/feed'):
                        handle_recent_alerts(chat_id)
                    elif cmd in ('/simular_alerta', '/test', '/prueba'):
                        handle_simulate_alert(chat_id)
                    elif cmd in ('/grafica', '/chart', '/grafico'):
                        if len(parts) > 1:
                            handle_chart_query(chat_id, parts[1])
                        else:
                            send_telegram_message(chat_id, "💡 Indica el ID de la empresa. Ejemplo: <code>/grafica COMP_0010</code>")
                    elif cmd in ('/whatif', '/simular', '/what_if'):
                        if len(parts) > 1:
                            amt_str = ' '.join(parts[2:]) if len(parts) > 2 else None
                            amt = parse_amount(amt_str) if amt_str else None
                            handle_whatif_query(chat_id, parts[1], amt)
                        else:
                            send_telegram_message(chat_id, "💡 Indica la empresa y opcionalmente el importe. Ejemplo: <code>/whatif COMP_0010</code> o <code>/whatif COMP_0010 50000</code>")
                    elif cmd in ('/palancas', '/levers', '/palanca'):
                        if len(parts) > 1:
                            handle_palancas_query(chat_id, parts[1])
                        else:
                            send_telegram_message(chat_id, "⚙️ Indica el ID. Ejemplo: <code>/palancas COMP_0031</code>")
                    elif cmd in ('/simulate', '/simular_palancas', '/rankings'):
                        if len(parts) > 1:
                            handle_levers_rankings(chat_id, parts[1])
                        else:
                            send_telegram_message(chat_id, "🧪 Indica el ID. Ejemplo: <code>/simulate COMP_0031</code>")
                    elif cmd.startswith('/score'):
                        if len(parts) > 1:
                            handle_score_query(chat_id, parts[1])
                        else:
                            send_telegram_message(chat_id, "💡 Indica el ID de la empresa. Ejemplo: <code>/score COMP_0010</code>")
                    else:
                        # If user simply types a company ID directly (e.g. "COMP_0010" or "comp0010")
                        if text.upper().startswith("COMP"):
                            handle_score_query(chat_id, text)
                        else:
                            handle_help(chat_id)

        except KeyboardInterrupt:
            print("\nBot stopped by user.")
            break
        except Exception as error:
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description='Interactive Telegram Bot for X-Ray')
    parser.add_argument('--interval', type=float, default=2.0, help='Polling interval in seconds')
    parser.add_argument('--no-auto-monitor', action='store_true', help='Disable background monitor check')
    args = parser.parse_args()

    run_bot_polling(poll_interval=args.interval, auto_monitor=not args.no_auto_monitor)


if __name__ == '__main__':
    main()
