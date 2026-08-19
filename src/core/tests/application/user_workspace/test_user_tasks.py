import uuid
from datetime import UTC, datetime, timedelta


def _task_payload(job_id: str, *, user_id: str | None, status: str = "SUCCESS", worker_type: str = "presenter_task"):
    return {
        "id": job_id,
        "task": "user_task",
        "user_id": user_id,
        "worker_id": f"worker-{job_id}",
        "worker_type": worker_type,
        "result": {
            "message": f"Result for {job_id}",
            "reason": "render_failed" if status == "FAILURE" else None,
            "retryable": status == "FAILURE",
            "data": {"secret": f"hidden-{job_id}"},
        },
        "status": status,
    }


def _delete_tasks(app, job_ids: list[str]) -> None:
    from core.model.task import Task

    with app.app_context():
        for job_id in job_ids:
            if Task.get(job_id):
                Task.delete(job_id)


def test_user_tasks_returns_only_authenticated_users_completed_results(app, client, api_header, auth_header_user_permissions):
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("user")
        admin = User.find_by_name("admin")
        assert user is not None
        assert admin is not None

    own_job_id = f"user-task-{uuid.uuid4().hex}"
    preview_job_id = f"preview-task-{uuid.uuid4().hex}"
    active_job_id = f"active-task-{uuid.uuid4().hex}"
    other_job_id = f"other-task-{uuid.uuid4().hex}"
    job_ids = [own_job_id, preview_job_id, active_job_id, other_job_id]

    try:
        assert client.post("/api/tasks", json=_task_payload(own_job_id, user_id=user.id), headers=api_header).status_code == 200
        assert (
            client.post(
                "/api/tasks",
                json=_task_payload(preview_job_id, user_id=user.id, status="PREVIEW", worker_type="rss_collector"),
                headers=api_header,
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/tasks",
                json=_task_payload(active_job_id, user_id=user.id, status="STARTED"),
                headers=api_header,
            ).status_code
            == 200
        )
        assert client.post("/api/tasks", json=_task_payload(other_job_id, user_id=admin.id), headers=api_header).status_code == 200

        response = client.get("/api/tasks/user", headers=auth_header_user_permissions)

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total_count"] == 2
        items_by_job_id = {item["job_id"]: item for item in payload["items"]}
        assert set(items_by_job_id) == {own_job_id, preview_job_id}
        assert items_by_job_id[preview_job_id]["status"] == "PREVIEW"
        assert items_by_job_id[own_job_id]["result"] == {
            "message": f"Result for {own_job_id}",
            "reason": None,
            "retryable": False,
        }
        assert "user_id" not in items_by_job_id[own_job_id]
    finally:
        _delete_tasks(app, job_ids)


def test_user_tasks_supports_search_sorting_and_paging(app, client, api_header, auth_header_user_permissions):
    from core.managers.db_manager import db
    from core.model.task import Task
    from core.model.user import User

    with app.app_context():
        user = User.find_by_name("user")
        assert user is not None

    older_job_id = f"older-task-{uuid.uuid4().hex}"
    newer_job_id = f"newer-task-{uuid.uuid4().hex}"
    job_ids = [older_job_id, newer_job_id]

    try:
        assert (
            client.post(
                "/api/tasks",
                json=_task_payload(older_job_id, user_id=user.id, status="FAILURE", worker_type="pdf_presenter"),
                headers=api_header,
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/tasks",
                json=_task_payload(newer_job_id, user_id=user.id, worker_type="word_presenter"),
                headers=api_header,
            ).status_code
            == 200
        )

        with app.app_context():
            older = Task.get(older_job_id)
            newer = Task.get(newer_job_id)
            assert older is not None
            assert newer is not None
            older.last_run = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
            newer.last_run = datetime.now(UTC).replace(tzinfo=None)
            db.session.commit()

        paged = client.get(
            "/api/tasks/user",
            query_string={"page": 1, "limit": 1, "order": "last_run_asc"},
            headers=auth_header_user_permissions,
        )
        searched = client.get(
            "/api/tasks/user",
            query_string={"search": "pdf_presenter"},
            headers=auth_header_user_permissions,
        )
        hidden_data_search = client.get(
            "/api/tasks/user",
            query_string={"search": f"hidden-{older_job_id}"},
            headers=auth_header_user_permissions,
        )
        invalid = client.get(
            "/api/tasks/user",
            query_string={"page": "not-an-int", "limit": -1, "order": "not_valid"},
            headers=auth_header_user_permissions,
        )

        assert paged.status_code == 200
        assert paged.get_json()["total_count"] == 2
        assert [item["job_id"] for item in paged.get_json()["items"]] == [older_job_id]
        assert searched.status_code == 200
        assert [item["job_id"] for item in searched.get_json()["items"]] == [older_job_id]
        assert hidden_data_search.status_code == 200
        assert hidden_data_search.get_json() == {"items": [], "total_count": 0}
        assert invalid.status_code == 200
        assert invalid.get_json()["items"][0]["job_id"] == newer_job_id
    finally:
        _delete_tasks(app, job_ids)


def test_user_tasks_requires_authentication(client):
    assert client.get("/api/tasks/user").status_code == 401
