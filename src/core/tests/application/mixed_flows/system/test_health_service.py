from types import SimpleNamespace

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


def test_broker_health_applicable_uses_redis_url(monkeypatch):
    qm = type("QueueManagerStub", (), {"redis_url": "redis://localhost:6379/0", "_redis": None})()
    monkeypatch.setattr(health, "queue_manager", SimpleNamespace(queue_manager=qm))

    assert health.broker_health_applicable() is True


def test_check_broker_uses_redis_ping(monkeypatch):
    class FakeRedis:
        def ping(self):
            return True

    qm = type("QueueManagerStub", (), {"_redis": FakeRedis()})()
    monkeypatch.setattr(health, "queue_manager", SimpleNamespace(queue_manager=qm))

    assert health.check_broker() == "up"


def test_check_workers_uses_rq_workers(monkeypatch):
    qm = type("QueueManagerStub", (), {"_redis": object()})()
    monkeypatch.setattr(health, "queue_manager", SimpleNamespace(queue_manager=qm))
    monkeypatch.setattr("rq.worker.Worker.all", lambda connection=None: [object()])

    assert health.check_workers() == "up"
