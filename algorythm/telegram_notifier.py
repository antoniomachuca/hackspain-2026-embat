import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG_PATH = HERE / 'telegram_config.json'
SUBSCRIBERS_PATH = HERE / 'telegram_subscribers.json'


def get_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl._create_unverified_context()


def _is_transient_telegram_error(error):
    msg = str(error).lower()
    transient_markers = (
        'timed out',
        'timeout',
        'temporarily unavailable',
        'connection reset',
        'connection aborted',
        'broken pipe',
        'handshake',
        'eof occurred',
        'network is unreachable',
        'name or service not known',
        '503',
        '502',
        '429',
    )
    return any(marker in msg for marker in transient_markers)


def urlopen_with_retries(req, timeout=15, retries=3, backoff_sec=0.8):
    """Open a Telegram API request with retries for flaky SSL/network."""
    last_error = None
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=get_ssl_context())
        except Exception as error:
            last_error = error
            if attempt >= retries - 1 or not _is_transient_telegram_error(error):
                raise
            time.sleep(backoff_sec * (attempt + 1))
    raise last_error


def load_config():
    config = {
        'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', '8965028491:AAHcyyt4pKY8T6zs9EkCRCzur5nZJcHAsJ8'),
        'bot_username': 'XRAY_EMBA_BOT',
        'default_chat_id': os.environ.get('TELEGRAM_CHAT_ID'),
        'enabled': True,
        'min_severity': 'MEDIA'
    }
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open(encoding='utf-8') as source:
                stored = json.load(source)
                config.update({k: v for k, v in stored.items() if v is not None})
        except Exception:
            pass
    env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if env_token:
        config['bot_token'] = env_token
    env_chat = os.environ.get('TELEGRAM_CHAT_ID')
    if env_chat:
        config['default_chat_id'] = env_chat
    return config


def load_subscribers():
    if not SUBSCRIBERS_PATH.exists():
        return []
    try:
        with SUBSCRIBERS_PATH.open(encoding='utf-8') as source:
            data = json.load(source)
            return data.get('subscribers', [])
    except Exception:
        return []


def save_subscribers(subscribers):
    unique = sorted(list({str(sub).strip() for sub in subscribers if str(sub).strip()}))
    temp_path = HERE / '.telegram_subscribers.tmp'
    with temp_path.open('w', encoding='utf-8') as stream:
        json.dump({'subscribers': unique}, stream, indent=2)
        stream.write('\n')
    temp_path.replace(SUBSCRIBERS_PATH)
    return unique


def add_subscriber(chat_id):
    chat_id = str(chat_id).strip()
    current = load_subscribers()
    if chat_id not in current:
        current.append(chat_id)
        save_subscribers(current)
    return current


def build_alert_keyboard(company_id):
    cid = str(company_id).strip().upper()
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Ver Gráfica", "callback_data": f"cb_chart:{cid}"},
                {"text": "🔍 Desglose CFO", "callback_data": f"cb_drivers:{cid}"}
            ],
            [
                {"text": "⚙️ Palancas", "callback_data": f"cb_pal:{cid}"},
                {"text": "🧪 Rankings", "callback_data": f"cb_rank:{cid}"}
            ],
            [
                {"text": "💡 What-If", "callback_data": f"cb_whatif:{cid}"}
            ]
        ]
    }


def send_telegram_message(chat_id, text, parse_mode='HTML', bot_token=None, reply_markup=None, retries=3):
    token = bot_token or load_config().get('bot_token')
    if not token:
        return {'ok': False, 'error': 'No bot token configured'}
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup

    data = json.dumps(payload).encode('utf-8')
    last_error = None
    for attempt in range(max(1, int(retries))):
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30, context=get_ssl_context()) as response:
                res_data = response.read().decode('utf-8')
                return json.loads(res_data)
        except Exception as error:
            last_error = error
            if attempt + 1 < max(1, int(retries)):
                time.sleep(0.6 * (attempt + 1))
                continue
            return {'ok': False, 'error': str(last_error)}
    return {'ok': False, 'error': str(last_error) if last_error else 'Unknown sendMessage error'}


def encode_multipart_formdata(fields, files):
    import uuid
    boundary = uuid.uuid4().hex
    crlf = b'\r\n'
    lines = []
    for key, value in fields.items():
        if value is None:
            continue
        lines.append(f'--{boundary}'.encode('utf-8'))
        lines.append(f'Content-Disposition: form-data; name="{key}"'.encode('utf-8'))
        lines.append(b'')
        if isinstance(value, (dict, list)):
            lines.append(json.dumps(value).encode('utf-8'))
        else:
            lines.append(str(value).encode('utf-8'))
    for key, (filename, file_bytes, content_type) in files.items():
        lines.append(f'--{boundary}'.encode('utf-8'))
        lines.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode('utf-8'))
        lines.append(f'Content-Type: {content_type}'.encode('utf-8'))
        lines.append(b'')
        lines.append(file_bytes)
    lines.append(f'--{boundary}--'.encode('utf-8'))
    lines.append(b'')
    body = crlf.join(lines)
    content_type_header = f'multipart/form-data; boundary={boundary}'
    return body, content_type_header


def send_telegram_photo(chat_id, photo_bytes, caption=None, parse_mode='HTML', reply_markup=None, bot_token=None, retries=3):
    token = bot_token or load_config().get('bot_token')
    if not token:
        return {'ok': False, 'error': 'No bot token configured'}

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    fields = {'chat_id': str(chat_id)}
    if caption:
        fields['caption'] = caption
        if parse_mode:
            fields['parse_mode'] = parse_mode
    if reply_markup is not None:
        if isinstance(reply_markup, (dict, list)):
            fields['reply_markup'] = json.dumps(reply_markup)
        else:
            fields['reply_markup'] = str(reply_markup)

    files = {
        'photo': ('chart.png', photo_bytes, 'image/png')
    }
    body, content_type = encode_multipart_formdata(fields, files)
    last_error = None
    for attempt in range(max(1, int(retries))):
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                'Content-Type': content_type,
                'Content-Length': str(len(body)),
                'User-Agent': 'XRayBot/1.0'
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=45, context=get_ssl_context()) as response:
                res_data = response.read().decode('utf-8')
                return json.loads(res_data)
        except Exception as error:
            last_error = error
            if attempt + 1 < max(1, int(retries)):
                time.sleep(0.6 * (attempt + 1))
                continue
            return {'ok': False, 'error': str(last_error)}
    return {'ok': False, 'error': str(last_error) if last_error else 'Unknown sendPhoto error'}


def answer_callback_query(callback_query_id, text=None, show_alert=False, bot_token=None):
    token = bot_token or load_config().get('bot_token')
    if not token or not callback_query_id:
        return {'ok': False, 'error': 'Missing token or callback_query_id'}

    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload = {'callback_query_id': callback_query_id}
    if text:
        payload['text'] = text
    if show_alert:
        payload['show_alert'] = show_alert

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10, context=get_ssl_context()) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as error:
        return {'ok': False, 'error': str(error)}


def send_chat_action(chat_id, action="typing", bot_token=None):
    token = bot_token or load_config().get('bot_token')
    if not token or not chat_id:
        return {'ok': False, 'error': 'Missing token or chat_id'}

    url = f"https://api.telegram.org/bot{token}/sendChatAction"
    data = json.dumps({'chat_id': str(chat_id), 'action': action}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=5, context=get_ssl_context()) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as error:
        return {'ok': False, 'error': str(error)}



def format_alert_html(alert):
    severity = alert.get('severity', 'MEDIA')
    state = alert.get('state', 'ESTABLE')
    direction = alert.get('direction', 'neutral')
    company_id = alert.get('company_id', 'N/D')
    group_id = alert.get('group_id', 'N/D')
    as_of = alert.get('as_of', 'N/D')
    comp_as_of = alert.get('comparison_as_of', 'trimestre anterior')
    score = alert.get('score', 0.0)
    delta_score = alert.get('delta_score', 0.0)
    momentum = alert.get('momentum', 0.0)
    
    if severity == 'ALTA' or state == 'DETERIORO':
        icon = '🚨'
        title = 'ALERTA CRÍTICA: DETERIORO FINANCIERO'
    elif state == 'TORCIENDOSE':
        icon = '⚠️'
        title = 'AVISO PREVENTIVO: TRAYECTORIA DESCENDENTE'
    elif state == 'RECUPERACION':
        icon = '🟢'
        title = 'SEÑAL POSITIVA: RECUPERACIÓN DE CAJA'
    elif state == 'MEJORANDO':
        icon = '📈'
        title = 'AVISO: MEJORA OPERATIVA SOSTENIDA'
    else:
        icon = 'ℹ️'
        title = f'MONITOR: CAMBIO DE ESTADO ({state})'

    delta_sign = '+' if delta_score > 0 else ''
    delta_symbol = '🔺' if delta_score > 0 else '🔻' if delta_score < 0 else '▶️'
    
    drivers = alert.get('drivers', [])
    driver_lines = []
    field_labels = {
        'liquidity_points': ('💧', 'Liquidez y Margen'),
        'collections_points': ('📑', 'Cobros y ERP'),
        'debt_points': ('🏦', 'Servicio de Deuda'),
        'momentum_points': ('⚡', 'Momentum / Inercia'),
        'growth_points': ('🌱', 'Crecimiento de Cobros'),
        'fragility_points': ('💣', 'Fragilidad / Estrés'),
        'clipping_points': ('📐', 'Ajuste de Rango')
    }
    for item in drivers:
        field = item.get('field', '')
        pts = item.get('delta_points', 0.0)
        sym, name = field_labels.get(field, ('•', field))
        sign = '+' if pts > 0 else ''
        driver_lines.append(f"  {sym} <b>{name}:</b> <code>{sign}{pts:.2f} pts</code>")
    
    drivers_block = '\n'.join(driver_lines) if driver_lines else '  • Sin variación significativa de factores'

    action = "Revisar vencimientos de facturas y restringir circulante." if direction == 'deterioration' else "Evaluar ampliación de líneas comerciales o confirmación de solvencia."

    msg = (
        f"{icon} <b>X-RAY MONITOR | {title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Empresa:</b> <code>{company_id}</code> <i>({group_id})</i>\n"
        f"📅 <b>Fecha de corte:</b> <code>{as_of}</code>\n\n"
        f"📊 <b>Score Actual:</b> <b>{score:.2f} / 100</b>\n"
        f"📉 <b>Variación:</b> {delta_symbol} <b>{delta_sign}{delta_score:.2f} pts</b> <i>(vs {comp_as_of})</i>\n"
        f"⚡ <b>Momentum:</b> <code>{momentum:.3f}</code> | <b>Estado:</b> <b>{state}</b>\n\n"
        f"🔍 <b>Factores Determinantes (Waterfall):</b>\n"
        f"{drivers_block}\n\n"
        f"💡 <b>Acción sugerida:</b> {action}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>Notificación autónoma proactiva emitida por X-Ray Engine</i>"
    )
    return msg


def sync_subscribers_from_updates(bot_token=None):
    token = bot_token or load_config().get('bot_token')
    if not token:
        return []
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'XRayMonitor/1.0'})
        with urllib.request.urlopen(req, timeout=10, context=get_ssl_context()) as response:
            data = json.loads(response.read().decode('utf-8'))
            if not data.get('ok'):
                return load_subscribers()
            updates = data.get('result', [])
            chats = set(load_subscribers())
            for item in updates:
                msg = item.get('message') or item.get('channel_post') or item.get('my_chat_member', {}).get('chat')
                if msg:
                    chat = msg.get('chat', msg)
                    chat_id = chat.get('id')
                    if chat_id:
                        chats.add(str(chat_id))
            return save_subscribers(list(chats))
    except Exception as error:
        return load_subscribers()


def broadcast_alert(alert, subscribers=None, bot_token=None, include_buttons=True):
    config = load_config()
    if not config.get('enabled', True):
        return {'sent': 0, 'failed': 0, 'reason': 'disabled'}

    min_severity = config.get('min_severity', 'MEDIA')
    severity = alert.get('severity', 'MEDIA')
    order = {'INFORMATIVA': 1, 'MEDIA': 2, 'ALTA': 3}
    if order.get(severity, 1) < order.get(min_severity, 2):
        return {'sent': 0, 'failed': 0, 'reason': f'severity {severity} below threshold {min_severity}'}

    text = format_alert_html(alert)
    company_id = alert.get('company_id')
    reply_markup = build_alert_keyboard(company_id) if (include_buttons and company_id) else None

    targets = set(subscribers or load_subscribers())
    default_chat = config.get('default_chat_id')
    if default_chat:
        targets.add(str(default_chat))
    
    if not targets:
        sync_subscribers_from_updates(bot_token)
        targets = set(load_subscribers())
        if default_chat:
            targets.add(str(default_chat))

    if not targets:
        return {'sent': 0, 'failed': 0, 'reason': 'no_subscribers'}

    sent = 0
    failed = 0
    token = bot_token or config.get('bot_token')
    for chat_id in targets:
        res = send_telegram_message(chat_id, text, parse_mode='HTML', bot_token=token, reply_markup=reply_markup)
        if res.get('ok'):
            sent += 1
        else:
            failed += 1
    return {'sent': sent, 'failed': failed, 'targets': list(targets)}


def broadcast_batch(alerts, bot_token=None):
    results = []
    for alert in alerts:
        res = broadcast_alert(alert, bot_token=bot_token)
        results.append(res)
    return results


def main():
    parser = argparse.ArgumentParser(description='Telegram Bot Notifier for X-Ray Financial Monitor')
    parser.add_argument('--test', action='store_true', help='Send a test alert to registered subscribers')
    parser.add_argument('--sync', action='store_true', help='Poll Telegram updates to discover new subscribers')
    parser.add_argument('--subscribers', action='store_true', help='List currently registered subscriber chat IDs')
    parser.add_argument('--add-subscriber', type=str, help='Manually add a chat ID to subscribers list')
    parser.add_argument('--send-latest', action='store_true', help='Send the latest emitted alert from alerts_feed.json')
    args = parser.parse_args()

    if args.add_subscriber:
        subs = add_subscriber(args.add_subscriber)
        print(f"Added subscriber {args.add_subscriber}. Total subscribers: {len(subs)}")
        return

    if args.sync:
        subs = sync_subscribers_from_updates()
        print(f"Synced subscribers from Telegram updates: {subs}")
        return

    if args.subscribers:
        subs = load_subscribers()
        print(f"Registered subscribers ({len(subs)}): {subs}")
        return

    if args.test:
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
        res = broadcast_alert(dummy_alert)
        print(f"Broadcast test result: {res}")
        return

    if args.send_latest:
        feed_path = HERE / 'engine_results' / 'alerts_feed.json'
        if not feed_path.exists():
            print(f"No alerts feed found at {feed_path}")
            return
        with feed_path.open(encoding='utf-8') as f:
            feed = json.load(f)
        alerts = feed.get('alerts', [])
        if not alerts:
            print("Alerts feed is empty.")
            return
        latest = alerts[-1]
        res = broadcast_alert(latest)
        print(f"Broadcast latest alert ({latest['company_id']}) result: {res}")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
