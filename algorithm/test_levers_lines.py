"""TDD: cobros/AP lines and resource_key overlap."""

from algorithm.levers_catalog import canonical_lever_id, PUBLIC_LEVER_IDS
from algorithm.levers_lines import check_resource_overlap, normalize_lineas
from algorithm.levers_objects import CompanyObjects


def _obj(**kwargs) -> CompanyObjects:
    base = dict(
        company_id='COMP_FAKE', group_id='GROUP_X', is_prior=False,
        debt_points=10.0, ar_pending_eur=300.0, ap_pending_eur=200.0,
        opex_m23=1e5, ap_expenses_m23=1e5, debt_service_m23=1e4,
        refunds_m23=1e4, receipts_m23=1e5, hhi=0.2, hhi_quality=1.0,
        hhi_used=True, n_ar_clients=2, has_lineofcredit=True,
        loc_outstanding=1e5, loc_granted=2e5, loc_headroom=1e5,
        has_factoring=True, factoring_outstanding=1e4, has_confirming=True,
        has_leasing=True, has_renting=False, has_investment=True,
        investment_balance=1e4, checking_balance=1e5,
        ar_invoices=(
            {'invoice_id': 'AR1', 'pending_amount': 100.0, 'due_date': '2026-09-10', 'counterparty_id': 'C1'},
            {'invoice_id': 'AR2', 'pending_amount': 200.0, 'due_date': '2026-09-20', 'counterparty_id': 'C2'},
        ),
        ap_invoices=(
            {'invoice_id': 'AP1', 'pending_amount': 80.0, 'due_date': '2026-09-10', 'counterparty_id': 'P1'},
            {'invoice_id': 'AP2', 'pending_amount': 120.0, 'due_date': '2026-09-20', 'counterparty_id': 'P2'},
        ),
    )
    base.update(kwargs)
    return CompanyObjects(**base)


def test_descuento_is_alias_not_public():
    assert canonical_lever_id('descuento_pronto_pago') == 'adelantar_cobros'
    assert 'descuento_pronto_pago' not in PUBLIC_LEVER_IDS
    assert 'adelantar_cobros' in PUBLIC_LEVER_IDS


def test_normalize_top_level_into_one_line():
    lines = normalize_lineas({'dias': 15, 'tasa_descuento': 0.02, 'clientes': ['C1']})
    assert len(lines) == 1
    assert lines[0]['clientes'] == ['C1']


def test_overlap_same_factura():
    obj = _obj()
    err = check_resource_overlap(obj, [{
        'id': 'adelantar_cobros',
        'lineas': [
            {'facturas': ['AR1'], 'dias': 15, 'tasa_descuento': 0.0},
            {'facturas': ['AR1'], 'dias': 7, 'tasa_descuento': 0.02},
        ],
    }])
    assert err is not None
    assert err['error'] == 'doble_conteo'
    assert err['resource_key'] == 'invoice:AR1'


def test_disjoint_facturas_ok():
    obj = _obj()
    err = check_resource_overlap(obj, [{
        'id': 'adelantar_cobros',
        'lineas': [
            {'facturas': ['AR1'], 'dias': 15, 'tasa_descuento': 0.0},
            {'facturas': ['AR2'], 'dias': 7, 'tasa_descuento': 0.02},
        ],
    }])
    assert err is None


def test_client_line_overlaps_factura_of_that_client():
    obj = _obj()
    err = check_resource_overlap(obj, [{
        'id': 'adelantar_cobros',
        'lineas': [
            {'clientes': ['C1'], 'dias': 30},
            {'facturas': ['AR1'], 'dias': 15},
        ],
    }])
    assert err is not None
    assert err['error'] == 'doble_conteo'
    assert err['resource_key'] == 'invoice:AR1'


def test_xor_targets():
    obj = _obj()
    err = check_resource_overlap(obj, [{
        'id': 'adelantar_cobros',
        'lineas': [{'facturas': ['AR1'], 'clientes': ['C2'], 'dias': 15}],
    }])
    assert err is not None
    assert err['error'] == 'linea_facturas_o_clientes'


def test_unknown_factura():
    obj = _obj()
    err = check_resource_overlap(obj, [{
        'id': 'adelantar_cobros',
        'lineas': [{'facturas': ['NOPE'], 'dias': 15}],
    }])
    assert err is not None
    assert err['error'] == 'factura_desconocida'
    assert err['resource_key'] == 'NOPE'


def test_ap_disjoint_allows_dpo_and_pronto_pago():
    obj = _obj()
    err = check_resource_overlap(obj, [
        {'id': 'ampliar_dpo', 'lineas': [{'facturas': ['AP1'], 'dias': 15}]},
        {'id': 'ofrecer_pronto_pago_proveedor', 'lineas': [{'facturas': ['AP2'], 'dias': 7, 'tasa_descuento': 0.02}]},
    ])
    assert err is None


def test_ap_pool_conflicts_without_lineas():
    obj = _obj()
    err = check_resource_overlap(obj, [
        {'id': 'ampliar_dpo', 'pct': 0.2},
        {'id': 'usar_confirming', 'pct': 0.2},
    ])
    assert err is not None
    assert err['error'] == 'doble_conteo'
    assert str(err['resource_key']).startswith('invoice:AP')
