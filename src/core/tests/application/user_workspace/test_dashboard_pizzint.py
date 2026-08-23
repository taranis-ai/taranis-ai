from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from models.dashboard import PizzintStatus

from core.managers import queue_manager
from core.service import pizzint


NOW = datetime(2026, 8, 23, 9, 42, 39, tzinfo=UTC)
PAYLOAD = {
    "success": True,
    "data_freshness": "fresh",
    "defcon_level": 4,
    "defcon_details": {
        "at_time": "2026-08-23T09:00:00.000Z",
        "smoothed_index": 42.5,
        "reason": "compute_doughcon_v9: elevated",
    },
}
CACHE_KEYS = (pizzint.PIZZINT_CACHE_KEY, pizzint.PIZZINT_FRESH_KEY, pizzint.PIZZINT_REFRESH_KEY)


@pytest.fixture
def pizzint_request(app, monkeypatch):
    with app.app_context():
        queue_manager.queue_manager.redis.delete(*CACHE_KEYS)
    response = Mock()
    response.json.return_value = PAYLOAD
    request = Mock(return_value=response)
    monkeypatch.setattr(pizzint, "_utcnow", lambda: NOW)
    monkeypatch.setattr(pizzint.requests, "get", request)
    yield request
    with app.app_context():
        queue_manager.queue_manager.redis.delete(*CACHE_KEYS)


def test_pizzint_status_is_validated_and_cached(app, pizzint_request):
    with app.app_context():
        status = pizzint.get_pizzint_status()
        assert pizzint.get_pizzint_status() == status

    assert status.level == 4
    assert status.observed_at == datetime(2026, 8, 23, 9, tzinfo=UTC)
    pizzint_request.assert_called_once_with(
        pizzint.PIZZINT_API_URL,
        params={"_t": 1787478159000},
        headers={"User-Agent": "TaranisAI/1.0"},
        timeout=5,
    )


def test_invalid_pizzint_status_is_unavailable(app, pizzint_request):
    pizzint_request.return_value.json.return_value = PAYLOAD | {"defcon_level": 8}

    with app.app_context():
        assert pizzint.get_pizzint_status() == PizzintStatus()


def test_failed_refresh_returns_cached_status(app, pizzint_request):
    cached = PizzintStatus(
        state="fresh",
        level=5,
        smoothed_index=6.97,
        observed_at=NOW,
        fetched_at=NOW - timedelta(minutes=11),
        reason="compute_doughcon_v9: quiet",
    )
    pizzint_request.side_effect = RuntimeError("private upstream detail")

    with app.app_context():
        queue_manager.queue_manager.redis.set(
            pizzint.PIZZINT_CACHE_KEY,
            cached.model_dump_json(),
            ex=pizzint.PIZZINT_STALE_SECONDS,
        )
        assert pizzint.get_pizzint_status().state == "stale"
        assert pizzint.get_pizzint_status().reason == cached.reason

    pizzint_request.assert_called_once()
