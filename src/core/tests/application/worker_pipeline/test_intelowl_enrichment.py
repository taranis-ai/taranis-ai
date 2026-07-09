import uuid
from typing import Any


def test_worker_stories_accept_story_ids_filter(client: Any, stories: list[str], api_header: dict[str, str]) -> None:
    response = client.get(
        "/api/worker/stories",
        headers=api_header,
        query_string=[("story_ids", stories[0]), ("story_ids", stories[1])],
    )

    assert response.status_code == 200
    assert {story["id"] for story in response.get_json()} == {stories[0], stories[1]}


def test_assess_botactions_accepts_multiple_stories_and_reports_for_non_intelowl(
    client: Any, auth_header: dict[str, str], monkeypatch: Any
) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_bot_task(bot_id: str, filter: dict[str, Any], user_id: str | None = None) -> tuple[dict[str, str], int]:
        captured["bot_id"] = bot_id
        captured["filter"] = filter
        return {"message": "queued"}, 200

    monkeypatch.setattr("core.api.assess.queue_manager.queue_manager.execute_bot_task", fake_execute_bot_task)

    response = client.post(
        "/api/assess/stories/botactions",
        json={"bot_id": "summary_bot", "story_ids": ["story-1", "story-2"], "report_ids": ["report-1"]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert captured == {
        "bot_id": "summary_bot",
        "filter": {"story_ids": ["story-1", "story-2"], "report_ids": ["report-1"]},
    }


def test_assess_botactions_queues_intelowl_like_any_other_bot(client: Any, auth_header: dict[str, str], monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_bot_task(bot_id: str, filter: dict[str, Any], user_id: str | None = None) -> tuple[dict[str, str], int]:
        captured["bot_id"] = bot_id
        captured["filter"] = filter
        return {"message": "queued"}, 200

    monkeypatch.setattr("core.api.assess.queue_manager.queue_manager.execute_bot_task", fake_execute_bot_task)

    response = client.post(
        "/api/assess/stories/botactions",
        json={"bot_id": "intel_owl_bot", "story_ids": ["story-1"], "report_ids": ["report-1"]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert captured == {
        "bot_id": "intel_owl_bot",
        "filter": {"story_id": "story-1", "report_ids": ["report-1"]},
    }


def test_analyze_report_botactions_accepts_multiple_reports_for_non_intelowl(
    client: Any, auth_header: dict[str, str], monkeypatch: Any
) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_bot_task(bot_id: str, filter: dict[str, Any], user_id: str | None = None) -> tuple[dict[str, str], int]:
        captured["bot_id"] = bot_id
        captured["filter"] = filter
        return {"message": "queued"}, 200

    monkeypatch.setattr("core.api.analyze.queue_manager.queue_manager.execute_bot_task", fake_execute_bot_task)

    response = client.post(
        "/api/analyze/report-items/botactions",
        json={"bot_id": "summary_bot", "report_ids": ["report-1", "report-2"]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert captured == {"bot_id": "summary_bot", "filter": {"report_ids": ["report-1", "report-2"]}}


def test_analyze_report_botactions_queues_intelowl_like_any_other_bot(client: Any, auth_header: dict[str, str], monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_bot_task(bot_id: str, filter: dict[str, Any], user_id: str | None = None) -> tuple[dict[str, str], int]:
        captured["bot_id"] = bot_id
        captured["filter"] = filter
        return {"message": "queued"}, 200

    monkeypatch.setattr("core.api.analyze.queue_manager.queue_manager.execute_bot_task", fake_execute_bot_task)

    response = client.post(
        "/api/analyze/report-items/botactions",
        json={"bot_id": "intel_owl_bot", "report_ids": ["report-1", "report-2"]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert captured == {"bot_id": "intel_owl_bot", "filter": {"report_ids": ["report-1", "report-2"]}}


def test_worker_task_results_upsert_intelowl_enrichment_and_cti_endpoints(
    client: Any,
    stories: list[str],
    cleanup_report_item: dict[str, Any],
    auth_header: dict[str, str],
    api_header: dict[str, str],
    app: Any,
) -> None:
    from core.managers.db_manager import db
    from core.model.asset import Asset
    from core.model.ioc import IOC
    from core.model.report_item import ReportItem
    from core.model.story import Story
    from core.model.task import Task

    task_id = f"intelowl-enrichment-{uuid.uuid4().hex}"
    story_id = stories[0]
    report_payload = dict(cleanup_report_item)
    report_payload["id"] = str(uuid.uuid4())
    report_payload["stories"] = [story_id]
    cve = "CVE-2024-1234"
    domain = "example.com"
    report_id = ""
    asset_id = ""
    news_item_id = ""
    updated_at = ""
    domain_updated_at = ""

    with app.app_context():
        story = Story.get(story_id)
        assert story is not None
        news_item = story.news_items[0]
        assert news_item.set_tags([{"name": cve, "tag_type": "cves"}], replace=False)[1] == 200
        report_obj, status = ReportItem.add(report_payload)
        assert status == 200
        assert isinstance(report_obj, ReportItem)
        report_id = report_obj.id
        asset = Asset(name="Affected host", serial="", description="", asset_observables=[{"ioc_type": "domain", "value": domain}])
        db.session.add(asset)
        db.session.flush()
        asset.add_vulnerability(report_obj)
        db.session.commit()
        asset_id = asset.id
        news_item_id = news_item.id

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
                            "type": "cve",
                            "value": cve,
                            "status": "reported_without_fails",
                            "analyzers": [{"name": "NVD_CVE", "status": "success", "report": {"score": 9.8}}],
                            "errors": [],
                            "submitted_at": "2026-07-06T10:00:00+00:00",
                            "completed_at": "2026-07-06T10:01:00+00:00",
                        },
                        {
                            "type": "domain",
                            "value": domain,
                            "status": "reported_without_fails",
                            "analyzers": [{"name": "ThreatFox", "status": "success", "report": {"malicious": False}}],
                            "errors": [],
                            "submitted_at": "2026-07-06T10:00:00+00:00",
                            "completed_at": "2026-07-06T10:01:00+00:00",
                        },
                    ],
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
            enrichment = IOC.get_by_ioc("cves", cve)
            assert enrichment is not None
            assert IOC.get_by_value(cve) == enrichment
            assert enrichment.status == "reported_without_fails"
            assert enrichment.analyzers == [{"name": "NVD_CVE", "status": "success", "report": {"score": 9.8}}]
            updated_at = enrichment.updated_at.isoformat()
            domain_enrichment = IOC.get_by_ioc("domain", domain)
            assert domain_enrichment is not None
            domain_updated_at = domain_enrichment.updated_at.isoformat()

        news_item_response = client.get(f"/api/assess/news-items/{news_item_id}/cti", headers=auth_header)
        story_response = client.get(f"/api/assess/stories/{story_id}/cti", headers=auth_header)
        report_response = client.get(f"/api/analyze/report-items/{report_id}/cti", headers=auth_header)
        asset_response = client.get(f"/api/assets/{asset_id}/cti", headers=auth_header)
        assets_response = client.get("/api/assets/cti", headers=auth_header)

        assert asset_response.get_json()["item_type"] == "asset"
        for cti_response in (news_item_response, story_response, report_response):
            assert cti_response.status_code == 200
            iocs = cti_response.get_json()["iocs"]
            assert iocs == [
                {
                    "ioc_type": "cve",
                    "value": cve,
                    "news_item_ids": [news_item_id],
                    "enrichment": {
                        "ioc_type": "cve",
                        "value": cve,
                        "status": "reported_without_fails",
                        "analyzers": [{"name": "NVD_CVE", "status": "success", "report": {"score": 9.8}}],
                        "errors": [],
                        "submitted_at": "2026-07-06T10:00:00",
                        "completed_at": "2026-07-06T10:01:00",
                        "updated_at": updated_at,
                    },
                }
            ]
        expected_asset_iocs = [
            {
                "ioc_type": "cve",
                "value": cve,
                "news_item_ids": [news_item_id],
                "enrichment": {
                    "ioc_type": "cve",
                    "value": cve,
                    "status": "reported_without_fails",
                    "analyzers": [{"name": "NVD_CVE", "status": "success", "report": {"score": 9.8}}],
                    "errors": [],
                    "submitted_at": "2026-07-06T10:00:00",
                    "completed_at": "2026-07-06T10:01:00",
                    "updated_at": updated_at,
                },
            },
            {
                "ioc_type": "domain",
                "value": domain,
                "news_item_ids": [],
                "enrichment": {
                    "ioc_type": "domain",
                    "value": domain,
                    "status": "reported_without_fails",
                    "analyzers": [{"name": "ThreatFox", "status": "success", "report": {"malicious": False}}],
                    "errors": [],
                    "submitted_at": "2026-07-06T10:00:00",
                    "completed_at": "2026-07-06T10:01:00",
                    "updated_at": domain_updated_at,
                },
            },
        ]
        assert asset_response.status_code == 200
        assert asset_response.get_json()["iocs"] == expected_asset_iocs
        assert assets_response.status_code == 200
        assert assets_response.get_json()["iocs"] == expected_asset_iocs
    finally:
        with app.app_context():
            if asset_id and (asset := Asset.get(asset_id)):
                db.session.delete(asset)
                db.session.commit()
            if Task.get(task_id):
                Task.delete(task_id)
            if enrichment := IOC.get_by_ioc("cves", cve):
                db.session.delete(enrichment)
                db.session.commit()
            if enrichment := IOC.get_by_ioc("domain", domain):
                db.session.delete(enrichment)
                db.session.commit()
            if report_id and ReportItem.get(report_id):
                ReportItem.delete(report_id)
