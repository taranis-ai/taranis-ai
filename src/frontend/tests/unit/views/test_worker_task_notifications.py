import json
from types import SimpleNamespace
from typing import Any

from requests import Response

from frontend.cache import cache
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.views.base_view import BaseView


def _response(status_code: int, payload: dict[str, Any]) -> Response:
    response = Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode()
    response.headers["Content-Type"] = "application/json"
    return response


def test_worker_task_success_warns_when_no_workers(app: Any, monkeypatch: Any):
    monkeypatch.setattr(
        "frontend.views.base_view.DataPersistenceLayer",
        lambda: SimpleNamespace(get_core_health=lambda: SimpleNamespace(services=SimpleNamespace(workers="down"))),
    )

    with app.test_request_context("/"):
        html = BaseView.render_worker_task_notification(_response(200, {"message": "Refresh for source scheduled"}))

    assert "Refresh for source scheduled" in html
    assert "No workers are connected" in html
    assert "alert-warning" in html


def test_worker_task_success_stays_success_when_workers_are_up(app: Any, monkeypatch: Any):
    monkeypatch.setattr(
        "frontend.views.base_view.DataPersistenceLayer",
        lambda: SimpleNamespace(get_core_health=lambda: SimpleNamespace(services=SimpleNamespace(workers="up"))),
    )

    with app.test_request_context("/"):
        html = BaseView.render_worker_task_notification(_response(200, {"message": "Publishing Product scheduled"}))

    assert "Publishing Product scheduled" in html
    assert "No workers are connected" not in html
    assert "alert-success" in html


def test_worker_task_failure_keeps_error_notification(app: Any, monkeypatch: Any):
    monkeypatch.setattr(
        "frontend.views.base_view.DataPersistenceLayer",
        lambda: SimpleNamespace(get_core_health=lambda: (_ for _ in ()).throw(AssertionError("health should not be checked"))),
    )

    with app.test_request_context("/"):
        html = BaseView.render_worker_task_notification(_response(500, {"error": "Could not reach Redis"}))

    assert "Could not reach Redis" in html
    assert "alert-error" in html
    assert "No workers are connected" not in html


def test_core_api_health_parses_degraded_response(app: Any, responses_mock: Any):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/health",
        json={"healthy": False, "services": {"workers": "down"}},
        status=503,
    )

    with app.test_request_context("/"):
        assert CoreApi().get_health() == {"healthy": False, "services": {"workers": "down"}}


def test_worker_task_health_warning_uses_cached_health(app: Any, responses_mock: Any, test_cache_backend: Any):
    cache.clear()
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/health",
        json={
            "healthy": False,
            "services": {"database": "up", "seed_data": "up", "broker": "up", "workers": "down"},
        },
        status=503,
    )

    with app.test_request_context("/"):
        first = BaseView.render_worker_task_notification(_response(200, {"message": "Refresh for source scheduled"}))
        second = BaseView.render_worker_task_notification(_response(200, {"message": "Refresh for source scheduled"}))

    assert "No workers are connected" in first
    assert "No workers are connected" in second
    assert len(responses_mock.calls) == 1
