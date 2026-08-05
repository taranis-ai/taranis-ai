from urllib.parse import urlparse

from flask import url_for

from frontend.config import Config


def _task_payload(job_id: str = "task-1") -> dict:
    return {
        "id": job_id,
        "job_id": job_id,
        "task": "presenter_task",
        "worker_id": "product-1",
        "worker_type": "pdf_presenter",
        "result": {"message": "Product rendered", "reason": None, "retryable": False},
        "status": "SUCCESS",
        "last_run": "2026-08-05T10:00:00Z",
    }


def test_my_tasks_renders_standard_table_for_basic_user(authenticated_client_basic, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/tasks/user",
        json={"items": [_task_payload()], "total_count": 1},
    )
    with authenticated_client_basic.application.app_context():
        url = url_for("user.tasks")

    response = authenticated_client_basic.get(url)

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-testid="my-tasks-page"' in body
    assert 'data-testid="user-tasks"' in body
    assert "Pdf Presenter" in body
    assert "Product rendered" in body
    assert 'placeholder="Search..."' in body
    assert "Items per page:" in body
    assert "Page 1 of 1" in body
    assert f'href="{url}?order=' in body


def test_my_tasks_forwards_table_query_to_core(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/tasks/user",
        json={"items": [_task_payload()], "total_count": 1},
    )
    with authenticated_client_basic.application.app_context():
        url = url_for("user.tasks", search="render", page=2, limit=5, order="last_run_asc")

    response = authenticated_client_basic.get(url, headers=htmx_header)

    assert response.status_code == 200
    assert 'id="user-tasks-table-container"' in response.get_data(as_text=True)
    core_call = responses_mock.calls[-1]
    assert urlparse(core_call.request.url).path.endswith("/tasks/user")
    assert core_call.request.params == {
        "search": "render",
        "page": "2",
        "limit": "5",
        "order": "last_run_asc",
    }


def test_my_tasks_renders_empty_state(authenticated_client_basic, responses_mock):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/tasks/user", json={"items": [], "total_count": 0})
    with authenticated_client_basic.application.app_context():
        url = url_for("user.tasks")

    response = authenticated_client_basic.get(url)

    assert response.status_code == 200
    assert 'data-testid="empty-user-tasks"' in response.get_data(as_text=True)


def test_my_tasks_renders_failure_reason_and_retryability(authenticated_client_basic, responses_mock):
    failed = _task_payload("task-failed")
    failed["status"] = "FAILURE"
    failed["result"] = {"message": "Rendering failed", "reason": "render_failed", "retryable": True}
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/tasks/user", json={"items": [failed], "total_count": 1})
    with authenticated_client_basic.application.app_context():
        url = url_for("user.tasks")

    response = authenticated_client_basic.get(url)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Failed" in body
    assert "Render Failed" in body
    assert "Retryable" in body


def test_my_tasks_navbar_link(app):
    with app.test_request_context("/"):
        from flask import render_template

        body = render_template("partials/navbar.html", is_admin=False)

    assert 'data-testid="nav-my-tasks"' in body
    assert ">My Tasks</a>" in body
