from forecasting.country import known_country, normalize_country


def test_spain_variants():
    assert normalize_country('España') == 'ES'
    assert normalize_country('ESPAÑA') == 'ES'
    assert normalize_country('ES') == 'ES'
    assert known_country('España')


def test_empty_none_garbage():
    assert normalize_country('') == ''
    assert normalize_country(None) == ''
    assert normalize_country('garbage') == ''
    assert not known_country('')
    assert not known_country(None)
    assert not known_country('garbage')


def test_portugal():
    assert normalize_country('Portugal') == 'PT'


def test_does_not_infer_from_eur():
    assert normalize_country('EUR') == ''
    assert not known_country('EUR')
