"""Aviso por correo a la empresa cuya trayectoria se tuerce.

Canal hermano de telegram_notifier.py: recibe el mismo diccionario de alerta
que produce score_monitor.py y lo convierte en un correo dirigido al
responsable financiero de la empresa afectada. Solo salen las alertas de
deterioro (TORCIENDOSE y DETERIORO); a una empresa a la que le va mal no le
mandamos las buenas noticias de las demás.

Pensado para Mailpit en local: SMTP sin autenticación en localhost:1025 y la
bandeja en http://localhost:8025. Ver algorythm/EMAIL.md.
"""

import argparse
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if not __package__:
    sys.path.insert(0, str(ROOT))

RECIPIENTS_PATH = HERE / 'email_recipients.json'

ESTADOS = {
    'DETERIORO': 'Deterioro',
    'TORCIENDOSE': 'Torciéndose',
    'BACHE': 'Bache',
    'ESTABLE': 'Estable',
    'MEJORANDO': 'Mejorando',
    'RECUPERACION': 'Recuperación',
}

# El mismo desglose que Telegram, pero en el lenguaje de quien lleva la caja.
FACTORES = {
    'liquidity_points': 'Liquidez y margen de caja',
    'collections_points': 'Cobros y facturas pendientes',
    'debt_points': 'Servicio de la deuda',
    'momentum_points': 'Tendencia de los últimos meses',
    'growth_points': 'Crecimiento de los cobros',
    'fragility_points': 'Fragilidad ante imprevistos',
    'clipping_points': 'Ajuste de rango del score',
}

ACCIONES = {
    'TORCIENDOSE': (
        'Todavía hay margen para corregir la trayectoria. Revisa los vencimientos de las '
        'facturas pendientes de cobro y adelanta los que puedas antes de que la caja se resienta.'
    ),
    'DETERIORO': (
        'Prioriza el circulante: renegocia plazos con proveedores, activa las líneas '
        'disponibles y revisa los pagos comprometidos del próximo trimestre.'
    ),
}

# Tokens del sistema visual del front (front/app/globals.css y components/ui.tsx).
# Los translúcidos van resueltos a sólidos sobre --color-deep para que los
# clientes de correo que no soportan rgba pinten lo mismo.
DEEP = '#08070c'
SURFACE = '#131218'
SURFACE_2 = '#1a1822'
LINE = '#262430'
INK = '#ffffff'
INK_2 = '#d2d2db'
INK_3 = '#afafbb'
INK_4 = '#787d96'
PURPLE = '#b083e8'
PURPLE_DEEP = '#7b32c0'
FONT = "'General Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# Color del estado, el mismo que ESTADOS_TELEGRAM en front/components/anillo.tsx:
# la ficha pinta el número del score y su etiqueta con el color del estado, no
# con la banda del score. El correo hace lo mismo para decir lo que dice la app.
COLOR = {'DETERIORO': '#e5775b', 'TORCIENDOSE': '#e59f5e'}
# EstadoChip: fondo teñido, resuelto a sólido.
ESTADO_BG = {'DETERIORO': '#2b1a19', 'TORCIENDOSE': '#2b2019'}
# Un tono por factor, como la cascada del front.
TONOS_FACTOR = ['#c357ec', '#b083e8', '#8f6fd6', '#7b32c0', '#e59f5e', '#e5775b']


def nombre_de(company_id):
    """Como nombreDe() en front/lib/motor.ts."""
    return str(company_id).replace('COMP_', 'Sociedad ')


def load_config():
    return {
        'smtp_host': os.environ.get('XRAY_SMTP_HOST', 'localhost'),
        'smtp_port': int(os.environ.get('XRAY_SMTP_PORT', '1025')),
        'sender': os.environ.get('XRAY_MAIL_FROM', 'X-Ray Monitor <monitor@xray.local>'),
        'domain': os.environ.get('XRAY_MAIL_DOMAIN', 'xray.local'),
        'front_url': os.environ.get('XRAY_FRONT_URL', 'http://localhost:3000').rstrip('/'),
        'enabled': os.environ.get('XRAY_MAIL_ENABLED', '1') != '0',
    }


def load_recipients(path=RECIPIENTS_PATH):
    """Direcciones que sobrescriben la derivada, por company_id."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with path.open(encoding='utf-8') as source:
            data = json.load(source)
    except (OSError, json.JSONDecodeError):
        return {}
    recipients = data.get('recipients', data) if isinstance(data, dict) else {}
    return {str(k).strip().upper(): str(v).strip() for k, v in recipients.items() if str(v).strip()}


def save_recipient(company_id, address, path=RECIPIENTS_PATH):
    current = load_recipients(path)
    current[str(company_id).strip().upper()] = str(address).strip()
    path = Path(path)
    temporary = path.with_name(f'.{path.name}.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump({'recipients': dict(sorted(current.items()))}, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    temporary.replace(path)
    return current


def recipient_for(company_id, overrides=None, domain='xray.local'):
    """La empresa no tiene correo en los datos: se deriva del identificador."""
    cid = str(company_id).strip().upper()
    overrides = load_recipients() if overrides is None else overrides
    if cid in overrides:
        return overrides[cid]
    return f"finanzas@{cid.lower().replace('_', '-')}.{domain}"


def should_send(alert):
    return alert.get('direction') == 'deterioration' and alert.get('state') in ACCIONES


def _num(value, decimals=1):
    """Número en formato español: coma decimal y punto de miles."""
    text = f"{float(value):,.{decimals}f}"
    return text.replace(',', ' ').replace('.', ',').replace(' ', '.')


def _signed(value, decimals=1):
    value = float(value)
    return ('+' if value > 0 else '') + _num(value, decimals)


def _company_url(alert, front_url):
    return f"{front_url}/{alert.get('company_id', '')}"


def format_subject(alert):
    state = ESTADOS.get(alert.get('state'), alert.get('state', ''))
    company = alert.get('company_id', 'N/D')
    delta = float(alert.get('delta_score', 0.0))
    # El régimen puede torcerse aunque el trimestre cierre en positivo; en ese caso el
    # delta en el asunto confunde más que informa.
    tail = f" ({_signed(delta)} puntos)" if delta < 0 else ''
    return f"[X-Ray] {nombre_de(company)}: tu salud financiera pasa a {state}{tail}"


def format_alert_text(alert, front_url):
    state = ESTADOS.get(alert.get('state'), alert.get('state', ''))
    lines = [
        f"Aviso del monitor X-Ray para {nombre_de(alert.get('company_id', 'N/D'))} ({alert.get('company_id', 'N/D')})",
        '',
        f"Con los datos bancarios hasta {alert.get('as_of', 'N/D')}, tu trayectoria de caja pasa a {state}.",
        f"Score actual: {_num(alert.get('score', 0.0))} / 100",
        f"Variación frente a {alert.get('comparison_as_of', 'el trimestre anterior')}: {_signed(alert.get('delta_score', 0.0))} puntos",
        '',
        'Qué está pesando más:',
    ]
    drivers = alert.get('drivers', [])
    if drivers:
        for item in drivers:
            name = FACTORES.get(item.get('field'), item.get('field', ''))
            lines.append(f"  - {name}: {_signed(item.get('delta_points', 0.0), 2)} puntos")
    else:
        lines.append('  - Sin un factor dominante; el cambio viene de varios pequeños.')
    lines += [
        '',
        f"Qué puedes hacer: {ACCIONES.get(alert.get('state'), '')}",
        '',
        f"Ficha completa y simulador de mejoras: {_company_url(alert, front_url)}",
        f"Desglose de drivers: {front_url}/empresa/{alert.get('company_id', '')}/drivers",
        '',
        'Este aviso lo emite automáticamente el monitor X-Ray cuando detecta un cambio de régimen',
        'en los movimientos bancarios, filtrando baches transitorios y estacionalidad.',
    ]
    return '\n'.join(lines)


def _delta_html(value, decimals=1, size=13):
    """Delta del front: flecha + signo + color. Nunca solo el color."""
    value = float(value)
    zero = abs(value) < 0.05
    color = INK_3 if zero else ('#a154e9' if value > 0 else '#e59f5e')
    arrow = '→' if zero else ('↑' if value > 0 else '↓')
    text = '0' if zero else f"{'+' if value > 0 else '−'}{_num(abs(value), decimals)}"
    return (f'<span style="color:{color};font-size:{size}px;font-weight:500;'
            f'font-variant-numeric:tabular-nums;white-space:nowrap">{arrow} {text}</span>')


def _chip(label, color, bg):
    return (f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;background:{bg};'
            f'color:{color};font-size:11px;font-weight:500;line-height:16px">{label}</span>')


def format_alert_html(alert, front_url, chart_cid=None):
    state_key = alert.get('state', '')
    state = ESTADOS.get(state_key, state_key)
    color = COLOR.get(state_key, '#e59f5e')
    company = alert.get('company_id', 'N/D')
    score = float(alert.get('score', 0.0))
    estado_bg = ESTADO_BG.get(state_key, SURFACE_2)
    drivers = alert.get('drivers', [])
    if drivers:
        # Barra proporcional al peso del factor, como el desglose del front.
        top = max(abs(float(item.get('delta_points', 0.0))) for item in drivers) or 1.0
        rows = ''
        for i, item in enumerate(drivers):
            pts = float(item.get('delta_points', 0.0))
            width = max(6, int(round(abs(pts) / top * 100)))
            tone = TONOS_FACTOR[i % len(TONOS_FACTOR)] if pts > 0 else ('#e5775b' if i == 0 else '#e59f5e')
            rows += (
                f'<tr>'
                f'<td style="padding:9px 0;border-top:1px solid {LINE};color:{INK_2};font-size:13.5px">'
                f'{FACTORES.get(item.get("field"), item.get("field", ""))}</td>'
                f'<td style="padding:9px 12px;border-top:1px solid {LINE};width:120px">'
                f'<div style="height:6px;border-radius:3px;background:{SURFACE_2}">'
                f'<div style="height:6px;width:{width}%;border-radius:3px;background:{tone}"></div></div></td>'
                f'<td style="padding:9px 0;border-top:1px solid {LINE};text-align:right;white-space:nowrap">'
                f'{_delta_html(pts, 2)}<span style="color:{INK_4};font-size:12px"> pts</span></td>'
                f'</tr>'
            )
    else:
        rows = (f'<tr><td colspan="3" style="padding:9px 0;border-top:1px solid {LINE};color:{INK_3};font-size:13px">'
                f'Sin un factor dominante; el cambio viene de varios pequeños.</td></tr>')
    chart = (
        f'<div style="margin:18px 0 6px;border:1px solid {LINE};border-radius:14px;overflow:hidden;background:{SURFACE}">'
        f'<div style="padding:12px 16px 0;font-size:12px;color:{INK_3}">Trayectoria · 24 meses · el umbral punteado es 60</div>'
        f'<img src="cid:{chart_cid}" alt="Trayectoria del score de {nombre_de(company)}" width="536" '
        f'style="display:block;width:100%;max-width:536px;height:auto;border:0"></div>'
        if chart_cid else ''
    )
    url = _company_url(alert, front_url)
    # El simulador vive en un diálogo dentro de la ficha (front/components/dialogo-simulador.tsx),
    # así que el botón principal lleva a la ficha; el secundario, a la página de drivers.
    url_drivers = f"{front_url}/empresa/{company}/drivers"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark">
<link href="https://api.fontshare.com/v2/css?f[]=general-sans@400,500&display=swap" rel="stylesheet">
<title>{format_subject(alert)}</title></head>
<body style="margin:0;padding:0;background:{DEEP};font-family:{FONT};color:{INK};-webkit-font-smoothing:antialiased">
<div style="background:{DEEP};background-image:linear-gradient(168deg,#08070c 0%,#120d1d 48%,#0a0810 100%);padding:28px 16px">
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;margin:0 auto;border-collapse:collapse">
  <tr><td style="padding:0 6px 14px">
    <table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse"><tr>
      <td style="width:26px;height:26px;border-radius:8px;background:{PURPLE};text-align:center;vertical-align:middle;color:{DEEP};font-weight:600;font-size:13px">X</td>
      <td style="padding-left:9px;font-size:13.5px;font-weight:500;letter-spacing:-.01em">X Ray <span style="color:{INK_4};font-weight:400">· Salud financiera</span></td>
    </tr></table>
  </td></tr>
  <tr><td style="background:{SURFACE};border:1px solid {LINE};border-radius:18px;padding:26px 28px 28px">
    <p style="margin:0 0 6px;font-size:10px;font-weight:500;letter-spacing:.07em;text-transform:uppercase;color:{INK_4}">Aviso del monitor · corte {alert.get('as_of', 'N/D')}</p>
    <h1 style="margin:0 0 4px;font-size:22px;line-height:1.25;font-weight:500;letter-spacing:-.015em">{nombre_de(company)} <span style="color:{INK_4};font-weight:400">({company})</span></h1>
    <p style="margin:0 0 20px;font-size:14px;line-height:1.5;color:{INK_2}">Tu trayectoria de caja ha cambiado de régimen y pasa a {_chip(state, color, estado_bg)}. No es un bache puntual: el patrón se mantiene una vez descontada la estacionalidad.</p>
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:separate;border-spacing:0">
      <tr>
        <td style="width:50%;padding:14px 16px;background:{SURFACE_2};border:1px solid {LINE};border-radius:12px;vertical-align:top">
          <p style="margin:0;font-size:12px;color:{INK_3}">Score actual</p>
          <p style="margin:6px 0 0;font-size:34px;line-height:1;font-weight:500;color:{color};font-variant-numeric:tabular-nums">{_num(score)}<span style="font-size:13px;color:{INK_4};font-weight:400"> / 100</span></p>
          <p style="margin:10px 0 0">{_chip(state, color, estado_bg)}</p>
        </td>
        <td style="width:10px"></td>
        <td style="width:50%;padding:14px 16px;background:{SURFACE_2};border:1px solid {LINE};border-radius:12px;vertical-align:top">
          <p style="margin:0;font-size:12px;color:{INK_3}">Frente a {alert.get('comparison_as_of', 'el trimestre anterior')}</p>
          <p style="margin:6px 0 0;line-height:1">{_delta_html(alert.get('delta_score', 0.0), 1, 34)}<span style="font-size:13px;color:{INK_4}"> pts</span></p>
          <p style="margin:10px 0 0;font-size:11px;color:{INK_4}">Momentum {_num(alert.get('momentum', 0.0), 3)}</p>
        </td>
      </tr>
    </table>
    {chart}
    <h2 style="margin:22px 0 4px;font-size:14.5px;font-weight:600;letter-spacing:-.01em">Qué está pesando más</h2>
    <p style="margin:0 0 6px;font-size:12px;color:{INK_3}">Puntos que cada factor ha sumado o restado al score en el trimestre.</p>
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">{rows}</table>
    <h2 style="margin:22px 0 6px;font-size:14.5px;font-weight:600;letter-spacing:-.01em">Qué puedes hacer</h2>
    <p style="margin:0 0 22px;font-size:13.5px;line-height:1.55;color:{INK_2}">{ACCIONES.get(state_key, '')}</p>
    <table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:0"><tr>
      <td style="border-radius:10px;background:{PURPLE}"><a href="{url}" style="display:inline-block;padding:10px 16px;color:{DEEP};text-decoration:none;font-size:13.5px;font-weight:500">Ver mi ficha y simular mejoras</a></td>
      <td style="width:8px"></td>
      <td style="border-radius:10px;border:1px solid {LINE};background:{SURFACE_2}"><a href="{url_drivers}" style="display:inline-block;padding:9px 15px;color:{INK};text-decoration:none;font-size:13.5px;font-weight:500">Ver drivers</a></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:16px 8px 0;font-size:11.5px;line-height:1.5;color:{INK_4}">
    Este aviso lo emite el monitor X-Ray cuando detecta un cambio de régimen en los movimientos bancarios,
    filtrando baches transitorios y estacionalidad. Reto de Embat · HackSpain 2026.
  </td></tr>
</table>
</div>
</body></html>"""


def build_message(alert, config=None, chart_png=None, recipient=None):
    config = config or load_config()
    company = str(alert.get('company_id', 'N/D')).strip().upper()
    msg = EmailMessage()
    msg['Subject'] = format_subject(alert)
    msg['From'] = config['sender']
    msg['To'] = recipient or recipient_for(company, domain=config['domain'])
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(idstring=alert.get('alert_id', 'alerta')[:16], domain=config['domain'])
    # Todas las alertas de una empresa cuelgan del mismo hilo en el buzón.
    thread_root = f"<xray-{company.lower()}@{config['domain']}>"
    msg['In-Reply-To'] = thread_root
    msg['References'] = thread_root
    msg['X-XRay-Company'] = company
    msg['X-XRay-State'] = str(alert.get('state', ''))
    msg['X-XRay-Severity'] = str(alert.get('severity', ''))

    msg.set_content(format_alert_text(alert, config['front_url']))
    chart_cid = None
    if chart_png:
        chart_cid = make_msgid(idstring='grafica', domain=config['domain'])
    msg.add_alternative(format_alert_html(alert, config['front_url'], chart_cid.strip('<>') if chart_cid else None), subtype='html')
    if chart_png:
        # disposition inline: si no, los buzones la muestran como adjunto y no dentro del cuerpo.
        msg.get_payload()[1].add_related(chart_png, maintype='image', subtype='png', cid=chart_cid,
                                         disposition='inline', filename=f'{company}_trayectoria.png')
    return msg


def render_chart(company_id):
    """PNG de 24 meses del módulo de gráficas del bot; None si no se puede generar."""
    try:
        from algorythm.telegram_charts import generate_company_chart
        return generate_company_chart(company_id, theme='embat')
    except Exception:
        return None


def send_message(msg, config=None):
    config = config or load_config()
    try:
        with smtplib.SMTP(config['smtp_host'], config['smtp_port'], timeout=15) as smtp:
            smtp.send_message(msg)
        return {'ok': True}
    except (OSError, smtplib.SMTPException) as error:
        return {'ok': False, 'error': str(error)}


def broadcast_alert(alert, config=None, recipient=None, include_chart=True, force=False):
    """Envía la alerta a la empresa afectada. Misma forma de resultado que Telegram.

    force=True salta el filtro de dirección: sirve para probar el correo con una
    empresa que hoy no está en deterioro.
    """
    config = config or load_config()
    if not config.get('enabled', True):
        return {'sent': 0, 'failed': 0, 'reason': 'disabled'}
    if not force and not should_send(alert):
        return {'sent': 0, 'failed': 0,
                'reason': f"direction {alert.get('direction')} / state {alert.get('state')} no se avisa a la empresa"}
    chart = render_chart(alert.get('company_id')) if include_chart else None
    msg = build_message(alert, config, chart_png=chart, recipient=recipient)
    result = send_message(msg, config)
    outcome = {'sent': 1 if result['ok'] else 0, 'failed': 0 if result['ok'] else 1,
               'to': msg['To'], 'subject': msg['Subject'], 'chart': chart is not None}
    if not result['ok']:
        outcome['error'] = result.get('error')
    return outcome


def broadcast_batch(alerts, config=None):
    return [broadcast_alert(alert, config=config) for alert in alerts]


TEST_ALERT = {
    'company_id': 'COMP_0010',
    'group_id': 'GROUP_0010',
    'alert_id': 'prueba-manual',
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
    ],
}


def alert_from_snapshot(company_id, results=None):
    """Alerta real de la empresa en el último mes del snapshot publicado.

    Es lo que vería el monitor si esa empresa cambiase de estado hoy: mismos
    números que la ficha del front (score, delta a 3 meses, factores).
    """
    from algorythm.score_monitor import load_completed_snapshot, make_alert
    manifest, panels, _ = load_completed_snapshot(Path(results) if results else HERE / 'engine_results')
    cid = str(company_id).strip().upper()
    if cid.startswith('COMP_') and cid[5:].isdigit():
        cid = f"COMP_{cid[5:].zfill(4)}"
    ids = [str(c) for c in panels['company_id']]
    if cid not in ids:
        raise ValueError(f'{cid} no está en el snapshot')
    alert = make_alert(panels, ids.index(cid), panels['score'].shape[1] - 1, manifest['model_version'])
    return dict(alert, delivery_mode='manual_test')


def main():
    parser = argparse.ArgumentParser(description='Aviso por correo a la empresa afectada (Mailpit en local).')
    parser.add_argument('--test', action='store_true',
                        help='Envía una alerta de prueba: la ficticia de COMP_0010, o la real de --company')
    parser.add_argument('--send-latest', action='store_true', help='Envía la última alerta de deterioro del feed')
    parser.add_argument('--company', type=str,
                        help='Con --test, construye la alerta con los datos reales de esta empresa; con --send-latest, filtra por ella')
    parser.add_argument('--force', action='store_true', help='Con --test --company, envía aunque la empresa no esté en deterioro')
    parser.add_argument('--to', type=str, help='Destinatario explícito para este envío')
    parser.add_argument('--no-chart', action='store_true', help='No incrustar la gráfica de 24 meses')
    parser.add_argument('--set-recipient', nargs=2, metavar=('COMPANY_ID', 'EMAIL'),
                        help='Guarda una dirección fija para una empresa en email_recipients.json')
    parser.add_argument('--recipients', action='store_true', help='Lista las direcciones fijadas')
    args = parser.parse_args()

    if args.set_recipient:
        current = save_recipient(*args.set_recipient)
        print(f"Guardado. Direcciones fijadas: {json.dumps(current, ensure_ascii=False)}")
        return

    if args.recipients:
        print(json.dumps(load_recipients(), indent=2, ensure_ascii=False))
        return

    if args.test:
        if args.company:
            alert = alert_from_snapshot(args.company)
            if not should_send(alert) and not args.force:
                print(f"{alert['company_id']} está en {alert['state']} ({alert['direction']}): no se avisa a la empresa. "
                      f"Usa --force para enviar igualmente.")
                return
        else:
            alert = dict(TEST_ALERT)
        print(json.dumps(broadcast_alert(alert, recipient=args.to, include_chart=not args.no_chart, force=args.force),
                         ensure_ascii=False))
        return

    if args.send_latest:
        feed_path = HERE / 'engine_results' / 'alerts_feed.json'
        if not feed_path.exists():
            print(f"No hay feed en {feed_path}")
            return
        with feed_path.open(encoding='utf-8') as source:
            alerts = json.load(source).get('alerts', [])
        candidates = [a for a in alerts if should_send(a)]
        if args.company:
            candidates = [a for a in candidates if a.get('company_id') == args.company.strip().upper()]
        if not candidates:
            print('El feed no tiene alertas de deterioro que enviar.')
            return
        print(json.dumps(broadcast_alert(candidates[-1], recipient=args.to, include_chart=not args.no_chart), ensure_ascii=False))
        return

    parser.print_help()


if __name__ == '__main__':
    main()
