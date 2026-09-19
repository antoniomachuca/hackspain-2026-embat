"""TDD for honest rescoring simulate_levers v2."""

from algorythm.levers import check_mutex, simulate_levers
from algorythm.bank_panels import get_company_bank_slice


def test_mutex_cobros_descuento():
    assert check_mutex(['adelantar_cobros', 'descuento_pronto_pago']) is not None
    assert check_mutex(['ampliar_dpo', 'usar_confirming']) is not None


def test_simulate_cobros_moves_score():
    result = simulate_levers(
        'COMP_0010',
        [{'id': 'adelantar_cobros', 'amount_eur': 50_000, 'agreement_type': 'presion_comercial'}],
    )
    assert result['ok'] is True
    assert result['delta_score'] is not None and result['delta_score'] > 0
    assert result['model_version']
    assert result['modo'] == 'contrafactual_de_corte'
    assert result['caja_liberada_eur'] == 50_000.0
    assert 'delta_bps' in result and result['delta_bps'] is None


def test_linea_returns_null_delta():
    result = simulate_levers('COMP_0004', [{'id': 'disponer_linea', 'amount_eur': 25_000}])
    assert result['ok'] is True
    assert result['delta_score'] is None
    assert result['caja_liberada_eur'] == 25_000.0


def test_inapplicable_refi_on_comp_0010():
    result = simulate_levers('COMP_0010', [{'id': 'refinanciar', 'pct': 0.2}])
    assert result['ok'] is False
    assert result['error'] == 'inaplicable'


def test_missing_agreement_rejected():
    result = simulate_levers('COMP_0010', [{'id': 'adelantar_cobros', 'amount_eur': 1000}])
    assert result['ok'] is False


def test_confirming_does_not_cut_expenses():
    bank_before = get_company_bank_slice('COMP_0004')
    exp0 = float(bank_before['expenses'][0, -1])
    result = simulate_levers('COMP_0004', [{'id': 'usar_confirming', 'pct': 0.2}])
    assert result['ok'] is True
    assert result['delta_score'] is None
    assert result['caja_liberada_eur'] > 0
    # rescoring uses a copy; original slice unchanged
    bank_after = get_company_bank_slice('COMP_0004')
    assert float(bank_after['expenses'][0, -1]) == exp0


def test_opex_sets_annual_euros():
    result = simulate_levers('COMP_0031', [{'id': 'recortar_opex', 'pct': 0.10}])
    assert result['ok'] is True
    assert result['eur_año'] is not None
    assert abs(result['eur_año'] - 12 * result['caja_liberada_eur']) < 1e-6


def test_dpo_does_not_fill_salud_delta():
    result = simulate_levers(
        'COMP_0010',
        [{'id': 'ampliar_dpo', 'pct': 0.2, 'agreement_type': 'acuerdo_negociado'}],
    )
    assert result['ok'] is True
    assert result['delta_score'] is None
    assert result['efecto_score_informativo'] is not None
