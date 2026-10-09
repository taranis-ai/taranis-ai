"""Bot DAG transaction and retry behavior at the worker API boundary."""

import uuid

from tests.application.support.builders import build_news_item_payload, create_osint_source, create_story


def test_bot_pipeline_uses_one_snapshot_and_commits_only_complete_runs(app, client, api_header, session):
    with app.app_context():
        if session.get_bind().dialect.name == "sqlite":
            session.get_bind().exec_driver_sql("BEGIN")
        session().join_transaction_mode = "create_savepoint"
        from core.model.bot import Bot
        from core.model.news_item import NewsItem
        from core.model.story import Story
        from core.model.task import Task

        source = create_osint_source(rank=0)
        first_payload = build_news_item_payload(source.id, title="First story")
        first = create_story(news_items=[first_payload])
        second = create_story(news_items=[build_news_item_payload(source.id, title="Second story")])
        unrelated = create_story(news_items=[build_news_item_payload(source.id, title="Unrelated source story")])
        first_item_id = first.news_items[0].id
        second_item_id = second.news_items[0].id
        bot_ids = {bot_type: Bot.filter_by_type(bot_type.lower()).id for bot_type in ("NLP_BOT", "STORY_BOT", "SUMMARY_BOT", "IOC_BOT")}
        filters = {
            bot_id: {"source": [source.id], "story_ids": [first.id, second.id], "worker": True, "exclude_attr": bot_type}
            for bot_type, bot_id in bot_ids.items()
        }
        snapshot_response = client.post("/api/worker/bot-pipeline/stories", json={"filters": filters}, headers=api_header)
        assert snapshot_response.status_code == 200
        snapshot = snapshot_response.json
        assert {story["id"] for story in snapshot["stories"]} == {first.id, second.id}
        assert all(set(ids) == {first.id, second.id} for ids in snapshot["selected"].values())
        limited = client.post(
            "/api/worker/bot-pipeline/stories",
            json={"filters": {bot_ids["STORY_BOT"]: {"source": source.id, "limit": "5", "worker": True}}},
            headers=api_header,
        )
        assert limited.status_code == 200
        assert len(limited.json["stories"]) == 3

        stages = [
            {
                "bot_id": bot_ids["NLP_BOT"],
                "bot_type": "NLP_BOT",
                "story_ids": [first.id, second.id],
                "result": {first_item_id: {"CVE-2026-1234": "cves"}, second_item_id: {"CVE-2026-5678": "cves"}},
            },
            {
                "bot_id": bot_ids["STORY_BOT"],
                "bot_type": "STORY_BOT",
                "story_ids": [first.id, second.id],
                "result": {"message": "Grouped", "changes": {"groups": [[first.id, second.id]]}},
            },
            {
                "bot_id": bot_ids["SUMMARY_BOT"],
                "bot_type": "SUMMARY_BOT",
                "story_ids": [first.id],
                "result": {
                    "message": "Summarized",
                    "changes": {
                        "story_updates": {first.id: {"summary": "Combined summary", "title": "Combined title"}},
                    },
                },
            },
            {"bot_id": bot_ids["IOC_BOT"], "bot_type": "IOC_BOT", "story_ids": [first.id], "result": {}},
        ]
        payload = {
            "id": str(uuid.uuid4()),
            "task": "bot_pipeline",
            "worker_type": "BOT_PIPELINE",
            "status": "SUCCESS",
            "result": {
                "message": "Pipeline complete",
                "data": {"bot_stages": stages, "story_revisions": snapshot["revisions"], "trigger_dependents": False},
            },
        }

        invalid_payload = {
            **payload,
            "id": str(uuid.uuid4()),
            "result": {
                **payload["result"],
                "data": {
                    **payload["result"]["data"],
                    "bot_stages": [stages[0], {**stages[1], "result": {"changes": {"groups": [[first.id, "unknown"]]}}}],
                },
            },
        }
        for invalid_stage in (
            invalid_payload["result"]["data"]["bot_stages"][1],
            {**stages[1], "story_ids": [unrelated.id]},
        ):
            invalid_payload["result"]["data"]["bot_stages"] = [stages[0], invalid_stage]
            invalid = client.post("/api/tasks", json=invalid_payload, headers=api_header)
            assert invalid.status_code == 400
            assert NewsItem.get(first_item_id).tags == []
            assert Story.get(first.id).revision == snapshot["revisions"][first.id]
            assert Task.get_by_job_id(invalid_payload["id"]) is None

        committed = client.post("/api/tasks", json=payload, headers=api_header)
        assert committed.status_code == 200
        assert Story.get(second.id) is None
        merged = Story.get(first.id)
        assert {item.id for item in merged.news_items} == {first_item_id, second_item_id}
        assert merged.title == "Combined title"
        assert merged.summary == "Combined summary"
        assert all(merged.find_attribute_by_key(bot_type) for bot_type in bot_ids)
        assert "|count=0|" in merged.find_attribute_by_key("IOC_BOT").value
        assert all(Story.get(unrelated.id).find_attribute_by_key(bot_type) is None for bot_type in bot_ids)
        assert {tag.name for tag in NewsItem.get(first_item_id).tags} == {"CVE-2026-1234"}
        assert {tag.name for tag in NewsItem.get(second_item_id).tags} == {"CVE-2026-5678"}
        revision = merged.revision
        assert client.post("/api/tasks", json=payload, headers=api_header).status_code == 200
        assert Story.get(first.id).revision == revision

        # Successful bots, including a zero-finding IOC run, are omitted from the next scoped snapshot.
        repeated = client.post("/api/worker/bot-pipeline/stories", json={"filters": filters}, headers=api_header)
        assert repeated.status_code == 200
        assert repeated.json["stories"] == []
        assert all(ids == [] for ids in repeated.json["selected"].values())
        forced = client.get("/api/worker/stories", query_string={"story_id": first.id}, headers=api_header)
        assert forced.status_code == 200
        assert forced.json[0]["id"] == first.id

        changed = client.post("/api/worker/news-items", json=[{**first_payload, "content": "Changed after the pipeline"}], headers=api_header)
        assert changed.status_code == 200
        assert changed.json["story_ids"] == [first.id]
        refreshed = client.post("/api/worker/bot-pipeline/stories", json={"filters": filters}, headers=api_header)
        assert refreshed.status_code == 200
        assert {story["id"] for story in refreshed.json["stories"]} == {first.id}
        assert all(ids == [first.id] for ids in refreshed.json["selected"].values())

        revision = Story.get(first.id).revision
        stale = client.post("/api/tasks", json={**payload, "id": str(uuid.uuid4())}, headers=api_header)
        assert stale.status_code == 409
        assert Story.get(first.id).revision == revision
