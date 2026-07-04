import uuid
from typing import Any, cast


def test_worker_stories_accept_story_ids_filter(client: Any, stories: list[str], api_header: dict[str, str]) -> None:
    response = client.get(
        "/api/worker/stories",
        headers=api_header,
        query_string=[("story_ids", stories[0]), ("story_ids", stories[1])],
    )

    assert response.status_code == 200
    assert {story["id"] for story in response.get_json()} == {stories[0], stories[1]}


def test_assess_botactions_accepts_multiple_stories_and_reports(client: Any, auth_header: dict[str, str], monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_bot_task(bot_id: str, filter: dict[str, Any]) -> tuple[dict[str, str], int]:
        captured["bot_id"] = bot_id
        captured["filter"] = filter
        return {"message": "queued"}, 200

    monkeypatch.setattr("core.api.assess.queue_manager.queue_manager.execute_bot_task", fake_execute_bot_task)

    response = client.post(
        "/api/assess/stories/botactions",
        json={"bot_id": "intelowl", "story_ids": ["story-1", "story-2"], "report_ids": ["report-1"]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert captured == {
        "bot_id": "intelowl",
        "filter": {"story_ids": ["story-1", "story-2"], "report_ids": ["report-1"]},
    }


def test_analyze_report_botactions_accepts_multiple_reports(client: Any, auth_header: dict[str, str], monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_bot_task(bot_id: str, filter: dict[str, Any]) -> tuple[dict[str, str], int]:
        captured["bot_id"] = bot_id
        captured["filter"] = filter
        return {"message": "queued"}, 200

    monkeypatch.setattr("core.api.analyze.queue_manager.queue_manager.execute_bot_task", fake_execute_bot_task)

    response = client.post(
        "/api/analyze/report-items/botactions",
        json={"bot_id": "intelowl", "report_ids": ["report-1", "report-2"]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert captured == {"bot_id": "intelowl", "filter": {"report_ids": ["report-1", "report-2"]}}


def test_worker_task_results_apply_intelowl_story_attribute(
    client: Any,
    stories: list[str],
    auth_header: dict[str, str],
    api_header: dict[str, str],
    app: Any,
) -> None:
    from core.model.task import Task

    task_id = f"intelowl-story-{uuid.uuid4().hex}"
    story_id = stories[0]
    summary = "IntelOwl enrichment: cve CVE-2024-1234 accepted job 1 https://intelowl.example/jobs/1"
    payload = {
        "id": task_id,
        "task": "bot_intelowl",
        "worker_id": "intelowl",
        "worker_type": "INTEL_OWL_BOT",
        "result": {
            "message": "IntelOwl enrichment submitted",
            "retryable": False,
            "data": {
                "bot_id": "intelowl",
                "result": {
                    "stories": {story_id: {"attribute": {"key": "intelowl_enrichment", "value": summary}}},
                    "reports": {},
                    "observables": {},
                    "skipped": [],
                    "errors": [],
                },
            },
        },
        "status": "SUCCESS",
    }

    try:
        response = client.post("/api/tasks", json=payload, headers=api_header)

        assert response.status_code == 200
        story_response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        assert story_response.status_code == 200
        attr_by_key = {attribute["key"]: attribute["value"] for attribute in story_response.get_json()["attributes"]}
        assert attr_by_key["intelowl_enrichment"] == summary
        assert attr_by_key["INTEL_OWL_BOT"].startswith("worker_id=intelowl|")
    finally:
        with app.app_context():
            if Task.get(task_id):
                Task.delete(task_id)


def test_worker_task_results_apply_intelowl_report_attribute(
    client: Any,
    cleanup_report_item: dict[str, Any],
    api_header: dict[str, str],
    app: Any,
) -> None:
    from core.managers.db_manager import db
    from core.model.attribute import AttributeType
    from core.model.report_item import ReportItem, ReportItemAttribute
    from core.model.task import Task

    task_id = f"intelowl-report-{uuid.uuid4().hex}"
    report_payload = dict(cleanup_report_item)
    report_payload["id"] = str(uuid.uuid4())
    summary = "IntelOwl enrichment: cve CVE-2024-1234 accepted job 1 https://intelowl.example/jobs/1"

    with app.app_context():
        report_obj, status = ReportItem.add(report_payload)
        report = cast(ReportItem, report_obj)
        assert status == 200
        report.attributes.append(ReportItemAttribute(title="IntelOwl Enrichment", value="", attribute_type=AttributeType.TEXT, index=99))
        db.session.commit()
        report_id = report.id

    payload = {
        "id": task_id,
        "task": "bot_intelowl",
        "worker_id": "intelowl",
        "worker_type": "INTEL_OWL_BOT",
        "result": {
            "message": "IntelOwl enrichment submitted",
            "retryable": False,
            "data": {
                "bot_id": "intelowl",
                "result": {
                    "stories": {},
                    "reports": {report_id: {"attribute_title": "IntelOwl Enrichment", "value": summary}},
                    "observables": {},
                    "skipped": [],
                    "errors": [],
                },
            },
        },
        "status": "SUCCESS",
    }

    try:
        response = client.post("/api/tasks", json=payload, headers=api_header)

        assert response.status_code == 200
        with app.app_context():
            attribute = ReportItemAttribute.find_attribute_by_title(report_id, "IntelOwl Enrichment")
            assert attribute is not None
            assert attribute.value == summary
    finally:
        with app.app_context():
            if Task.get(task_id):
                Task.delete(task_id)
            if ReportItem.get(report_id):
                ReportItem.delete(report_id)
