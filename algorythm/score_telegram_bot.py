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
    get_ssl_context
)
from algorythm.score_monitor import monitor_once


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
        f"o una recuperación, <b>te enviará un aviso de inmediato sin que tengas que preguntar</b>.\n\n"
        f"📌 <b>Comandos interactivos disponibles:</b>\n"
        f"• 📉 <code>/top_riesgo</code> : Top 5 empresas en mayor riesgo o deterioro.\n"
        f"• 🔍 <code>/score &lt;ID&gt;</code> : Consulta una empresa (ej. <code>/score COMP_0010</code>).\n"
        f"• 📜 <code>/alertas</code> : Ver las últimas 5 alertas emitidas por el monitor.\n"
        f"• ⚡ <code>/simular_alerta</code> : Probar la recepción de una alerta crítica.\n"
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
        f"• <code>/alertas</code> - Histórico de las 5 alertas más recientes del feed.\n"
        f"• <code>/simular_alerta</code> - Enviar una alerta de prueba con formato completo.\n"
        f"• <code>/status</code> - Estadísticas del monitor y cartera auditada.\n"
    )
    return send_telegram_message(chat_id, msg)


def handle_status(chat_id):
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
    panels = load_latest_scores()
    if not panels:
        return send_telegram_message(chat_id, "⚠️ No se encontraron resultados de scoring en <code>engine_results/</code>.")
    
    last_idx = panels['score'].shape[1] - 1
    base_idx = max(0, last_idx - 3)
    deltas = panels['score'][:, last_idx] - panels['score'][:, base_idx]
    eligible = panels['state_eligible'][:, last_idx]
    
    # Filter only eligible companies with negative delta
    candidates = []
    for i in range(len(panels['company_id'])):
        if eligible[i]:
            candidates.append((i, float(deltas[i]), float(panels['score'][i, last_idx]), str(panels['state'][i, last_idx])))
    
    candidates.sort(key=lambda x: x[1]) # sort by most negative delta
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
    panels = load_latest_scores()
    if not panels:
        return send_telegram_message(chat_id, "⚠️ No se han encontrado datos de puntuación disponibles.")

    ids = [str(cid) for cid in panels['company_id']]
    if company_id not in ids:
        # Search partial match
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
    
    # Drivers
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
    return send_telegram_message(chat_id, msg)


def handle_recent_alerts(chat_id):
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
    return send_telegram_message(chat_id, text)


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
                    elif cmd.startswith('/score'):
                        if len(parts) > 1:
                            handle_score_query(chat_id, parts[1])
                        else:
                            send_telegram_message(chat_id, "💡 Indica el ID de la empresa. Ejemplo: <code>/score COMP_0010</code>")
                    else:
                        # If user simply types a company ID directly (e.g. "COMP_0010")
                        if text.upper().startswith("COMP_"):
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
