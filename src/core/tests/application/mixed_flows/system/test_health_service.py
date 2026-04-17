import pytest

from core.service import health


@pytest.mark.parametrize(
    ("manual_exists", "product_type_exists", "expected"),
    [
        (True, True, "up"),
        (False, True, "down"),
        (True, False, "down"),
        (False, False, "down"),
    ],
)
def test_check_seed_data(monkeypatch, manual_exists, product_type_exists, expected):
    monkeypatch.setattr("core.model.osint_source.OSINTSource.get", lambda source_id: object() if manual_exists else None)
    monkeypatch.setattr("core.model.product_type.ProductType.get_first", lambda query: object() if product_type_exists else None)

    assert health.check_seed_data() == expected
