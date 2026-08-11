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
    failed = _task_payload("task-failed")
    failed["status"] = "FAILURE"
    failed["result"] = {"message": "Rendering failed", "reason": "render_failed", "retryable": True}
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/tasks/user",
        json={"items": [_task_payload(), failed], "total_count": 2},
    )
    with authenticated_client_basic.application.app_context():
        url = url_for("user.tasks")

    response = authenticated_client_basic.get(url)

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Pdf Presenter" in body
    assert "Product rendered" in body
    assert "Success" in body
    assert "Failed" in body
    assert "Rendering failed" in body
    assert "Render Failed" in body
    assert "Retryable" in body
    assert 'data-testid="nav-my-tasks"' in body
    assert ">My Tasks</a>" in body


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


def test_my_tasks_htmx_failure_returns_sanitized_notification(authenticated_client_basic, htmx_header, monkeypatch):
    def fail_to_load_tasks(*args, **kwargs):
        raise RuntimeError("sensitive task loading details")

    monkeypatch.setattr("frontend.views.user_views.DataPersistenceLayer.get_objects", fail_to_load_tasks)
    with authenticated_client_basic.application.app_context():
        url = url_for("user.tasks")

    response = authenticated_client_basic.get(url, headers=htmx_header)

    assert response.status_code == 500
    body = response.get_data(as_text=True)
    assert "Failed to load tasks." in body
    assert "sensitive task loading details" not in body
