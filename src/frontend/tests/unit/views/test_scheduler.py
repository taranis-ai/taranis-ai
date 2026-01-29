import pytest
from flask import url_for

from frontend.cache_models import CacheObject
from frontend.views.admin_views import scheduler_views


@pytest.mark.parametrize(
    ("endpoint", "expected_tab"),
    [
        ("admin.scheduler", "scheduled"),
        ("admin.scheduler_jobs_table", "scheduled"),
        ("admin.scheduler_active_jobs", "active"),
        ("admin.scheduler_failed_jobs", "failed"),
        ("admin.scheduler_history", "history"),
    ],
)
def test_scheduler_deep_link_renders_dashboard(endpoint, expected_tab, authenticated_client, monkeypatch):
    def fake_api_get(self, endpoint_name, params=None):
        mapping = {
            "/config/schedule": {"items": [{"id": "job-1", "name": "Test Job", "queue": "default"}]},
            "/config/workers/tasks": [],
            "/config/workers/stats": {"workers": []},
        }
        return mapping.get(endpoint_name, {"items": []})

    def fake_get_objects(self, model, paging_data=None):
        return CacheObject([])

    monkeypatch.setattr(scheduler_views.CoreApi, "api_get", fake_api_get, raising=False)
    monkeypatch.setattr(scheduler_views.DataPersistenceLayer, "get_objects", fake_get_objects, raising=False)

    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert f'class="tab tab-active" data-tab="{expected_tab}"' in html
    assert f'id="{expected_tab}-tab" class="tab-panel ' in html
    assert f'id="{expected_tab}-tab" class="tab-panel hidden"' not in html


def test_scheduler_tab_query_param_overrides_initial(authenticated_client, monkeypatch):
    def fake_api_get(self, endpoint_name, params=None):
        mapping = {
            "/config/schedule": {"items": [{"id": "job-1", "name": "Test Job", "queue": "default"}]},
            "/config/workers/tasks": [],
            "/config/workers/stats": {"workers": []},
        }
        return mapping.get(endpoint_name, {"items": []})

    def fake_get_objects(self, model, paging_data=None):
        return CacheObject([])

    monkeypatch.setattr(scheduler_views.CoreApi, "api_get", fake_api_get, raising=False)
    monkeypatch.setattr(scheduler_views.DataPersistenceLayer, "get_objects", fake_get_objects, raising=False)

    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs", tab="scheduled")

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'class="tab tab-active" data-tab="scheduled"' in html
    assert 'id="scheduled-tab" class="tab-panel hidden"' not in html


@pytest.mark.parametrize(
    ("stats", "expected_label", "expected_variant"),
    [
        ({"successes": 3, "failures": 0, "total": 3}, "All Success", "success"),
        ({"successes": 0, "failures": 1, "total": 1}, "First Failure", "warning"),
        ({"successes": 8, "failures": 2, "total": 10, "success_pct": 80}, "Mostly Success", "warning"),
        ({"successes": 0, "failures": 2, "total": 2, "success_pct": 0}, "Some Failures", "warning"),
        ({"successes": 1, "failures": 5, "total": 6, "success_pct": 16}, "Many Failures", "error"),
    ],
)
def test_build_task_status_badge(stats, expected_label, expected_variant):
    badge = scheduler_views._build_task_status_badge(stats)

    assert badge["label"] == expected_label
    assert badge["variant"] == expected_variant
