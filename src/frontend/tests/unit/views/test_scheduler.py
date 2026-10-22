import json
from urllib.parse import parse_qs, urlparse

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
        ("admin.scheduler_history", "history"),
        ("admin.scheduler_completed_runs", "completed"),
    ],
)
def test_scheduler_deep_link_renders_dashboard(endpoint, expected_tab, authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    tree = lxml_html.fromstring(html)
    assert f'activeTab: "{expected_tab}"' in tree.xpath('//*[@id="scheduler-dashboard"]')[0].get("x-data")
    assert not tree.xpath(f'//*[@id="{expected_tab}-tab"]')[0].get("style")


def test_scheduler_tab_query_param_overrides_initial(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs", tab="scheduled")

    response = authenticated_client.get(url, headers={"HX-Request": "true", "HX-History-Restore-Request": "true"})

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    tree = lxml_html.fromstring(html)
    assert 'activeTab: "scheduled"' in tree.xpath('//*[@id="scheduler-dashboard"]')[0].get("x-data")
    assert not tree.xpath('//*[@id="scheduled-tab"]')[0].get("style")


def test_source_filters_preserve_each_other_and_table_query(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for(
            "admin.osint_sources",
            filter_manual="false",
            state="failure",
            search="source",
            page=3,
            limit=5,
            order="name_desc",
        )

    response = authenticated_client.get(url)

    assert response.status_code == 200
    tree = lxml_html.fromstring(response.get_data(as_text=True))
    status_form = tree.xpath('//*[@aria-label="Status"]/ancestor::form')[0]
    manual_form = tree.xpath('//*[@aria-label="Manual sources"]/ancestor::form')[0]
    status_values = {(item.get("name"), item.get("value")) for item in status_form.xpath('.//input[@type="hidden"]')}
    manual_values = {(item.get("name"), item.get("value")) for item in manual_form.xpath('.//input[@type="hidden"]')}
    expected_shared = {("search", "source"), ("limit", "5"), ("order", "name_desc")}
    assert expected_shared | {("filter_manual", "false")} <= status_values
    assert expected_shared | {("state", "failure")} <= manual_values
    assert status_form.xpath('.//*[@data-testid="status-filter-failed"][@checked]')
    assert not status_form.xpath('.//input[@name="page"]')
    assert not manual_form.xpath('.//input[@name="page"]')

    search_form = tree.xpath('//*[@id="osint_source-table-container-search"]/ancestor::form')[0]
    assert search_form.xpath('.//input[@type="hidden"][@name="state"][@value="failure"]')
    order_link = tree.xpath('//a[contains(@href, "order=")]')[0]
    limit_select = tree.xpath('//select[@name="limit"]')[0]
    assert parse_qs(urlparse(order_link.get("href")).query)["state"] == ["failure"]
    assert limit_select.xpath('ancestor::form//input[@type="hidden"][@name="state"][@value="failure"]')


def test_bot_table_query_preserves_failure_filter(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for("admin.bots", state="failure", search="bot", page=3, limit=5, order="name_desc")

    response = authenticated_client.get(url)

    assert response.status_code == 200
    tree = lxml_html.fromstring(response.get_data(as_text=True))
    status_form = tree.xpath('//*[@aria-label="Status"]/ancestor::form')[0]
    status_values = {(item.get("name"), item.get("value")) for item in status_form.xpath('.//input[@type="hidden"]')}
    assert {("search", "bot"), ("limit", "5"), ("order", "name_desc")} <= status_values
    assert status_form.xpath('.//*[@data-testid="status-filter-failed"][@checked]')
    assert not status_form.xpath('.//input[@name="page"]')

    search_form = tree.xpath('//*[@id="bot-table-container-search"]/ancestor::form')[0]
    assert search_form.xpath('.//input[@type="hidden"][@name="state"][@value="failure"]')
    order_link = tree.xpath('//a[contains(@href, "order=")]')[0]
    limit_select = tree.xpath('//select[@name="limit"]')[0]
    assert parse_qs(urlparse(order_link.get("href")).query)["state"] == ["failure"]
    assert limit_select.xpath('ancestor::form//input[@type="hidden"][@name="state"][@value="failure"]')


def test_scheduler_dashboard_refreshes_from_events_with_manual_fallback(authenticated_client, mock_core_get_endpoints):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler")

    response = authenticated_client.get(url)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    tree = lxml_html.fromstring(html)
    assert tree.xpath('//*[@id="scheduler-refresh"]')[0].text_content().strip() == "Refresh"
    for target in ("scheduler-dashboard", "queue-cards"):
        assert "realtime:scheduler.changed from:document" in tree.xpath(f'//*[@id="{target}"]')[0].get("hx-trigger")
        assert "realtime:resync from:document" in tree.xpath(f'//*[@id="{target}"]')[0].get("hx-trigger")
    assert "setInterval" not in html
    assert 'hx-trigger="every ' not in html


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
            "admin.scheduler_history",
            "/tasks",
            {"/config/schedule", "/config/workers/active", "/config/workers/failed"},
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
        ("admin.scheduler_history", ["/tasks"], "Success Rate"),
        ("admin.scheduler_completed_runs", ["/tasks/runs"], "Ran 4 bots"),
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


def test_active_jobs_refresh_confirms_observed_executions_across_batches(
    authenticated_client, responses_mock, mock_core_get_endpoints, htmx_header
):
    observed_jobs = [{"id": f"observed-{index}", "started_at": "2026-10-22T14:00:00+02:00"} for index in range(51)]
    saved_runs = {
        job_id: {
            "id": job_id,
            "job_id": job_id,
            "status": status,
            "last_run": completed_at,
            "result": {"message": "Recorded result"},
        }
        for job_id, status, completed_at in (
            ("observed-0", "SUCCESS", "2026-10-22T12:00:01"),
            ("observed-1", "SUCCESS", "2026-10-22T11:59:59Z"),
            ("observed-50", "FAILURE", "2026-10-22T12:00:00Z"),
        )
    }

    def completed_runs(core_request):
        job_ids = parse_qs(urlparse(core_request.url).query)["job_ids"]
        items = [saved_runs[job_id] for job_id in job_ids if job_id in saved_runs]
        return 200, {"Content-Type": "application/json"}, json.dumps({"items": items, "total_count": len(items)})

    responses_mock.remove(responses.GET, f"{Config.TARANIS_CORE_URL}/tasks/runs")
    responses_mock.add_callback(responses.GET, f"{Config.TARANIS_CORE_URL}/tasks/runs", callback=completed_runs)
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs", search="running", page=3, limit=5, order="name_desc")
    submitted_jobs = [*observed_jobs, observed_jobs[0], {"id": "missing-start"}]

    response = authenticated_client.post(url, data={"observed_jobs": json.dumps(submitted_jobs)}, headers=htmx_header)

    assert response.status_code == 200
    document = lxml_html.fromstring(response.text)
    table = document.xpath('//*[@id="active-jobs-table"]')[0]
    assert json.loads(table.get("data-completed-jobs")) == [observed_jobs[0], observed_jobs[50]]
    assert "Running Bot" in response.text
    assert "observed_jobs" not in table.get("data-refresh-url")
    calls = responses_mock.calls
    assert parse_qs(urlparse(calls[0].request.url).query) == {
        "search": ["running"],
        "page": ["3"],
        "limit": ["5"],
        "order": ["name_desc"],
    }
    for call, expected_ids in zip(calls[1:], [[job["id"] for job in observed_jobs[:50]], ["observed-50"]], strict=True):
        assert parse_qs(urlparse(call.request.url).query) == {"job_ids": expected_ids, "page": ["1"], "limit": ["50"]}

    # A later authoritative read can resolve a result that was missing during the first refresh.
    saved_runs["observed-2"] = {**saved_runs["observed-0"], "id": "observed-2", "job_id": "observed-2"}
    response = authenticated_client.post(url, data={"observed_jobs": json.dumps(submitted_jobs)}, headers=htmx_header)

    assert response.status_code == 200
    document = lxml_html.fromstring(response.text)
    assert json.loads(document.xpath('//*[@id="active-jobs-table"]')[0].get("data-completed-jobs")) == [
        observed_jobs[0],
        observed_jobs[2],
        observed_jobs[50],
    ]


def test_active_jobs_refresh_retains_active_table_when_completion_lookup_fails(
    authenticated_client, responses_mock, mock_core_get_endpoints, htmx_header
):
    responses_mock.replace(
        responses.GET,
        f"{Config.TARANIS_CORE_URL}/tasks/runs",
        json={"error": "private backend detail"},
        status=500,
    )
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs")
    data = {"observed_jobs": json.dumps([{"id": "observed-1", "started_at": "2026-10-22T12:00:00Z"}])}

    response = authenticated_client.post(url, data=data, headers=htmx_header)

    assert response.status_code == 200
    assert "Running Bot" in response.text
    assert "private backend detail" not in response.text
    document = lxml_html.fromstring(response.text)
    assert json.loads(document.xpath('//*[@id="active-jobs-table"]')[0].get("data-completed-jobs")) == []

    responses_mock.replace(responses.GET, f"{Config.TARANIS_CORE_URL}/tasks/runs", json={"error": "Access denied"}, status=403)
    response = authenticated_client.post(url, data=data, headers=htmx_header)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "observed_jobs",
    [
        "private malformed value",
        json.dumps([{"id": "observed-1", "started_at": "private malformed value"}]),
    ],
)
def test_active_jobs_refresh_rejects_invalid_observations(observed_jobs, authenticated_client, responses_mock, htmx_header):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs")

    response = authenticated_client.post(url, data={"observed_jobs": observed_jobs}, headers=htmx_header)

    assert response.status_code == 400
    assert "Invalid observed jobs." in response.text
    assert "private malformed value" not in response.text
    assert not responses_mock.calls


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


def test_scheduler_failed_jobs_renders_rq_error(authenticated_client, responses_mock, mock_core_get_endpoints, htmx_header):
    bot_name = "NER 'test' <script>alert(1)</script>"
    error = f"The job exceeded its execution timeout.\nExecution budget per attempt: 864 seconds\nFailed bot: {bot_name}"
    responses_mock.replace(
        responses.GET,
        f"{Config.TARANIS_CORE_URL}/config/workers/failed",
        json={
            "items": [{"id": "failed-1", "name": bot_name, "queue": "bots", "failed_at": "2025-01-01T11:50:00", "error": error}],
            "total_count": 1,
        },
    )
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_failed_jobs")

    response = authenticated_client.get(url, headers=htmx_header)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    document = lxml_html.fromstring(html)
    summary = document.xpath("//td/p")[0].text_content()
    assert summary == error.split("\n", 1)[0]
    handler = document.xpath("//button[contains(@onclick, 'showJobErrorModal')]/@onclick")[0]
    payload = json.loads(handler.removeprefix("window.showJobErrorModal(").removesuffix(")"))
    assert payload["error"] == error
    assert payload["name"] == bot_name
    assert "<script>alert(1)</script>" not in html


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
        ("admin.scheduler_history", "execution-history-jobs", "execution-history-table"),
        ("admin.scheduler_completed_runs", "completed-runs", "completed-runs-table"),
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
