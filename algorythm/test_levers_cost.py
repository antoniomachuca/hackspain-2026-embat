"""TDD: D2C/D3C proposed cost numbers."""

from algorythm.levers_cost import (
    TIPO_REF_ANUAL,
    caja_neta,
    discount_buttons,
    dpo_cost_buttons,
    floor_pct,
    impacto_anual_eur,
    validate_agreement,
)


def test_floor_pct_15_days_is_about_12_bps():
    value = floor_pct(15)
    assert abs(value - TIPO_REF_ANUAL * 15 / 365) < 1e-12
    assert 0.0011 < value < 0.0014


def test_discount_buttons_respect_floor_and_caps():
    buttons = discount_buttons(15)
    pcts = [b['pct'] for b in buttons]
    assert pcts[0] >= max(floor_pct(15), 0.005) - 1e-12
    assert pcts[-1] <= 0.03 + 1e-12
    assert pcts == sorted(pcts)


def test_dpo_cost_buttons_are_positive():
    buttons = dpo_cost_buttons(15)
    assert all(b['pct'] > 0 for b in buttons)
    assert all(b['pct'] <= 0.03 for b in buttons)


def test_caja_neta_rejects_negative():
    assert caja_neta(1000, 0.02) == 980.0
    assert caja_neta(100, 1.5) == 0.0


def test_impacto_anual_is_twelve_months():
    assert impacto_anual_eur(1000) == 12_000.0


def test_validate_agreement_cobros_requires_type():
    ok, reason = validate_agreement('adelantar_cobros', None)
    assert ok is False
    assert reason

    ok, reason = validate_agreement('adelantar_cobros', 'presion_comercial')
    assert ok is True

    ok, reason = validate_agreement('descuento_pronto_pago', 'presion_comercial')
    assert ok is True

    ok, reason = validate_agreement('descuento_pronto_pago', 'descuento_pronto_pago')
    assert ok is True

    ok, reason = validate_agreement('adelantar_cobros', None, params={'tasa_descuento': 0.02})
    assert ok is True


def test_validate_agreement_dpo():
    ok, _ = validate_agreement('ampliar_dpo', 'acuerdo_negociado')
    assert ok is True
    ok, _ = validate_agreement('ampliar_dpo', 'presion_comercial')
    assert ok is False


def test_opex_needs_no_agreement():
    ok, _ = validate_agreement('recortar_opex', None)
    assert ok is True
