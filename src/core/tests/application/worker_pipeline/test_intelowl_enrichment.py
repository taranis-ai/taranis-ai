import uuid
from typing import Any


def test_worker_stories_accept_story_ids_filter(client: Any, stories: list[str], api_header: dict[str, str]) -> None:
    response = client.get(
        "/api/worker/stories",
        headers=api_header,
        query_string=[("story_ids", stories[0]), ("story_ids", stories[1])],
    )

    assert response.status_code == 200
    assert {story["id"] for story in response.get_json()} == set(stories[:2])


def test_intelowl_task_result_is_available_through_story_cti(
    client: Any,
    stories: list[str],
    auth_header: dict[str, str],
    api_header: dict[str, str],
    app: Any,
) -> None:
    from core.managers.db_manager import db
    from core.model.ioc import IOC
    from core.model.story import Story
    from core.model.task import Task

    task_id = f"intelowl-enrichment-{uuid.uuid4().hex}"
    story_id = stories[0]
    cve = "CVE-2024-1234"

    with app.app_context():
        story = Story.get(story_id)
        assert story is not None
        assert story.news_items[0].set_tags([{"name": cve, "tag_type": "cves"}], replace=False)[1] == 200

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
                    "enrichments": [
                        {
                            "ioc_type": "cve",
                            "value": cve,
                            "status": "reported_without_fails",
                            "analyzers": [{"name": "NVD_CVE", "status": "success", "report": {"score": 9.8}}],
                            "errors": [],
                        }
                    ],
                    "errors": [],
                },
            },
        },
        "status": "SUCCESS",
    }

    try:
        assert client.post("/api/tasks", json=payload, headers=api_header).status_code == 200

        response = client.get(f"/api/assess/stories/{story_id}/cti", headers=auth_header)
        assert response.status_code == 200
        ioc = response.get_json()["iocs"][0]
        assert ioc["value"] == cve
        assert ioc["enrichment"]["status"] == "reported_without_fails"
        assert ioc["enrichment"]["analyzers"][0]["name"] == "NVD_CVE"
    finally:
        with app.app_context():
            if Task.get(task_id):
                Task.delete(task_id)
            if enrichment := IOC.get_by_ioc("cve", cve):
                db.session.delete(enrichment)
                db.session.commit()
