"""TDD for honest rescoring simulate_levers v2."""

from algorythm.levers import check_mutex, simulate_levers
from algorythm.bank_panels import get_company_bank_slice
from algorythm.levers_objects import get_company_objects


def test_mutex_refi_family_only():
    assert check_mutex(['adelantar_cobros', 'descuento_pronto_pago']) is None
    assert check_mutex(['ampliar_dpo', 'usar_confirming']) is None
    assert check_mutex(['refinanciar', 'leasing_a_cuota_menor']) is not None


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


def test_tasa_descuento_is_a_field_not_a_lever():
    base = simulate_levers(
        'COMP_0010',
        [{'id': 'adelantar_cobros', 'amount_eur': 50_000, 'agreement_type': 'presion_comercial'}],
    )
    discounted = simulate_levers(
        'COMP_0010',
        [{'id': 'adelantar_cobros', 'amount_eur': 50_000, 'tasa_descuento': 0.02}],
    )
    assert base['ok'] is True and discounted['ok'] is True
    assert base['caja_liberada_eur'] == 50_000.0
    assert abs(discounted['caja_liberada_eur'] - 49_000.0) < 1e-6
    assert 'descuento_supuesto' in discounted['warnings']


def test_descuento_alias_still_simulates():
    result = simulate_levers(
        'COMP_0010',
        [{'id': 'descuento_pronto_pago', 'amount_eur': 10_000}],
    )
    assert result['ok'] is True
    assert abs(result['caja_liberada_eur'] - 9_800.0) < 1e-6


def _two_ar_clients(company_id: str) -> tuple[str, ...]:
    obj = get_company_objects(company_id)
    clients = []
    seen = set()
    for inv in obj.ar_invoices:
        cp = str(inv.get('counterparty_id') or '')
        if cp and cp not in seen:
            seen.add(cp)
            clients.append(cp)
        if len(clients) >= 2:
            break
    return tuple(clients)


def test_disjoint_client_lines_are_allowed():
    clients = _two_ar_clients('COMP_0004')
    assert len(clients) >= 2
    result = simulate_levers(
        'COMP_0004',
        [{
            'id': 'adelantar_cobros',
            'agreement_type': 'presion_comercial',
            'lineas': [
                {'clientes': [clients[0]], 'dias': 15, 'tasa_descuento': 0.0},
                {'clientes': [clients[1]], 'dias': 7, 'tasa_descuento': 0.02},
            ],
        }],
    )
    assert result['ok'] is True
    assert result['caja_liberada_eur'] >= 0


def test_disjoint_factura_lines_are_allowed():
    obj = get_company_objects('COMP_0004')
    ids = [str(inv['invoice_id']) for inv in obj.ar_invoices if inv.get('invoice_id')][:2]
    assert len(ids) == 2
    result = simulate_levers(
        'COMP_0004',
        [{
            'id': 'adelantar_cobros',
            'agreement_type': 'presion_comercial',
            'lineas': [
                {'facturas': [ids[0]], 'dias': 15, 'tasa_descuento': 0.0},
                {'facturas': [ids[1]], 'dias': 7, 'tasa_descuento': 0.02},
            ],
        }],
    )
    assert result['ok'] is True
    assert result['caja_liberada_eur'] > 0


def test_shared_factura_lines_are_422():
    obj = get_company_objects('COMP_0031')
    invoice_id = next((str(inv['invoice_id']) for inv in obj.ar_invoices if inv.get('invoice_id')), '')
    if not invoice_id:
        client = next(str(inv['counterparty_id']) for inv in obj.ar_invoices if inv.get('counterparty_id'))
        result = simulate_levers(
            'COMP_0031',
            [{
                'id': 'adelantar_cobros',
                'agreement_type': 'presion_comercial',
                'lineas': [
                    {'clientes': [client], 'dias': 15, 'tasa_descuento': 0.0},
                    {'clientes': [client], 'dias': 30, 'tasa_descuento': 0.02},
                ],
            }],
        )
    else:
        result = simulate_levers(
            'COMP_0031',
            [{
                'id': 'adelantar_cobros',
                'agreement_type': 'presion_comercial',
                'lineas': [
                    {'facturas': [invoice_id], 'dias': 15, 'tasa_descuento': 0.0},
                    {'facturas': [invoice_id], 'dias': 7, 'tasa_descuento': 0.02},
                ],
            }],
        )
    assert result['ok'] is False
    assert result['error'] == 'doble_conteo'
    assert result.get('resource_key')


def test_xor_facturas_y_clientes_en_linea():
    result = simulate_levers(
        'COMP_0031',
        [{
            'id': 'adelantar_cobros',
            'agreement_type': 'presion_comercial',
            'lineas': [{'facturas': ['x'], 'clientes': ['y'], 'dias': 15}],
        }],
    )
    assert result['ok'] is False
    assert result['error'] == 'linea_facturas_o_clientes'


def test_ap_levers_conflict_only_on_shared_invoices():
    stacked = simulate_levers(
        'COMP_0010',
        [
            {'id': 'ampliar_dpo', 'pct': 0.2, 'agreement_type': 'acuerdo_negociado'},
            {'id': 'ofrecer_pronto_pago_proveedor', 'pct': 0.2, 'agreement_type': 'acuerdo_negociado'},
        ],
    )
    assert stacked['ok'] is False
    assert stacked['error'] == 'doble_conteo'
