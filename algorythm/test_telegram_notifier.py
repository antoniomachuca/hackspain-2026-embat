import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from algorythm.telegram_notifier import (
    format_alert_html, add_subscriber, load_subscribers,
    save_subscribers, broadcast_alert, load_config
)


class TestTelegramNotifier(unittest.TestCase):

    def test_format_alert_html_deterioration(self):
        alert = {
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
                {'field': 'collections_points', 'delta_points': -6.20}
            ]
        }
        html = format_alert_html(alert)
        self.assertIn('COMP_0010', html)
        self.assertIn('46.16', html)
        self.assertIn('-30.88', html)
        self.assertIn('DETERIORO', html)
        self.assertIn('Liquidez y Margen', html)
        self.assertIn('Cobros y ERP', html)

    def test_format_alert_html_improvement(self):
        alert = {
            'company_id': 'COMP_0055',
            'group_id': 'GROUP_0055',
            'as_of': '2026-09-01',
            'comparison_as_of': '2026-06-01',
            'state': 'MEJORANDO',
            'severity': 'MEDIA',
            'direction': 'improvement',
            'score': 72.50,
            'delta_score': 15.20,
            'momentum': 0.180,
            'drivers': [
                {'field': 'growth_points', 'delta_points': 8.50}
            ]
        }
        html = format_alert_html(alert)
        self.assertIn('COMP_0055', html)
        self.assertIn('+15.20', html)
        self.assertIn('MEJORANDO', html)

    def test_subscriber_management(self):
        original = load_subscribers()
        try:
            saved = save_subscribers(['12345', '67890'])
            self.assertIn('12345', saved)
            self.assertIn('67890', saved)
            
            updated = add_subscriber('99999')
            self.assertIn('99999', updated)
        finally:
            save_subscribers(original)

    @patch('urllib.request.urlopen')
    def test_broadcast_alert_mocked(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'ok': True, 'result': {'message_id': 101}}).encode('utf-8')
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
        res = broadcast_alert(alert, subscribers=['12345'])
        self.assertEqual(res.get('sent'), 1)
        self.assertEqual(res.get('failed'), 0)


if __name__ == '__main__':
    unittest.main()
