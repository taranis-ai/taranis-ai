import pytest

from core.service import health


@pytest.mark.parametrize(
    ("database_status", "seed_data_status", "broker_applicable", "broker_status", "workers_status", "expected"),
    [
        (
            "up",
            "up",
            True,
            "up",
            "up",
            {
                "status_code": 200,
                "body": {
                    "healthy": True,
                    "services": {"database": "up", "seed_data": "up", "broker": "up", "workers": "up"},
                },
            },
        ),
        (
            "down",
            "up",
            False,
            "up",
            "up",
            {
                "status_code": 503,
                "body": {
                    "healthy": False,
                    "services": {"database": "down", "seed_data": "down", "broker": "n/a", "workers": "n/a"},
                },
            },
        ),
        (
            "up",
            "down",
            False,
            "up",
            "up",
            {
                "status_code": 503,
                "body": {
                    "healthy": False,
                    "services": {"database": "up", "seed_data": "down", "broker": "n/a", "workers": "n/a"},
                },
            },
        ),
    ],
)
def test_get_health_response(
    monkeypatch,
    database_status,
    seed_data_status,
    broker_applicable,
    broker_status,
    workers_status,
    expected,
):
    monkeypatch.setattr("core.service.health.check_database", lambda: database_status)
    monkeypatch.setattr("core.service.health.check_seed_data", lambda: seed_data_status)
    monkeypatch.setattr("core.service.health.broker_health_applicable", lambda: broker_applicable)
    monkeypatch.setattr("core.service.health.check_broker", lambda: broker_status)
    monkeypatch.setattr("core.service.health.check_workers", lambda: workers_status)

    response_body, status_code = health.get_health_response()

    assert status_code == expected["status_code"]
    assert response_body == expected["body"]


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
