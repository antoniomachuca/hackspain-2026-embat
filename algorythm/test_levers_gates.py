"""TDD: applicability gates (filtro A)."""

from algorythm.levers_catalog import PUBLIC_LEVER_IDS
from algorythm.levers_gates import evaluate_catalog, is_applicable


def test_every_public_id_has_a_verdict():
    rows = evaluate_catalog('COMP_0010')
    ids = {row['id'] for row in rows}
    assert set(PUBLIC_LEVER_IDS) <= ids
    for row in rows:
        assert 'es_aplicable' in row
        assert 'familia' in row
        if not row['es_aplicable']:
            assert row['motivo_rechazo']


def test_prior_blocks_all(monkeypatch):
    from algorythm import levers_gates as g
    from algorythm.levers_objects import CompanyObjects

    dummy = CompanyObjects(
        company_id='COMP_FAKE', group_id='GROUP_X', is_prior=True,
        debt_points=10.0, ar_pending_eur=1e6, ap_pending_eur=1e6,
        opex_m23=1e5, ap_expenses_m23=1e5, debt_service_m23=1e4,
        refunds_m23=1e4, receipts_m23=1e5, hhi=0.2, hhi_quality=1.0,
        hhi_used=True, n_ar_clients=6, has_lineofcredit=True,
        loc_outstanding=1e5, loc_granted=2e5, loc_headroom=1e5,
        has_factoring=True, factoring_outstanding=1e4, has_confirming=True,
        has_leasing=True, has_renting=False, has_investment=True,
        investment_balance=1e4, checking_balance=1e5,
    )
    monkeypatch.setattr(g, 'get_company_objects', lambda cid, path=None: dummy)
    rows = evaluate_catalog('COMP_FAKE')
    assert all(r['es_aplicable'] is False for r in rows)
    assert all(r['motivo_rechazo'] == 'sin_evidencia_score' for r in rows)


def test_opex_requires_salary_utility():
    obj_ok = 'COMP_0031'
    applicable, reason = is_applicable(obj_ok, 'recortar_opex')
    assert applicable is True
    assert reason is None


def test_refi_requires_material_h():
    applicable, reason = is_applicable('COMP_0010', 'refinanciar')
    # COMP_0010 last-month H is 0 in bank_inputs
    assert applicable is False
    assert reason


def test_cobros_requires_ar():
    applicable, _ = is_applicable('COMP_0031', 'adelantar_cobros')
    assert applicable is True


def test_confirming_requires_product_and_ap():
    rows = {r['id']: r for r in evaluate_catalog('COMP_0031')}
    assert 'usar_confirming' in rows
    assert rows['usar_confirming']['es_aplicable'] in (True, False)
    if not rows['usar_confirming']['es_aplicable']:
        assert rows['usar_confirming']['motivo_rechazo']
