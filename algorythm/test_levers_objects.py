"""TDD: company objects for lever gates and AR/AP selection."""

from datetime import date

from algorythm.levers_objects import (
    CUTOFF,
    CompanyObjects,
    build_lever_objects,
    get_company_objects,
    select_ar_advance,
)


def test_cutoff_is_official():
    assert CUTOFF == date(2026, 9, 1)


def test_comp_0010_has_ar_or_ap_or_bank_signal():
    obj = get_company_objects('COMP_0010')
    assert obj.company_id == 'COMP_0010'
    assert obj.group_id
    assert obj.ap_pending_eur >= 0 or obj.ar_pending_eur >= 0
    assert obj.ap_expenses_m23 >= 0


def test_comp_0031_has_material_ar_and_opex():
    obj = get_company_objects('COMP_0031')
    assert obj.ar_pending_eur > 10_000
    assert obj.opex_m23 > 1_000
    assert obj.debt_service_m23 > 0
    assert obj.is_prior is False


def test_unknown_company_raises():
    try:
        get_company_objects('COMP_9999')
    except KeyError:
        return
    raise AssertionError('expected KeyError')


def test_select_ar_advance_never_exceeds_pending():
    obj = get_company_objects('COMP_0031')
    for days in (7, 15, 30):
        picked = select_ar_advance(obj, days=days)
        assert 0 <= picked.amount_eur <= obj.ar_pending_eur + 1e-6
        assert picked.days == days


def test_select_ar_advance_monotone_in_days():
    obj = get_company_objects('COMP_0031')
    a7 = select_ar_advance(obj, days=7).amount_eur
    a15 = select_ar_advance(obj, days=15).amount_eur
    a30 = select_ar_advance(obj, days=30).amount_eur
    assert a7 <= a15 <= a30


def test_build_is_idempotent_cache():
    a = get_company_objects('COMP_0176')
    b = get_company_objects('COMP_0176')
    assert a.company_id == b.company_id
    assert a.has_lineofcredit == b.has_lineofcredit


def test_product_flags_are_bool():
    obj = get_company_objects('COMP_0010')
    for name in (
        'has_lineofcredit', 'has_factoring', 'has_confirming',
        'has_leasing', 'has_renting', 'has_investment',
    ):
        assert isinstance(getattr(obj, name), bool)


def test_build_lever_objects_roundtrip(tmp_path):
    dest = tmp_path / 'lever_objects.npz'
    path = build_lever_objects(destination=dest)
    assert path.exists()
    obj = get_company_objects('COMP_0010', path=dest)
    assert isinstance(obj, CompanyObjects)
    if obj.ar_invoices:
        assert any(inv.get('invoice_id') for inv in obj.ar_invoices)
