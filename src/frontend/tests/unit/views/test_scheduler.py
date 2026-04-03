from urllib.parse import urlparse

import pytest
from flask import url_for

from frontend.cache import cache


def _requested_core_paths(responses_mock):
    return [urlparse(call.request.url).path.removeprefix("/api") for call in responses_mock.calls]


@pytest.fixture(autouse=True)
def _clear_scheduler_cache():
    for key in list(cache.cache._cache.keys()):
        if not str(key).startswith("user_cache_"):
            cache.delete(key)
    yield
    for key in list(cache.cache._cache.keys()):
        if not str(key).startswith("user_cache_"):
            cache.delete(key)


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
def test_scheduler_deep_link_renders_dashboard(endpoint, expected_tab, authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert f'class="tab tab-active" data-tab="{expected_tab}"' in html
    assert f'id="{expected_tab}-tab" class="tab-panel ' in html
    assert f'id="{expected_tab}-tab" class="tab-panel hidden"' not in html


def test_scheduler_tab_query_param_overrides_initial(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs", tab="scheduled")

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'class="tab tab-active" data-tab="scheduled"' in html
    assert 'id="scheduled-tab" class="tab-panel hidden"' not in html


def test_scheduler_dashboard_uses_tab_scoped_refresh_triggers(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler")

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'id="queue-cards"' in html
    assert 'hx-trigger="every 10s"' in html
    assert 'id="scheduled-jobs-table"' in html
    assert 'id="active-jobs-table"' in html
    assert 'id="failed-jobs-table"' in html
    assert html.count('hx-trigger="scheduler:refresh"') == 3
    assert 'id="execution-history">' in html
    assert "window.htmx.trigger(target, 'scheduler:refresh');" in html


@pytest.mark.parametrize(
    ("endpoint", "expected_paths", "expected_text"),
    [
        ("admin.scheduler_jobs_table", ["/config/schedule"], "Total: 1 scheduled jobs"),
        ("admin.scheduler_queue_cards", ["/config/workers/tasks", "/config/workers/stats"], "Collectors"),
        ("admin.scheduler_active_jobs", ["/config/workers/active"], "Running Bot"),
        ("admin.scheduler_failed_jobs", ["/config/workers/failed"], "Failed Connector"),
        ("admin.scheduler_history", ["/config/task-results"], "Success Rate"),
    ],
)
def test_scheduler_htmx_partials_use_granular_endpoints(
    endpoint,
    expected_paths,
    expected_text,
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    assert _requested_core_paths(responses_mock) == expected_paths
    assert "/config/workers/dashboard" not in _requested_core_paths(responses_mock)
    assert expected_text in response.get_data(as_text=True)
