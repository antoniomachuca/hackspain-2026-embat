import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from algorythm.telegram_notifier import (
    build_alert_keyboard,
    send_telegram_message,
    send_telegram_photo,
    answer_callback_query,
    broadcast_alert,
    encode_multipart_formdata
)
from algorythm.telegram_charts import generate_company_chart
from algorythm.score_whatif import (
    simulate_whatif,
    calculate_projection,
    solve_optimal_injection,
    determine_projected_state,
    select_recommended_product
)
from algorythm.score_telegram_bot import (
    parse_amount,
    handle_callback_query,
    handle_chart_query,
    handle_whatif_query
)


class TestTelegramFeatures(unittest.TestCase):

    # ==========================================
    # 1. Tests for Inline Keyboards and API
    # ==========================================

    def test_build_alert_keyboard(self):
        markup = build_alert_keyboard('COMP_0010')
        self.assertIn('inline_keyboard', markup)
        buttons = [btn for row in markup['inline_keyboard'] for btn in row]
        callbacks = [btn['callback_data'] for btn in buttons]
        texts = [btn['text'] for btn in buttons]

        self.assertIn('cb_chart:COMP_0010', callbacks)
        self.assertIn('cb_drivers:COMP_0010', callbacks)
        self.assertIn('cb_whatif:COMP_0010', callbacks)

        self.assertTrue(any('Gráfica' in t for t in texts))
        self.assertTrue(any('CFO' in t or 'Desglose' in t for t in texts))
        self.assertTrue(any('What-If' in t for t in texts))

    @patch('urllib.request.urlopen')
    def test_send_telegram_message_with_reply_markup(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'ok': True, 'result': {'message_id': 123}}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        keyboard = build_alert_keyboard('COMP_0010')
        res = send_telegram_message(12345, "Alerta de prueba", reply_markup=keyboard)
        self.assertTrue(res.get('ok'))

        # Verify request body contains reply_markup
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        sent_payload = json.loads(req.data.decode('utf-8'))
        self.assertIn('reply_markup', sent_payload)
        self.assertEqual(sent_payload['reply_markup'], keyboard)

    @patch('urllib.request.urlopen')
    def test_broadcast_alert_includes_buttons_by_default(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'ok': True, 'result': {'message_id': 124}}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        alert = {
            'company_id': 'COMP_0010',
            'group_id': 'GROUP_0010',
            'as_of': '2026-09-01',
            'state': 'DETERIORO',
            'severity': 'ALTA',
            'direction': 'deterioration',
            'score': 46.16,
            'delta_score': -30.88,
            'momentum': -0.250,
            'drivers': []
        }
        res = broadcast_alert(alert, subscribers=['99999'])
        self.assertEqual(res.get('sent'), 1)

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        sent_payload = json.loads(req.data.decode('utf-8'))
        self.assertIn('reply_markup', sent_payload)
        self.assertEqual(
            sent_payload['reply_markup']['inline_keyboard'][0][0]['callback_data'],
            'cb_chart:COMP_0010'
        )

    def test_encode_multipart_formdata(self):
        fields = {'chat_id': '12345', 'caption': 'Resumen CFO'}
        files = {'photo': ('chart.png', b'\x89PNGfakebytes', 'image/png')}
        body, content_type = encode_multipart_formdata(fields, files)

        self.assertIn('multipart/form-data; boundary=', content_type)
        self.assertIn(b'name="chat_id"', body)
        self.assertIn(b'12345', body)
        self.assertIn(b'filename="chart.png"', body)
        self.assertIn(b'\x89PNGfakebytes', body)

    @patch('urllib.request.urlopen')
    def test_send_telegram_photo(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'ok': True, 'result': {'message_id': 125}}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fake_photo = b'\x89PNG\r\n\x1a\n' + b'0' * 100
        res = send_telegram_photo(12345, fake_photo, caption="Gráfica de prueba")
        self.assertTrue(res.get('ok'))

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        self.assertIn('multipart/form-data', req.headers['Content-type'])
        self.assertIn(b'Gr\xc3\xa1fica de prueba', req.data)

    @patch('urllib.request.urlopen')
    def test_answer_callback_query(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'ok': True, 'result': True}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = answer_callback_query('query_id_123', text="Cargando simulación...")
        self.assertTrue(res.get('ok'))

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        sent_payload = json.loads(req.data.decode('utf-8'))
        self.assertEqual(sent_payload['callback_query_id'], 'query_id_123')
        self.assertEqual(sent_payload['text'], 'Cargando simulación...')

    # ==========================================
    # 2. Tests for What-If Simulator
    # ==========================================

    def test_calculate_projection(self):
        # Baseline: score 45.0, L_pts 10.0, C_pts 20.0, F_pts -4.0, fragility 0.5, ref_scale 50000
        delta_s, proj_score, l_gain, f_gain, c_gain = calculate_projection(
            amount=50000.0,
            current_score=45.0,
            liquidity_points=10.0,
            collections_points=20.0,
            fragility_points=-4.0,
            fragility=0.5,
            reference_scale=50000.0
        )
        self.assertGreater(delta_s, 0.0)
        self.assertEqual(proj_score, 45.0 + delta_s)
        self.assertGreater(l_gain, 0.0)
        self.assertGreater(f_gain, 0.0)
        self.assertGreater(c_gain, 0.0)
        self.assertLessEqual(proj_score, 100.0)

    def test_solve_optimal_injection(self):
        opt_amount = solve_optimal_injection(
            current_score=45.0,
            liquidity_points=15.0,
            collections_points=20.0,
            fragility_points=-4.0,
            fragility=0.5,
            reference_scale=50000.0,
            target_score=60.0
        )
        self.assertGreater(opt_amount, 0.0)
        # Verify that injecting opt_amount achieves >= 59.5 (due to rounding)
        _, proj, _, _, _ = calculate_projection(
            opt_amount, 45.0, 15.0, 20.0, -4.0, 0.5, 50000.0
        )
        self.assertGreaterEqual(proj, 59.0)

    def test_determine_projected_state(self):
        # Rescuing from DETERIORO when reaching >= 60.0
        st1 = determine_projected_state('DETERIORO', 28.0, 61.0, 33.0)
        self.assertEqual(st1, 'RECUPERACION')

        # Improving to ESTABLE
        st2 = determine_projected_state('DETERIORO', 35.0, 52.0, 17.0)
        self.assertEqual(st2, 'ESTABLE')

        # Stable remaining stable
        st3 = determine_projected_state('ESTABLE', 62.0, 75.0, 13.0)
        self.assertEqual(st3, 'ESTABLE')

    def test_select_recommended_product(self):
        prod_l, _ = select_recommended_product(liquidity_points=12.0, fragility_points=-1.0, collections_points=25.0)
        self.assertIn("Factoring", prod_l)

        prod_f, _ = select_recommended_product(liquidity_points=35.0, fragility_points=-5.5, collections_points=25.0)
        self.assertIn("Revolving", prod_f)

    def test_simulate_whatif_auto_amount(self):
        res = simulate_whatif('COMP_0010')
        self.assertIsNotNone(res)
        self.assertEqual(res['company_id'], 'COMP_0010')
        self.assertTrue(res['is_optimal_computed'])
        self.assertGreater(res['injection_amount'], 0)
        self.assertGreater(res['projected_score'], res['current_score'])
        self.assertIn('summary_html', res)
        self.assertIn('COMP_0010', res['summary_html'])
        self.assertIn('Nuevo Score Proyectado', res['summary_html'])
        self.assertIn('Embat', res['recommended_product'])

    def test_simulate_whatif_custom_amount(self):
        res = simulate_whatif('COMP_0010', injection_amount=75000.0)
        self.assertIsNotNone(res)
        self.assertEqual(res['injection_amount'], 75000.0)
        self.assertFalse(res['is_optimal_computed'])
        self.assertGreater(res['delta_score'], 0.0)

    def test_simulate_whatif_deterioro_rescue(self):
        # COMP_0059 is in DETERIORO
        res = simulate_whatif('COMP_0059')
        self.assertIsNotNone(res)
        self.assertEqual(res['current_state'], 'DETERIORO')
        self.assertIn(res['projected_state'], ('ESTABLE', 'RECUPERACION'))
        self.assertGreaterEqual(res['projected_score'], 55.0)

    def test_simulate_whatif_nonexistent_company(self):
        res = simulate_whatif('NON_EXISTENT_COMPANY_XYZ')
        self.assertIsNone(res)

    # ==========================================
    # 3. Tests for Trajectory Charts
    # ==========================================

    def test_generate_company_chart_png(self):
        png_bytes = generate_company_chart('COMP_0010')
        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 15000)
        # Check standard PNG header magic numbers
        self.assertTrue(png_bytes.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_generate_company_chart_normalized(self):
        # Support input without underscore e.g. comp0010
        png_bytes = generate_company_chart('comp0010')
        self.assertTrue(png_bytes.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_simulate_whatif_normalized(self):
        # Support input without underscore e.g. comp0010
        res = simulate_whatif('comp0010')
        self.assertIsNotNone(res)
        self.assertEqual(res['company_id'], 'COMP_0010')

    def test_projection_upper_bound_clamping(self):
        # Test company already near 100
        delta_s, proj_score, _, _, _ = calculate_projection(
            amount=500000.0,
            current_score=97.0,
            liquidity_points=48.0,
            collections_points=28.0,
            fragility_points=-0.2,
            fragility=0.02,
            reference_scale=50000.0
        )
        self.assertLessEqual(proj_score, 100.0)
        self.assertEqual(proj_score, 97.0 + delta_s)
        self.assertLessEqual(delta_s, 3.0)

    def test_generate_company_chart_deterioro(self):
        png_bytes = generate_company_chart('COMP_0059')
        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 15000)
        self.assertTrue(png_bytes.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_generate_company_chart_unknown_raises(self):
        with self.assertRaises(ValueError):
            generate_company_chart('COMP_9999_DOES_NOT_EXIST')

    # ==========================================
    # 4. Tests for Bot Routing and Helpers
    # ==========================================

    def test_parse_amount_variations(self):
        self.assertEqual(parse_amount('50000'), 50000.0)
        self.assertEqual(parse_amount('50k'), 50000.0)
        self.assertEqual(parse_amount('1.5m'), 1500000.0)
        self.assertEqual(parse_amount('50.000€'), 50000.0)
        self.assertEqual(parse_amount('50.000,50'), 50000.5)
        self.assertEqual(parse_amount('50,000'), 50000.0)
        self.assertEqual(parse_amount('50 000 €'), 50000.0)
        self.assertEqual(parse_amount('2,5 M €'), 2500000.0)
        self.assertIsNone(parse_amount('invalid_amount'))
        self.assertIsNone(parse_amount(''))

    @patch('algorythm.score_telegram_bot.send_chat_action')
    @patch('algorythm.score_telegram_bot.add_subscriber')
    @patch('algorythm.score_telegram_bot.handle_chart_query')
    @patch('algorythm.score_telegram_bot.answer_callback_query')
    def test_handle_callback_query_chart(self, mock_answer, mock_chart, mock_add_sub, mock_action):
        cb = {
            'id': 'cb_1001',
            'data': 'cb_chart:COMP_0010',
            'message': {'chat': {'id': 12345}}
        }
        handle_callback_query(cb)
        mock_answer.assert_called_once_with('cb_1001', text='⏳ Generando gráfica 24M de COMP_0010...')
        mock_chart.assert_called_once_with(12345, 'COMP_0010')
        mock_add_sub.assert_called_once_with(12345)

    @patch('algorythm.score_telegram_bot.send_chat_action')
    @patch('algorythm.score_telegram_bot.add_subscriber')
    @patch('algorythm.score_telegram_bot.handle_whatif_query')
    @patch('algorythm.score_telegram_bot.answer_callback_query')
    def test_handle_callback_query_whatif(self, mock_answer, mock_whatif, mock_add_sub, mock_action):
        cb = {
            'id': 'cb_1002',
            'data': 'cb_whatif:COMP_0010',
            'message': {'chat': {'id': 12345}}
        }
        handle_callback_query(cb)
        mock_answer.assert_called_once_with('cb_1002', text='⏳ Calculando simulación What-If de COMP_0010...')
        mock_whatif.assert_called_once_with(12345, 'COMP_0010', None)
        mock_add_sub.assert_called_once_with(12345)

    @patch('algorythm.score_telegram_bot.send_chat_action')
    @patch('algorythm.score_telegram_bot.add_subscriber')
    @patch('algorythm.score_telegram_bot.handle_score_query')
    @patch('algorythm.score_telegram_bot.answer_callback_query')
    def test_handle_callback_query_drivers(self, mock_answer, mock_score, mock_add_sub, mock_action):
        cb = {
            'id': 'cb_1003',
            'data': 'cb_drivers:COMP_0010',
            'message': {'chat': {'id': 12345}}
        }
        handle_callback_query(cb)
        mock_answer.assert_called_once_with('cb_1003', text='⏳ Extrayendo desglose Waterfall de COMP_0010...')
        mock_score.assert_called_once_with(12345, 'COMP_0010')
        mock_add_sub.assert_called_once_with(12345)


if __name__ == '__main__':
    unittest.main()
