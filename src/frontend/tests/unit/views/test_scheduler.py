from urllib.parse import urlparse

import pytest
import responses
from flask import url_for
from lxml import html as lxml_html
from models.user import ProfileSettings

from frontend.cache import add_user_to_cache, cache
from frontend.config import Config


def _requested_core_paths(responses_mock):
    return [urlparse(call.request.url).path.removeprefix("/api") for call in responses_mock.calls]


@pytest.fixture
def _clear_scheduler_cache():
    cache.clear()
    yield
    cache.clear()


pytestmark = pytest.mark.usefixtures("_clear_scheduler_cache")


@pytest.mark.parametrize(
    ("endpoint", "expected_tab"),
    [
        ("admin.scheduler", "scheduled"),
        ("admin.scheduler_jobs_table", "scheduled"),
        ("admin.scheduler_active_jobs", "active"),
        ("admin.scheduler_failed_jobs", "failed"),
        ("admin.scheduler_errors", "errors"),
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


def test_admin_sidebar_badges_link_to_worker_specific_errors_without_changing_main_links(
    authenticated_client,
    mock_core_get_endpoints,
):
    with authenticated_client.application.app_context():
        scheduler_url = url_for("admin.scheduler")
        source_url = url_for("admin.osint_sources")
        bot_url = url_for("admin.bots")
        source_errors_url = url_for("admin.osint_sources", filter_manual="false", state="failure")
        bot_errors_url = url_for("admin.bots", state="failure")

    response = authenticated_client.get(scheduler_url)

    assert response.status_code == 200
    tree = lxml_html.fromstring(response.get_data(as_text=True))
    source_link = tree.xpath('//*[@data-testid="admin-menu-OSINT Source"]')[0]
    bot_link = tree.xpath('//*[@data-testid="admin-menu-Bot"]')[0]
    source_error_link = tree.xpath('//*[@data-testid="admin-menu-OSINT Source-errors"]')[0]
    bot_error_link = tree.xpath('//*[@data-testid="admin-menu-Bot-errors"]')[0]
    assert source_link.get("href") == source_url
    assert bot_link.get("href") == bot_url
    assert source_error_link.get("href") == source_errors_url
    assert bot_error_link.get("href") == bot_errors_url
    assert source_error_link.getparent().tag == "li"
    assert bot_error_link.getparent().tag == "li"


@pytest.mark.parametrize(
    ("endpoint", "query", "message"),
    [
        ("admin.osint_sources", {"filter_manual": "false", "state": "failure"}, "Showing failed OSINT sources only"),
        ("admin.bots", {"state": "failure"}, "Showing failed bots only"),
    ],
)
def test_worker_failure_filter_can_be_cleared(endpoint, query, message, authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        filtered_url = url_for(endpoint, **query)
        unfiltered_url = url_for(endpoint)

    response = authenticated_client.get(filtered_url)

    assert response.status_code == 200
    tree = lxml_html.fromstring(response.get_data(as_text=True))
    banner = tree.xpath('//*[@data-testid="active-failure-filter"]')[0]
    clear_link = tree.xpath('//*[@data-testid="clear-failure-filter"]')[0]
    assert banner.text_content().strip().startswith(message)
    assert clear_link.get("href") == unfiltered_url
    assert clear_link.get("hx-get") == unfiltered_url

    unfiltered_response = authenticated_client.get(unfiltered_url)

    assert unfiltered_response.status_code == 200
    assert 'data-testid="active-failure-filter"' not in unfiltered_response.get_data(as_text=True)


def test_admin_sidebar_hides_zero_error_badges(authenticated_client, responses_mock, mock_core_get_endpoints):
    responses_mock.replace(
        responses.GET,
        f"{Config.TARANIS_CORE_URL}/config/admin-menu-badges",
        json={"osint_source": 0, "bot": 0},
    )
    with authenticated_client.application.app_context():
        scheduler_url = url_for("admin.scheduler")

    response = authenticated_client.get(scheduler_url)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-testid="admin-menu-OSINT Source"' in html
    assert 'data-testid="admin-menu-Bot"' in html
    assert 'data-testid="admin-menu-OSINT Source-errors"' not in html
    assert 'data-testid="admin-menu-Bot-errors"' not in html


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
    assert 'id="task-errors-panel"' in html
    assert ">Queue Failures</a>" in html
    assert ">Task Errors</a>" in html
    assert ">Failed Jobs</a>" not in html
    assert html.count('hx-trigger="scheduler:refresh"') == 5
    assert html.count("intervalMs: 10000") == 4
    assert "intervalMs: 5000" not in html
    assert 'id="execution-history"' in html


@pytest.mark.parametrize(
    ("endpoint", "selected_path", "inactive_paths"),
    [
        (
            "admin.scheduler",
            "/config/schedule",
            {"/config/workers/active", "/config/workers/failed", "/tasks"},
        ),
        (
            "admin.scheduler_active_jobs",
            "/config/workers/active",
            {"/config/schedule", "/config/workers/failed", "/tasks"},
        ),
        (
            "admin.scheduler_failed_jobs",
            "/config/workers/failed",
            {"/config/schedule", "/config/workers/active", "/tasks"},
        ),
        (
            "admin.scheduler_errors",
            "/tasks/errors",
            {"/config/schedule", "/config/workers/active", "/config/workers/failed", "/tasks"},
        ),
        (
            "admin.scheduler_history",
            "/tasks",
            {"/config/schedule", "/config/workers/active", "/config/workers/failed", "/tasks/errors"},
        ),
    ],
)
def test_scheduler_dashboard_initial_render_loads_only_selected_tab(
    endpoint,
    selected_path,
    inactive_paths,
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
):
    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url)

    assert response.status_code == 200
    requested_paths = _requested_core_paths(responses_mock)
    assert "/config/workers/dashboard" not in requested_paths
    assert "/config/workers/tasks" in requested_paths
    assert "/config/workers/stats" in requested_paths
    assert selected_path in requested_paths
    assert inactive_paths.isdisjoint(requested_paths)


def test_scheduler_dashboard_renders_inactive_tabs_as_placeholders(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler")

    response = authenticated_client.get(url)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-testid="scheduled-jobs"' in html
    assert 'id="active-jobs-table"' in html
    assert 'id="failed-jobs-table"' in html
    assert 'id="task-errors-panel"' in html
    assert 'id="execution-history"' in html
    assert html.count("Loading...</p>") == 4
    assert 'data-testid="active-jobs"' not in html
    assert 'data-testid="failed-jobs"' not in html
    assert 'data-testid="execution-history-jobs"' not in html


@pytest.mark.parametrize(
    ("endpoint", "expected_paths", "expected_text"),
    [
        ("admin.scheduler_jobs_table", ["/config/schedule"], "Items per page:"),
        ("admin.scheduler_queue_cards", ["/config/workers/tasks", "/config/workers/stats"], "Collectors"),
        ("admin.scheduler_active_jobs", ["/config/workers/active"], "Running Bot"),
        ("admin.scheduler_failed_jobs", ["/config/workers/failed"], "Failed Connector"),
        ("admin.scheduler_errors", ["/tasks/errors"], "404 Client Error"),
        ("admin.scheduler_history", ["/tasks"], "Success Rate"),
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


def test_scheduler_history_displays_worker_type_and_hover_worker_id(
    authenticated_client, responses_mock, mock_core_get_endpoints, htmx_header
):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_history")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "WORDLIST_BOT" in html
    assert 'title="Worker ID: bot-1"' in html


def test_scheduler_failed_jobs_renders_rq_error(authenticated_client, mock_core_get_endpoints, htmx_header):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_failed_jobs")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    assert "Boom" in response.get_data(as_text=True)


def test_scheduler_jobs_table_formats_next_run_in_profile_timezone(
    authenticated_client, responses_mock, mock_core_get_endpoints, htmx_header, auth_user
):
    job = {**mock_core_get_endpoints["Scheduler"]["items"][0], "next_run_time": "2025-01-01T12:00:00"}
    responses_mock.replace(
        responses.GET,
        mock_core_get_endpoints["Scheduler"]["_url"],
        json={"items": [job], "total_count": 1},
    )

    local_time_user = auth_user.model_copy(update={"profile": ProfileSettings(language="en", timezone="Europe/Vienna")})
    add_user_to_cache(local_time_user.model_dump(mode="json"))
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_jobs_table")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    assert "01. January 2025 13:00" in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("endpoint", "table_id", "container_id"),
    [
        ("admin.scheduler_jobs_table", "scheduled-jobs", "scheduled-jobs-table"),
        ("admin.scheduler_active_jobs", "active-jobs", "active-jobs-table"),
        ("admin.scheduler_failed_jobs", "failed-jobs", "failed-jobs-table"),
        ("admin.scheduler_errors", "task-errors", "task-errors-table"),
        ("admin.scheduler_history", "execution-history-jobs", "execution-history-table"),
    ],
)
def test_scheduler_tables_render_standard_controls(
    endpoint,
    table_id,
    container_id,
    authenticated_client,
    mock_core_get_endpoints,
    htmx_header,
):
    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'data-testid="{table_id}"' in html
    assert f'id="{container_id}"' in html
    assert 'placeholder="Search..."' in html
    assert "Items per page:" in html
    assert "Page 1 of" in html
    assert f'href="{url}?order=' in html


def test_scheduler_table_forwards_query_to_core(
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_jobs_table", search="collector", page=2, limit=5, order="name_desc")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    request_query = responses_mock.calls[-1].request.params
    assert request_query == {
        "search": "collector",
        "page": "2",
        "limit": "5",
        "order": "name_desc",
    }
    html = response.get_data(as_text=True)
    assert 'value="collector"' in html


def test_scheduler_table_leaves_default_order_to_core(
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_jobs_table")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    assert responses_mock.calls[-1].request.params == {}


def test_scheduler_history_filters_aggregate_rows(
    authenticated_client,
    mock_core_get_endpoints,
    htmx_header,
):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_history", search="wordlist")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "WORDLIST_BOT" in html
    assert "rss_collector" not in html


def test_scheduler_errors_forwards_filters_and_renders_persisted_error(
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_errors", scope="history", category="collector", search="missing")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    assert responses_mock.calls[-1].request.params == {
        "scope": "history",
        "category": "collector",
        "search": "missing",
    }
    html = response.get_data(as_text=True)
    assert "https://example.invalid/missing" in html
    assert "404 Client Error" in html
    assert 'aria-label="Error scope"' in html


@pytest.mark.parametrize("order", ["successes_asc", "failures_asc", "success_pct_asc"])
def test_scheduler_history_sorts_statistics_numerically(
    order,
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    history = {
        "items": [],
        "total_count": 0,
        "task_stats": {
            "task-two": {
                "worker_type": "Task Two",
                "worker_id": "worker-two",
                "last_run": "2026-01-01T00:00:00Z",
                "successes": 2,
                "failures": 2,
                "total": 4,
                "success_pct": 2,
            },
            "task-ten": {
                "worker_type": "Task Ten",
                "worker_id": "worker-ten",
                "last_run": "2026-01-02T00:00:00Z",
                "successes": 10,
                "failures": 10,
                "total": 20,
                "success_pct": 10,
            },
        },
        "totals": {"successes": 12, "failures": 12, "overall_success_rate": 50},
    }
    responses_mock.replace(responses.GET, f"{Config.TARANIS_CORE_URL}/tasks", json=history)
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_history", order=order)

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.index("Task Two") < html.index("Task Ten")


def test_scheduler_history_uses_default_slice_for_negative_paging(
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    history = {
        "items": [],
        "total_count": 0,
        "task_stats": {
            f"task-{index:02d}": {
                "worker_type": f"Task {index:02d}",
                "worker_id": f"worker-{index:02d}",
                "last_run": f"2026-01-{(index % 28) + 1:02d}T00:00:00Z",
                "successes": index,
                "failures": 0,
                "total": index,
                "success_pct": 100,
            }
            for index in range(21)
        },
        "totals": {"successes": 210, "failures": 0, "overall_success_rate": 100},
    }
    responses_mock.replace(responses.GET, f"{Config.TARANIS_CORE_URL}/tasks", json=history)
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_history", order="task_asc", page=-1, limit=-1)

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'title="Worker ID: worker-00"' in html
    assert 'title="Worker ID: worker-19"' in html
    assert 'title="Worker ID: worker-20"' not in html


def test_scheduler_history_uses_default_order_for_invalid_direction(
    authenticated_client,
    responses_mock,
    mock_core_get_endpoints,
    htmx_header,
):
    history = {
        "items": [],
        "total_count": 0,
        "task_stats": {
            "older": {
                "worker_type": "Older Task",
                "worker_id": "older",
                "last_run": "2026-01-01T00:00:00Z",
            },
            "newer": {
                "worker_type": "Newer Task",
                "worker_id": "newer",
                "last_run": "2026-01-02T00:00:00Z",
            },
        },
        "totals": {},
    }
    responses_mock.replace(responses.GET, f"{Config.TARANIS_CORE_URL}/tasks", json=history)
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_history", order="successes_sideways")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.index("Newer Task") < html.index("Older Task")
