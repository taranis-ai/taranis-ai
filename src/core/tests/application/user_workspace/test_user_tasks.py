import uuid
from datetime import UTC, datetime, timedelta

import pytest
from redis.exceptions import RedisError
from rq.executions import Execution
from rq.job import JobStatus


@pytest.mark.parametrize("action,outcome", [("summary_bot", "SUCCESS"), ("generate_tags", "FAILURE")])
def test_story_task_lifecycle_is_visible_only_to_its_owner(
    app, client, session, redis_client, api_header, auth_header, auth_header_user_permissions, monkeypatch, action, outcome
):
    from core.model.user import User
    from tests.application.support.builders import build_news_item_payload, create_story

    story = create_story(news_items=[build_news_item_payload()])
    story_id = story.id
    user_id = User.find_by_name("user").id
    manager = app.extensions["rq"]
    queue = manager.get_queue("bots")
    history_id = f"previous-{story_id}"
    assert client.post("/api/tasks", json=_task_payload(history_id, user_id=user_id), headers=api_header).status_code == 200

    response = client.post(
        "/api/assess/stories/botactions", json={"story_id": story_id, "bot_id": action}, headers=auth_header_user_permissions
    )
    assert response.status_code == 200
    job = queue.get_jobs()[0]
    # Private queue configuration must never enter either public task projection.
    job.meta["checkpoint"] = {"secret": "private-provider-configuration"}
    job.save_meta()

    def unavailable_live_jobs(**kwargs):
        raise RedisError("Queue temporarily unavailable")

    with monkeypatch.context() as outage:
        outage.setattr(manager, "_live_jobs", unavailable_live_jobs)
        history = client.get("/api/tasks/user", query_string={"search": story_id}, headers=auth_header_user_permissions).json
        assert history["live_tasks_available"] is False
        assert [item["job_id"] for item in history["items"]] == [history_id]

    own = client.get("/api/tasks/user", query_string={"search": story_id}, headers=auth_header_user_permissions).json
    assert own["live_tasks_available"] is True
    assert own["total_count"] == 2
    live = next(item for item in own["items"] if item["job_id"] == job.id)
    assert live["status"] == "QUEUED"
    assert story_id in live["name"]
    expected_action = "Generate Tags" if action == "generate_tags" else "Summary"
    assert expected_action in live["name"]
    assert "private-provider-configuration" not in str(own)
    assert client.get("/api/tasks/user", query_string={"search": story_id}, headers=auth_header).json["total_count"] == 0

    scheduled = client.get("/api/config/schedule", query_string={"search": story_id}, headers=auth_header).json
    assert [item["id"] for item in scheduled["items"]] == [job.id]
    assert scheduled["items"][0]["name"] == live["name"]
    assert scheduled["items"][0]["status_badge"]["label"] == "Queued"
    assert manager.get_scheduled_job_count() == manager.get_scheduled_jobs({})[0]["total_count"]

    # RQ creates an execution and records STARTED before invoking the worker function.
    with redis_client.pipeline() as pipeline:
        Execution.create(job, ttl=300, pipeline=pipeline)
        job.prepare_for_execution("task-lifecycle-worker", pipeline=pipeline)
        pipeline.execute()
    running = client.get("/api/tasks/user", query_string={"search": story_id}, headers=auth_header_user_permissions).json
    assert next(item for item in running["items"] if item["job_id"] == job.id)["status"] == "RUNNING"
    assert client.get("/api/config/schedule", query_string={"search": story_id}, headers=auth_header).json["total_count"] == 0
    active = client.get("/api/config/workers/active", query_string={"search": story_id}, headers=auth_header).json
    assert [item["id"] for item in active["items"]] == [job.id]
    assert active["items"][0]["name"] == live["name"]

    payload = _task_payload(job.id, user_id=user_id, status=outcome)
    payload.update(task=job.meta["task"], worker_id=job.meta["worker_id"], worker_type=job.meta["worker_type"])
    assert client.post("/api/tasks", json=payload, headers=api_header).status_code == 200
    completed = client.get("/api/tasks/user", headers=auth_header_user_permissions).json["items"]
    assert [item["status"] for item in completed if item["job_id"] == job.id] == [outcome]
    assert history_id in {item["job_id"] for item in completed}
    assert client.get("/api/config/workers/active", query_string={"search": story_id}, headers=auth_header).json["total_count"] == 0

    job.set_status(JobStatus.FINISHED if outcome == "SUCCESS" else JobStatus.FAILED)
    job.delete()
    # A registry snapshot can still contain an ID whose job has disappeared.
    redis_client.rpush(queue.key, job.id)
    assert client.get("/api/tasks/user", query_string={"search": job.id}, headers=auth_header_user_permissions).json["total_count"] == 1


def test_user_tasks_page_live_jobs_together_with_history(app, client, session, redis_client, auth_header_user_permissions):
    from core.model.task import Task
    from core.model.user import User

    user = User.find_by_name("user")
    queue = app.extensions["rq"].get_queue("bots")
    now = datetime.now(UTC)
    worker_types = ["A", "B", "Z", None, "D", "C"]
    for index, worker_type in enumerate(worker_types):
        job_id = f"mixed-task-{index}"
        if index % 2:
            task = Task(**_task_payload(job_id, user_id=user.id))
            task.worker_type = worker_type
            task.last_run = (now + timedelta(seconds=index)).replace(tzinfo=None)
            session.add(task)
        else:
            job = queue.enqueue("worker.bots.bot_tasks.bot_task", job_id=job_id, meta={"user_id": user.id, "worker_type": worker_type})
            job.enqueued_at = now + timedelta(seconds=index)
            job.save()
    session.commit()

    for field, ascending in {"last_run": [0, 1, 2, 3, 4, 5], "worker_type": [3, 0, 1, 5, 4, 2]}.items():
        for direction in ("asc", "desc"):
            seen = []
            for page in range(1, 5):
                response = client.get(
                    "/api/tasks/user",
                    query_string={"search": "mixed-task", "limit": 2, "page": page, "order": f"{field}_{direction}"},
                    headers=auth_header_user_permissions,
                )
                assert response.status_code == 200
                assert response.json["total_count"] == 6
                seen.extend(item["job_id"] for item in response.json["items"])
            expected = ascending if direction == "asc" else ascending[::-1]
            assert seen == [f"mixed-task-{index}" for index in expected]


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


@pytest.mark.parametrize("status", ["SUCCESS", "WARNING"])
def test_user_tasks_returns_only_authenticated_users_completed_results(app, client, api_header, auth_header_user_permissions, status):
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
        assert (
            client.post("/api/tasks", json=_task_payload(own_job_id, user_id=user.id, status=status), headers=api_header).status_code == 200
        )
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
        assert hidden_data_search.get_json() == {"items": [], "total_count": 0, "live_tasks_available": True}
        assert invalid.status_code == 200
        assert invalid.get_json()["items"][0]["job_id"] == newer_job_id
    finally:
        _delete_tasks(app, job_ids)


def test_user_tasks_requires_authentication(client):
    assert client.get("/api/tasks/user").status_code == 401


def test_completed_runs_includes_background_jobs_and_filters_without_exposing_payloads(app, client, api_header):
    prefix = f"completed-{uuid.uuid4().hex}"
    job_ids = [f"{prefix}-{suffix}" for suffix in ("success", "failure", "active")]
    try:
        for job_id, status in zip(job_ids, ("SUCCESS", "FAILURE", "STARTED"), strict=True):
            payload = _task_payload(job_id, user_id=None, status=status)
            if status == "FAILURE":
                payload["result"].update(message="private traceback and provider secret", reason="job_timeout")
            assert client.post("/api/tasks", json=payload, headers=api_header).status_code == 200
        response = client.get("/api/tasks/runs", query_string={"search": prefix, "limit": 1}, headers=api_header)
        assert response.status_code == 200
        assert response.json["total_count"] == 2
        assert response.json["items"][0]["job_id"] == job_ids[1]
        assert response.json["items"][0]["result"]["message"] == "The job exceeded its execution timeout."
        assert "private traceback" not in response.text
        assert "secret" not in response.text
        assert "data" not in response.json["items"][0]["result"]
        success = client.get("/api/tasks/runs", query_string={"search": prefix, "status": "SUCCESS"}, headers=api_header)
        assert success.json["total_count"] == 1
        assert success.json["items"][0]["job_id"] == job_ids[0]
        assert client.get("/api/tasks/runs", query_string={"search": f"hidden-{prefix}"}, headers=api_header).json["total_count"] == 0
        invalid = client.get("/api/tasks/runs", query_string={"search": prefix, "status": "INVALID", "limit": -1}, headers=api_header)
        assert invalid.status_code == 200
        assert invalid.json["total_count"] == 2
        for number in range(100):
            job_id = f"{prefix}-extra-{number}"
            job_ids.append(job_id)
            assert client.post("/api/tasks", json=_task_payload(job_id, user_id=None), headers=api_header).status_code == 200
        bounded = client.get("/api/tasks/runs", query_string={"search": prefix, "limit": 100000000}, headers=api_header)
        assert bounded.status_code == 200
        assert bounded.json["total_count"] == 102
        assert len(bounded.json["items"]) == 100
        next_page = client.get("/api/tasks/runs", query_string={"search": prefix, "limit": 100000000, "page": 2}, headers=api_header)
        assert next_page.json["total_count"] == 102
        assert len(next_page.json["items"]) == 2
        assert {item["id"] for item in bounded.json["items"]}.isdisjoint(item["id"] for item in next_page.json["items"])
        assert client.get("/api/tasks/runs").status_code == 401
    finally:
        _delete_tasks(app, job_ids)
