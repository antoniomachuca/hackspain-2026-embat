"""Telegram palancas presentation and callback routing."""

from unittest.mock import patch

from algorythm.telegram_levers import format_palancas_html, format_rankings_html, palancas_keyboard
from algorythm.telegram_notifier import build_alert_keyboard
from algorythm.score_telegram_bot import handle_callback_query


def test_alert_keyboard_includes_palancas():
    markup = build_alert_keyboard('COMP_0010')
    callbacks = [btn['callback_data'] for row in markup['inline_keyboard'] for btn in row]
    assert 'cb_whatif:COMP_0010' in callbacks
    assert 'cb_pal:COMP_0010' in callbacks
    assert 'cb_rank:COMP_0010' in callbacks
    assert 'cb_rec:COMP_0010' not in callbacks


def test_palancas_keyboard_bytes():
    markup = palancas_keyboard('COMP_0031')
    for row in markup['inline_keyboard']:
        for btn in row:
            assert len(btn['callback_data'].encode()) <= 64


def test_format_palancas_html():
    html = format_palancas_html('COMP_0010', [
        {'id': 'adelantar_cobros', 'familia': 'salud', 'es_aplicable': True},
        {'id': 'ampliar_dpo', 'familia': 'circulante', 'es_aplicable': True},
        {'id': 'refinanciar', 'familia': 'salud', 'es_aplicable': False, 'motivo_rechazo': 'sin_debt_service'},
    ])
    assert 'adelantar_cobros' in html
    assert 'ampliar_dpo' in html
    assert 'sin_debt_service' in html


def test_format_rankings_nulls_circulante_delta():
    html = format_rankings_html({
        'company_id': 'COMP_0031',
        'n_sims': 12,
        'modo': 'contrafactual_de_corte',
        'sugerencias': [{'id': 'adelantar_cobros', 'label': 'Adelantar cobros 15d', 'delta_score': 3.2, 'caja_liberada_eur': 1000, 'familia': 'salud'}],
        'opciones_circulante': [{'id': 'ampliar_dpo', 'label': 'Ampliar DPO', 'delta_score': None, 'caja_liberada_eur': 8000, 'familia': 'circulante'}],
        'recomendado': {'id': 'adelantar_cobros', 'label': 'Adelantar cobros 15d', 'familia': 'salud'},
    })
    assert 'ΔS nulo' in html
    assert 'Adelantar cobros' in html


def test_callback_palancas():
    with patch('algorythm.score_telegram_bot.send_chat_action'), \
         patch('algorythm.score_telegram_bot.add_subscriber'), \
         patch('algorythm.score_telegram_bot.handle_palancas_query') as mock_pal, \
         patch('algorythm.score_telegram_bot.answer_callback_query'):
        handle_callback_query({
            'id': 'cb_p',
            'data': 'cb_pal:COMP_0010',
            'message': {'chat': {'id': 99}},
        })
        mock_pal.assert_called_once_with(99, 'COMP_0010')


def test_callback_rank():
    with patch('algorythm.score_telegram_bot.send_chat_action'), \
         patch('algorythm.score_telegram_bot.add_subscriber'), \
         patch('algorythm.score_telegram_bot.handle_levers_rankings') as mock_rank, \
         patch('algorythm.score_telegram_bot.answer_callback_query'):
        handle_callback_query({
            'id': 'cb_r',
            'data': 'cb_rank:COMP_0031',
            'message': {'chat': {'id': 99}},
        })
        mock_rank.assert_called_once_with(99, 'COMP_0031')
