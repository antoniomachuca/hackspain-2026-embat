import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from algorythm.email_notifier import (
    alert_from_snapshot, broadcast_alert, build_message, format_alert_html, format_alert_text,
    format_subject, load_recipients, nombre_de, recipient_for, save_recipient, should_send,
)

CONFIG = {
    'smtp_host': 'localhost', 'smtp_port': 1025, 'sender': 'X-Ray Monitor <monitor@xray.local>',
    'domain': 'xray.local', 'front_url': 'http://localhost:3000', 'enabled': True,
}

DETERIORO = {
    'company_id': 'COMP_0010', 'group_id': 'GROUP_0010', 'alert_id': 'abc123',
    'as_of': '2026-09-01', 'comparison_as_of': '2026-06-01',
    'state': 'DETERIORO', 'severity': 'ALTA', 'direction': 'deterioration',
    'score': 46.16, 'delta_score': -30.88, 'momentum': -0.25,
    'drivers': [
        {'field': 'liquidity_points', 'delta_points': -20.15},
        {'field': 'collections_points', 'delta_points': -6.20},
    ],
}

MEJORA = dict(DETERIORO, company_id='COMP_0055', state='MEJORANDO', severity='MEDIA',
              direction='improvement', delta_score=15.2, drivers=[{'field': 'growth_points', 'delta_points': 8.5}])

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32


class TestEmailNotifier(unittest.TestCase):

    def test_solo_avisa_a_la_empresa_cuando_se_deteriora(self):
        self.assertTrue(should_send(DETERIORO))
        self.assertTrue(should_send(dict(DETERIORO, state='TORCIENDOSE', severity='MEDIA')))
        self.assertFalse(should_send(MEJORA))
        self.assertFalse(should_send(dict(DETERIORO, state='BACHE')))

    def test_destinatario_derivado_del_identificador(self):
        self.assertEqual(recipient_for('COMP_0010', overrides={}), 'finanzas@comp-0010.xray.local')
        self.assertEqual(recipient_for('comp_0010', overrides={'COMP_0010': 'cfo@velasco.es'}), 'cfo@velasco.es')

    def test_asunto_y_texto_en_lenguaje_de_empresa(self):
        subject = format_subject(DETERIORO)
        self.assertIn('Sociedad 0010', subject)
        self.assertIn('Deterioro', subject)
        self.assertIn('-30,9', subject)
        self.assertNotIn('puntos', format_subject(dict(DETERIORO, delta_score=8.7)))
        text = format_alert_text(DETERIORO, 'http://localhost:3000')
        self.assertIn('Liquidez y margen de caja', text)
        self.assertIn('-20,15', text)
        self.assertIn('http://localhost:3000/COMP_0010', text)
        self.assertIn('Prioriza el circulante', text)

    def test_html_incrusta_la_grafica_por_cid(self):
        html = format_alert_html(DETERIORO, 'http://localhost:3000', chart_cid='grafica@xray.local')
        self.assertIn('src="cid:grafica@xray.local"', html)
        self.assertIn('46,2', html)
        self.assertNotIn('<img', format_alert_html(DETERIORO, 'http://localhost:3000'))

    def test_html_sigue_el_sistema_visual_del_front(self):
        html = format_alert_html(DETERIORO, 'http://localhost:3000')
        self.assertIn('Sociedad 0010', html)
        self.assertIn('#08070c', html)            # --color-deep
        self.assertIn('#b083e8', html)            # morado Embat
        self.assertIn('General Sans', html)
        self.assertNotIn('Atención', html)        # la ficha no usa la banda cuando hay estado
        self.assertIn('color:#e5775b;font-variant-numeric', html)   # el número va en el color del estado
        self.assertIn('↓ −30,9', html)            # delta con flecha y signo, como el front
        self.assertIn('/empresa/COMP_0010/drivers', html)

    def test_score_y_etiqueta_en_el_color_del_estado(self):
        # Como el Anillo de la ficha: TORCIENDOSE pinta el número en naranja y la
        # etiqueta dice Torciéndose aunque el score sea 60,6.
        html = format_alert_html(dict(DETERIORO, state='TORCIENDOSE', score=60.6), 'http://localhost:3000')
        self.assertIn('color:#e59f5e;font-variant-numeric', html)
        self.assertEqual(html.count('>Torciéndose<'), 2)   # frase de cabecera y tarjeta del score
        self.assertNotIn('Estable', html)
        self.assertEqual(nombre_de('COMP_0176'), 'Sociedad 0176')

    def test_alerta_real_desde_el_snapshot(self):
        alert = alert_from_snapshot('comp_176')
        self.assertEqual(alert['company_id'], 'COMP_0176')
        self.assertEqual(alert['delivery_mode'], 'manual_test')
        self.assertIn('score', alert)
        self.assertEqual(len(alert['drivers']), 2)
        with self.assertRaises(ValueError):
            alert_from_snapshot('COMP_9999')

    def test_force_salta_el_filtro_de_direccion(self):
        with patch('algorythm.email_notifier.smtplib.SMTP') as smtp_cls, \
             patch('algorythm.email_notifier.render_chart', return_value=None):
            smtp = MagicMock()
            smtp_cls.return_value.__enter__.return_value = smtp
            res = broadcast_alert(MEJORA, config=CONFIG, force=True)
        self.assertEqual(res['sent'], 1)

    def test_mensaje_multipart_con_grafica_y_hilo_por_empresa(self):
        msg = build_message(DETERIORO, CONFIG, chart_png=PNG)
        self.assertEqual(msg['To'], 'finanzas@comp-0010.xray.local')
        self.assertEqual(msg['From'], CONFIG['sender'])
        self.assertEqual(msg['In-Reply-To'], '<xray-comp_0010@xray.local>')
        self.assertEqual(msg['X-XRay-State'], 'DETERIORO')
        self.assertEqual(msg.get_content_type(), 'multipart/alternative')
        plain, rich = msg.get_payload()
        self.assertEqual(plain.get_content_type(), 'text/plain')
        self.assertEqual(rich.get_content_type(), 'multipart/related')
        html_part, image = rich.get_payload()
        self.assertEqual(html_part.get_content_type(), 'text/html')
        self.assertEqual(image.get_content_type(), 'image/png')
        self.assertEqual(image.get_payload(decode=True), PNG)
        self.assertEqual(image.get_content_disposition(), 'inline')
        cid = image['Content-ID'].strip('<>')
        self.assertIn(f'cid:{cid}', html_part.get_content())

    def test_sin_grafica_el_mensaje_sigue_siendo_valido(self):
        msg = build_message(DETERIORO, CONFIG, chart_png=None)
        plain, rich = msg.get_payload()
        self.assertEqual(rich.get_content_type(), 'text/html')

    def test_broadcast_envia_por_smtp(self):
        with patch('algorythm.email_notifier.smtplib.SMTP') as smtp_cls, \
             patch('algorythm.email_notifier.render_chart', return_value=PNG):
            smtp = MagicMock()
            smtp_cls.return_value.__enter__.return_value = smtp
            res = broadcast_alert(DETERIORO, config=CONFIG)
        smtp_cls.assert_called_once_with('localhost', 1025, timeout=15)
        smtp.send_message.assert_called_once()
        sent = smtp.send_message.call_args.args[0]
        self.assertEqual(sent['To'], 'finanzas@comp-0010.xray.local')
        self.assertEqual(res['sent'], 1)
        self.assertTrue(res['chart'])

    def test_broadcast_ignora_mejoras_sin_tocar_smtp(self):
        with patch('algorythm.email_notifier.smtplib.SMTP') as smtp_cls:
            res = broadcast_alert(MEJORA, config=CONFIG)
        smtp_cls.assert_not_called()
        self.assertEqual(res['sent'], 0)
        self.assertIn('no se avisa', res['reason'])

    def test_broadcast_reporta_fallo_de_conexion(self):
        with patch('algorythm.email_notifier.smtplib.SMTP', side_effect=ConnectionRefusedError('sin Mailpit')), \
             patch('algorythm.email_notifier.render_chart', return_value=None):
            res = broadcast_alert(DETERIORO, config=CONFIG)
        self.assertEqual(res['failed'], 1)
        self.assertIn('sin Mailpit', res['error'])

    def test_destinatario_explicito_manda(self):
        with patch('algorythm.email_notifier.smtplib.SMTP') as smtp_cls, \
             patch('algorythm.email_notifier.render_chart', return_value=None):
            smtp = MagicMock()
            smtp_cls.return_value.__enter__.return_value = smtp
            res = broadcast_alert(DETERIORO, config=CONFIG, recipient='hugo@ejemplo.es')
        self.assertEqual(res['to'], 'hugo@ejemplo.es')

    def test_direcciones_fijadas_se_guardan_y_leen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'email_recipients.json'
            self.assertEqual(load_recipients(path), {})
            save_recipient('comp_0010', 'cfo@velasco.es', path)
            self.assertEqual(load_recipients(path), {'COMP_0010': 'cfo@velasco.es'})
            self.assertEqual(json.load(path.open())['recipients'], {'COMP_0010': 'cfo@velasco.es'})


if __name__ == '__main__':
    unittest.main()
