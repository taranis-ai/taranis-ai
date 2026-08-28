# pyright: reportAttributeAccessIssue=false
import importlib.util
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest


def _tag_names(tags: list[dict] | dict[str, dict]) -> set[str]:
    if isinstance(tags, dict):
        tags = list(tags.values())
    return {tag["name"] for tag in tags}


def _expected_story_tag_names(story: dict) -> set[str]:
    return {tag["name"] for item in story.get("news_items", []) for tag in item.get("tags", [])}


class TestWorkerApi:
    base_uri = "/api/worker"

    def test_rss_source_includes_global_entry_limit(self, client, api_header, fake_source, monkeypatch):
        monkeypatch.setattr(
            "core.model.osint_source.Settings.get_settings",
            lambda: {"collector_max_entries": 17},
        )

        response = client.get(f"{self.base_uri}/osint-sources/{fake_source}", headers=api_header)

        assert response.status_code == 200
        assert response.get_json()["collector_max_entries"] == 17

    def test_mastodon_cursor_comes_from_latest_task_result(self, client, api_header, app):
        from core.model.osint_source import OSINTSource
        from core.model.task import Task

        source_id = str(uuid.uuid4())
        task_ids = [f"collect_mastodon_collector_{source_id}", f"cron_osint_source_{source_id}_{uuid.uuid4().hex}"]
        cursor = {
            "timeline": "https://mastodon.example|hashtag|security",
            "last_status_id": "123",
        }
        payload = {
            "id": task_ids[0],
            "task": "collector_task",
            "worker_id": source_id,
            "worker_type": "mastodon_collector",
            "result": {"message": "Collected", "data": {"source_id": source_id, "mastodon_cursor": cursor}},
            "status": "SUCCESS",
        }

        try:
            with app.app_context():
                OSINTSource.add(
                    {
                        "id": source_id,
                        "name": "Mastodon cursor test",
                        "description": "Mastodon cursor test",
                        "type": "mastodon_collector",
                        "parameters": {
                            "INSTANCE_URL": "https://mastodon.example",
                            "TIMELINE": "hashtag",
                            "HASHTAG": "security",
                        },
                    }
                )

            response = client.post("/api/tasks", json=payload, headers=api_header)
            assert response.status_code == 200

            source_response = client.get(f"{self.base_uri}/osint-sources/{source_id}", headers=api_header)
            assert source_response.status_code == 200
            assert source_response.get_json()["mastodon_cursor"] == cursor

            malformed = {
                **payload,
                "id": task_ids[1],
                "result": {"message": "Ignored", "data": {"mastodon_cursor": {"last_status_id": 124}}},
            }
            assert client.post("/api/tasks", json=malformed, headers=api_header).status_code == 200

            source_response = client.get(f"{self.base_uri}/osint-sources/{source_id}", headers=api_header)
            assert source_response.status_code == 200
            assert "mastodon_cursor" not in source_response.get_json()
        finally:
            with app.app_context():
                for task_id in task_ids:
                    if Task.get(task_id):
                        Task.delete(task_id)
                if OSINTSource.get(source_id):
                    OSINTSource.delete(source_id)

    def test_bot_story_query_uses_default_lookback_setting(self, client, api_header, monkeypatch):
        captured_filter = {}
        current_time = datetime(2026, 8, 12, 12, 0)

        monkeypatch.setattr("core.api.worker.Settings.get_settings", lambda: {"default_bot_lookback_days": 5})
        monkeypatch.setattr("core.api.worker.Story.utcnow", lambda: current_time)

        def capture_filter(filter_args):
            captured_filter.update(filter_args)
            return [{"id": "story-1"}]

        monkeypatch.setattr("core.api.worker.Story.get_for_worker", capture_filter)

        response = client.get(
            f"{self.base_uri}/stories",
            query_string={"worker": "true", "exclude_attr": "ANALYST_BOT"},
            headers=api_header,
        )

        assert response.status_code == 200
        assert captured_filter["timefrom"] == "2026-08-07T12:00:00"

    def test_zero_bot_lookback_does_not_apply_timefrom(self, client, api_header, monkeypatch):
        captured_filter = {}

        monkeypatch.setattr("core.api.worker.Settings.get_settings", lambda: {"default_bot_lookback_days": 0})

        def capture_filter(filter_args):
            captured_filter.update(filter_args)
            return [{"id": "story-1"}]

        monkeypatch.setattr("core.api.worker.Story.get_for_worker", capture_filter)

        response = client.get(
            f"{self.base_uri}/stories",
            query_string={"worker": "true", "exclude_attr": "ANALYST_BOT"},
            headers=api_header,
        )

        assert response.status_code == 200
        assert "timefrom" not in captured_filter

    def test_non_bot_story_query_does_not_apply_default_lookback(self, client, api_header, monkeypatch):
        captured_filter = {}

        def capture_filter(filter_args):
            captured_filter.update(filter_args)
            return [{"id": "story-1"}]

        monkeypatch.setattr("core.api.worker.Story.get_for_worker", capture_filter)

        response = client.get(
            f"{self.base_uri}/stories",
            query_string={"source": "source-1"},
            headers=api_header,
        )

        assert response.status_code == 200
        assert "timefrom" not in captured_filter

    def test_post_collection_bots_forwards_user_id(self, client, api_header, monkeypatch):
        captured = {}

        def fake_post_collection_bots(source_id, user_id=None):
            captured["source_id"] = source_id
            captured["user_id"] = user_id
            return {"message": "scheduled"}, 200

        monkeypatch.setattr("core.api.worker.queue_manager.queue_manager.post_collection_bots", fake_post_collection_bots)

        response = client.put(
            f"{self.base_uri}/post-collection-bots",
            json={"source_id": "source-1", "user_id": "user-1"},
            headers=api_header,
        )

        assert response.status_code == 200
        assert captured == {"source_id": "source-1", "user_id": "user-1"}

    @pytest.mark.parametrize(
        "result_payload",
        [
            {"message": "", "reason": None, "retryable": False, "data": []},
            {"message": "Preview finished", "reason": None, "retryable": False, "data": False},
            {"message": "Preview finished", "reason": None, "retryable": False, "data": 0},
        ],
    )
    def test_worker_task_results_preserves_falsy_result_fields(self, client, api_header, app, result_payload):
        from core.model.task import Task

        task_id = f"task-result-{uuid.uuid4().hex}"

        payload = {"id": task_id, "task": "collector_preview", "result": result_payload, "status": "SUCCESS"}

        try:
            response = client.post("/api/tasks", json=payload, headers=api_header)

            assert response.status_code == 200
            assert response.get_json()["task"] == "collector_preview"
            assert response.get_json()["result"] == result_payload

            with app.app_context():
                stored = Task.get(task_id)
                assert stored is not None
                assert stored.to_dict()["result"] == result_payload
                assert stored.task == "collector_preview"
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    @pytest.mark.parametrize("status", ["PREVIEW", "FAILURE"])
    def test_worker_preview_terminal_result_publishes_realtime_event(self, client, api_header, app, monkeypatch, status):
        from core.model.task import Task

        source_id = uuid.uuid4().hex
        user_id = str(uuid.uuid4())
        task_id = f"source_preview_{source_id}"
        publish = Mock(return_value=True)
        monkeypatch.setattr("core.service.task.realtime_publisher.osint_source_preview_finished", publish)

        payload = {
            "id": task_id,
            "task": "collector_preview",
            "user_id": user_id,
            "result": {"message": "Preview finished", "reason": None, "retryable": False, "data": []},
            "status": status,
        }

        try:
            response = client.post("/api/tasks", json=payload, headers=api_header)

            assert response.status_code == 200
            publish.assert_called_once_with(source_id, user_id, status)
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_worker_story_update(self, client, stories, cleanup_story_update_data, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """

        story_1_id = stories[0]
        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_1_id},
        )

        story_1 = response.get_json()[0]
        assert story_1.get("attributes", {}).get("TLP", {}).get("value", "no TLP attribute") == "clear", (
            "TLP attribute should be clear on preseed"
        )

        update_story_data = cleanup_story_update_data
        update_story_data["id"] = story_1_id

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_story_data,
            headers=api_header,
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Story updated successfully"
        assert result.get("id") == story_1_id

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_1_id})

        assert response.status_code == 200
        assert response.get_json()[0].get("title") == update_story_data["title"]
        assert response.get_json()[0].get("id") == story_1_id
        assert response.get_json()[0].get("attributes", {}).get("TLP", {}).get("value", "no TLP attribute") == "clear", (
            "TLP attribute should be kept after update"
        )
        assert len(response.get_json()[0].get("attributes")) == 3

    def test_worker_story_update_with_new_news_item(self, client, stories, cleanup_story_update_data, cleanup_news_item, api_header):
        """
        This test updates the same story as before (using the story_id from the previous test)
        by including new news items and adding an extra attribute.
        It verifies that the total number of news_items in the story increases as expected.
        """
        story_1_id = stories[0]

        # Get the current state of the story to know the original number of news items.
        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_1_id},
        )
        assert response.status_code == 200
        original_story = response.get_json()[0]
        original_news_items = original_story.get("news_items", [])
        assert len(original_news_items) == 1
        assert len(original_story.get("attributes", {})) == 3, "Number of expected attributes is 3"

        update_data = cleanup_story_update_data.copy()
        update_data["id"] = story_1_id  # reuse the story id from the previous test
        expected_tags = [{"name": "tag1", "tag_type": "misc"}, {"name": "tag2", "tag_type": "misc"}]
        update_data["news_items"] = [{**cleanup_news_item, "tags": expected_tags}]
        update_data["attributes"].append({"key": "status", "value": "updated"})

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_data,
            headers=api_header,
        )
        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Story updated successfully"
        assert result.get("id") == story_1_id

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_1_id})
        assert response.status_code == 200
        updated_story = response.get_json()[0]
        assert updated_story.get("title") == update_data["title"]
        assert updated_story.get("id") == story_1_id

        updated_news_items = updated_story.get("news_items", [])
        assert len(updated_news_items) == 2, f"Expected 2 news items, but got {len(updated_news_items)}"

        for new_item in update_data["news_items"]:
            assert any(item.get("id") == new_item["id"] for item in updated_news_items), (
                f"News item {new_item['id']} was not found in the updated story."
            )

        attributes_in_story = updated_story.get("attributes", {})
        assert "status" in attributes_in_story, "Updated attribute key 'status' not found in the story."
        assert attributes_in_story["status"].get("value") == "updated", (
            f"Expected 'updated' but got '{attributes_in_story['status'].get('value')}'"
        )
        assert _tag_names(updated_story.get("tags", {})) == _tag_names(expected_tags)

    def test_worker_story_update_including_existing_news_items(
        self, client, stories, cleanup_news_item_2, cleanup_story_update_data, api_header
    ):
        story_1_id = stories[0]
        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_1_id},
        )
        assert response.status_code == 200
        original_story = response.get_json()[0]
        original_news_items = original_story.get("news_items", [])
        expected_tags = [{"name": "tag1", "tag_type": "misc"}, {"name": "tag2", "tag_type": "misc"}]
        new_news_item = {**cleanup_news_item_2, "tags": expected_tags}

        update_data = cleanup_story_update_data.copy()
        update_data["id"] = story_1_id
        update_data["news_items"] = [*original_news_items, new_news_item]

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_data,
            headers=api_header,
        )
        result = response.get_json()

        assert response.status_code == 200
        assert result.get("message") == "Story updated successfully"
        assert result.get("id") == story_1_id

        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_1_id},
        )

        assert response.status_code == 200
        assert response.get_json()[0].get("title") == update_data["title"]
        assert len(response.get_json()[0].get("news_items", [])) == len(update_data["news_items"])
        assert _tag_names(response.get_json()[0].get("tags", {})) == _tag_names(expected_tags)

    def test_worker_story_update_with_conflict(self, client, stories, cleanup_news_item_2, cleanup_story_update_data, api_header):
        story_2_id = stories[1]

        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_2_id},
        )
        assert response.status_code == 200
        original_story = response.get_json()[0]
        original_news_items = original_story.get("news_items", [])

        updated_news_items = original_news_items.copy()
        updated_news_items.append(cleanup_news_item_2)

        update_data = cleanup_story_update_data.copy()
        update_data["id"] = story_2_id
        update_data["news_items"] = updated_news_items

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_data,
            headers=api_header,
        )
        result = response.get_json()
        assert response.status_code == 409
        assert "conflicts_number" in result.get("error")

        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_2_id},
        )
        assert response.status_code == 200
        updated_story = response.get_json()[0]

        assert updated_story.get("title") == original_story["title"]
        assert len(updated_story.get("news_items", [])) == len(original_story.get("news_items", []))

    def test_worker_create_full_story(self, client, full_story: list[dict], api_header):
        response = client.post(
            f"{self.base_uri}/stories",
            json=full_story[0],
            headers=api_header,
        )

        assert response.status_code == 200
        result = response.get_json()
        new_story_id = result.get("story_id", "t<story_id>")
        assert result.get("message") == "Story added successfully"
        assert result.get("news_item_ids")[0] == full_story[0].get("news_items", [])[0].get("id", "<news_item_id>")
        assert new_story_id == full_story[0].get("id")

        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": new_story_id},
        )
        assert response.status_code == 200
        story = response.get_json()[0]
        assert story.get("id") == new_story_id
        assert story.get("title") == full_story[0].get("title")
        assert len(story.get("news_items", [])) == len(full_story[0].get("news_items", []))
        assert _tag_names(story.get("tags", [])) == _expected_story_tag_names(full_story[0])
        for news_item in story.get("news_items", []):
            expected_item = next(item for item in full_story[0].get("news_items", []) if item["id"] == news_item["id"])
            assert _tag_names(news_item.get("tags", [])) == _tag_names(expected_item.get("tags", []))
        assert len(story.get("attributes", {})) == len(full_story[0].get("attributes", [])) + 1  # TLP is automatically added

    def test_worker_post_to_misp_endpoint(self, client, full_story: list[dict], api_header):
        """Test if MISP endpoint handles updates without conflicts correctly"""
        story_id = full_story[0].get("id")

        response = client.post(
            f"{self.base_uri}/misp/stories",
            json=[full_story[0]],
            headers=api_header,
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Stories added or updated successfully"
        assert result.get("details").get("story_ids")[0] == story_id

        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": story_id},
        )
        assert response.status_code == 200
        story = response.get_json()[0]
        assert story.get("id") == story_id
        assert story.get("title") == full_story[0].get("title")
        assert len(story.get("news_items", [])) == len(full_story[0].get("news_items", []))
        assert _tag_names(story.get("tags", [])) == _expected_story_tag_names(full_story[0])
        for news_item in story.get("news_items", []):
            expected_item = next(item for item in full_story[0].get("news_items", []) if item["id"] == news_item["id"])
            assert _tag_names(news_item.get("tags", [])) == _tag_names(expected_item.get("tags", []))
        assert len(story.get("attributes", {})) == len(full_story[0].get("attributes", [])) + 1

    def test_worker_put_tags(self, client, stories, api_header, monkeypatch):
        story_1_id = stories[0]
        tags = ["tag3", "tag4"]
        refreshed = []
        monkeypatch.setattr("core.service.news_item.refresh_misp_auto_update_jobs", refreshed.append)
        story_response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_1_id})
        news_item_id = story_response.get_json()[0]["news_items"][0]["id"]

        response = client.put(f"{self.base_uri}/tags", json={news_item_id: tags}, headers=api_header)

        assert response.status_code == 200
        assert response.get_json().get("message") == "Tags updated"

        updated_story_response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_1_id})
        assert updated_story_response.status_code == 200

        updated_story = updated_story_response.get_json()[0]
        updated_news_item = next(news_item for news_item in updated_story.get("news_items", []) if news_item["id"] == news_item_id)

        updated_tags = updated_news_item.get("tags", [])
        assert [tag.get("name") for tag in updated_tags] == tags
        assert all(tag.get("tag_type") == "misc" for tag in updated_tags)
        assert refreshed == [[story_1_id]]

    def test_worker_put_tags_invalid_cases(self, client, stories, api_header):
        story_1_id = stories[0]
        story_response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_1_id})
        news_item_id = story_response.get_json()[0]["news_items"][0]["id"]

        # Empty list
        response = client.put(f"{self.base_uri}/tags", json={news_item_id: []}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # Tags not a list
        response = client.put(f"{self.base_uri}/tags", json={news_item_id: "notalist"}, headers=api_header)
        assert response.status_code == 207
        assert "message" in response.get_json()

        # Missing news item id
        response = client.put(f"{self.base_uri}/tags", json={"not_a_news_item_id": ["tag1"]}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # Tags list contains non-string elements
        response = client.put(f"{self.base_uri}/tags", json={news_item_id: [123, None]}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # News item ID is not a string
        response = client.put(f"{self.base_uri}/tags", json={123: ["tag1"]}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # Payload is not a dict
        response = client.put(f"{self.base_uri}/tags", json=["not", "a", "dict"], headers=api_header)
        assert response.status_code == 400
        assert "error" in response.get_json()

        # Empty payload
        response = client.put(f"{self.base_uri}/tags", json={}, headers=api_header)
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_worker_story_roundtrip_preserves_news_item_tag_distribution(self, client, full_story_with_multiple_items_id, api_header):
        story_id, _ = full_story_with_multiple_items_id
        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_id})
        assert response.status_code == 200
        story = response.get_json()[0]
        news_items = story["news_items"]
        assert len(news_items) == 2

        first_item_id = news_items[0]["id"]
        second_item_id = news_items[1]["id"]
        tag_payload = {
            first_item_id: [{"name": "roundtrip-first", "tag_type": "specific"}],
            second_item_id: [{"name": "roundtrip-second", "tag_type": "specific"}],
        }
        response = client.put(f"{self.base_uri}/tags", json=tag_payload, headers=api_header)
        assert response.status_code == 200

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_id})
        assert response.status_code == 200
        roundtrip_payload = response.get_json()[0]
        response = client.post(f"{self.base_uri}/stories", json=roundtrip_payload, headers=api_header)
        assert response.status_code == 200

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_id})
        assert response.status_code == 200
        updated_story = response.get_json()[0]
        updated_tags = {item["id"]: {tag["name"] for tag in item["tags"]} for item in updated_story["news_items"]}

        assert updated_tags[first_item_id] == {"roundtrip-first"}
        assert updated_tags[second_item_id] == {"roundtrip-second"}

    def test_worker_get_tags(self, client, api_header, stories):
        from core.model.news_item_tag import NewsItemTag
        from core.model.story import Story

        expected_tags = {f"worker-tag-{index}" for index in range(5)}
        clear_result, clear_status = NewsItemTag.delete_all()
        assert clear_status == 200, clear_result

        story = Story.get(stories[0])
        assert story is not None
        update_result, update_status = story.news_items[0].set_tags(sorted(expected_tags))
        assert update_status == 200, update_result

        response = client.get(f"{self.base_uri}/tags", headers=api_header)

        assert response.status_code == 200
        assert isinstance(response.get_json(), dict)
        assert set(response.get_json()) == expected_tags


class TestWorkerTaskResults:
    base_uri = "/api/tasks"

    @pytest.mark.parametrize(
        ("payload", "expected_error"),
        [
            ({"status": "SUCCESS", "result": {"message": "ok", "retryable": False}}, "id"),
            ({"id": "task-1", "result": {"message": "ok", "retryable": False}}, "status"),
            ({"id": 123, "status": "SUCCESS", "result": {"message": "ok", "retryable": False}}, "id"),
            ({"id": "task-1", "status": 123, "result": {"message": "ok", "retryable": False}}, "status"),
            ({"id": "task-1", "status": "SUCCESS"}, "result"),
            ({"id": "task-1", "status": "SUCCESS", "kwargs": {}}, "result"),
            ({"id": "task-1", "status": "SUCCESS", "result": {"retryable": False}}, "message"),
        ],
    )
    def test_worker_task_results_rejects_missing_or_invalid_required_fields(self, client, api_header, payload, expected_error):
        response = client.post(self.base_uri, json=payload, headers=api_header)

        assert response.status_code == 400
        assert expected_error in response.get_json()["error"]

    def test_worker_task_results_rejects_invalid_task_field(self, client, api_header):
        response = client.post(
            self.base_uri,
            json={"id": "task-1", "task": ["bad"], "result": {"message": "ok", "retryable": False}, "status": "SUCCESS"},
            headers=api_header,
        )

        assert response.status_code == 400
        assert "task" in response.get_json()["error"]

    def test_worker_task_results_updates_product_render(self, client, api_header, app, cleanup_product):
        from core.model.product import Product
        from core.model.task import Task

        product_id = str(uuid.uuid7())
        task_id = f"presenter-job-{uuid.uuid4().hex}"
        render_result = "YmFzZTY0"

        with app.app_context():
            product = Product.add({**cleanup_product, "id": product_id})
            render_revision = product.to_worker_dict()["render_revision"]

        payload = {
            "id": task_id,
            "task": "presenter_task",
            "result": {
                "message": "ok",
                "retryable": False,
                "data": {"product_id": product_id, "render_result": render_result, "render_revision": render_revision},
            },
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)

            assert response.status_code == 200
            with app.app_context():
                product = Product.get(product_id)
                assert product is not None
                assert product.render_result == render_result
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)
                if Product.get(product_id):
                    Product.delete(product_id)

    def test_worker_task_results_only_apply_to_matching_product_revision(self, client, api_header, app, cleanup_product):
        from core.managers.db_manager import db
        from core.model.product import Product
        from core.model.task import Task

        product_id = str(uuid.uuid7())
        task_id = f"presenter-job-{uuid.uuid4().hex}"

        with app.app_context():
            product = Product.add({**cleanup_product, "id": product_id})
            stale_revision = product.to_worker_dict()["render_revision"]
            product.title = "Updated while rendering"
            db.session.commit()

        payload = {
            "id": task_id,
            "task": "presenter_task",
            "result": {
                "message": "ok",
                "retryable": False,
                "data": {"product_id": product_id, "render_result": "YmFzZTY0", "render_revision": stale_revision},
            },
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)

            assert response.status_code == 200
            with app.app_context():
                product = Product.get(product_id)
                assert product is not None
                assert product.render_result is None
                assert product.last_rendered is None
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)
                if Product.get(product_id):
                    Product.delete(product_id)

    def test_worker_task_results_apply_bot_tags(self, client, stories, auth_header, api_header, app, wordlist_bot_result, monkeypatch):
        from core.model.task import Task

        refreshed = []
        monkeypatch.setattr("core.service.task.refresh_misp_auto_update_jobs", refreshed.append)
        task_id = f"cron-bot-wordlist-{uuid.uuid4().hex}"
        payload = {
            "id": task_id,
            "task": f"bot_{wordlist_bot_result['worker_id']}",
            "worker_id": wordlist_bot_result["worker_id"],
            "worker_type": wordlist_bot_result["worker_type"],
            "result": wordlist_bot_result["result"],
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)

            assert response.status_code == 200
            assert refreshed == [set(stories)]

            for story_id in stories:
                story_response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
                assert story_response.status_code == 200

                story_data = story_response.get_json()
                structured_tags = {tag["name"]: tag["tag_type"] for tag in story_data.get("tags", [])}
                expected_tags = {}
                for news_item in story_data.get("news_items", []):
                    expected_tags |= wordlist_bot_result["result"]["data"]["result"].get(news_item["id"], {})

                assert structured_tags == expected_tags
                attr_by_key = {attribute.get("key"): attribute.get("value") for attribute in story_data.get("attributes", [])}
                assert attr_by_key["WORDLIST_BOT"].startswith(f"worker_id={wordlist_bot_result['worker_id']}")
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_task_submission_accepts_task_id_alias(self, client, api_header, app):
        from core.model.task import Task

        task_id = f"alias-task-{uuid.uuid4().hex}"
        payload = {
            "task_id": task_id,
            "task": "collector_task",
            "result": {"message": "ok", "retryable": False, "data": {"source_id": "source-1"}},
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)
            assert response.status_code == 200
            assert response.get_json()["job_id"] == task_id
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_task_submission_persists_user_id(self, client, api_header, app):
        from core.model.task import Task

        task_id = f"user-task-{uuid.uuid4().hex}"
        payload = {
            "id": task_id,
            "task": "collector_task",
            "user_id": "user-123",
            "worker_id": "source-1",
            "worker_type": "rss_collector",
            "result": {"message": "ok", "retryable": False, "data": {"source_id": "source-1"}},
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)
            assert response.status_code == 200
            assert response.get_json()["user_id"] == "user-123"

            with app.app_context():
                stored = Task.get(task_id)
                assert stored is not None
                assert stored.user_id == "user-123"
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_gather_word_list_success_result_replays_with_canonical_result_data(self, client, api_header, app, monkeypatch):
        from core.model.task import Task
        from core.model.word_list import WordList

        task_id = f"gather-word-list-{uuid.uuid4().hex}"
        update_word_list = Mock(return_value=None)
        monkeypatch.setattr(WordList, "update_word_list", update_word_list)

        payload = {
            "id": task_id,
            "task": "gather_word_list",
            "worker_id": "word-list-1",
            "worker_type": "gather_word_list",
            "result": {
                "message": "Successfully updated wordlist",
                "reason": None,
                "retryable": False,
                "data": {
                    "word_list_id": "word-list-1",
                    "content": "alpha,beta",
                    "content_type": "text/csv",
                },
            },
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)

            assert response.status_code == 200
            update_word_list.assert_called_once_with(
                word_list_id="word-list-1",
                content="alpha,beta",
                content_type="text/csv",
            )
            assert "message" not in response.get_json()["result"]["data"]
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_tasks_get_returns_strict_canonical_rows_only(self, client, api_header, app):
        from core.model.task import Task

        task_id = f"strict-task-{uuid.uuid4().hex}"
        payload = {
            "id": task_id,
            "task": "collector_task",
            "worker_id": "source-1",
            "worker_type": "rss_collector",
            "result": {
                "message": "Collected 1 item",
                "reason": None,
                "retryable": False,
                "data": {"source_id": "source-1"},
            },
            "status": "SUCCESS",
        }

        try:
            create_response = client.post(self.base_uri, json=payload, headers=api_header)
            assert create_response.status_code == 200

            history_response = client.get(self.base_uri, headers=api_header)
            assert history_response.status_code == 200

            history = history_response.get_json()
            task_row = next(item for item in history["items"] if item["job_id"] == task_id)
            assert task_row["result"] == payload["result"]

            detail_response = client.get(f"{self.base_uri}/{task_id}", headers=api_header)
            assert detail_response.status_code == 200
            assert detail_response.get_json()["result"] == payload["result"]
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    @pytest.mark.parametrize(
        ("status", "result_message"),
        [
            ("FAILURE", "Error: feed retrieval failed"),
        ],
    )
    def test_collector_non_success_result_invalidates_only_osint_source_cache(
        self, client, api_header, app, monkeypatch, status, result_message
    ):
        import fakeredis

        from core.model.task import Task
        from core.service import cache_invalidation as cache_invalidation_module

        source_id = f"source-{uuid.uuid4().hex}"
        task_id = f"collect_rss_collector_{source_id}"
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        cached_keys = {
            "taranis_frontend:user:alice:model:osint_source:list:default",
            f"taranis_frontend:user:alice:model:osint_source:detail:{source_id}",
            "taranis_frontend:user:alice:model:osint_source:detail:other-source",
            f"taranis_frontend:user:alice:model:task:detail:{task_id}",
            "taranis_frontend:user:alice:model:job:list:default",
            "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
            "taranis_frontend:user:alice:model:admin_menu_badges:detail:singleton",
            "taranis_frontend:user:alice:model:active_job:list:default",
            "taranis_frontend:user:alice:model:failed_job:list:default",
            "taranis_frontend:user:alice:model:queue_status:list:default",
            "taranis_frontend:user:alice:model:worker_stats:detail:singleton",
            "taranis_frontend:user:alice:model:story:list:default",
        }
        redis_client.mset(dict.fromkeys(cached_keys, "1"))

        service = cache_invalidation_module.FrontendCacheInvalidationService()
        service._client = redis_client
        monkeypatch.setattr(cache_invalidation_module, "cache_invalidation_service", service)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_ENABLED", True)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_KEY_PREFIX", "taranis_frontend")

        payload = {
            "id": task_id,
            "task": "collector_task",
            "worker_id": source_id,
            "worker_type": "rss_collector",
            "result": {
                "message": result_message,
                "reason": "collection_failed" if status == "FAILURE" else None,
                "retryable": False,
                "data": {"source_id": source_id},
            },
            "status": status,
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)

            assert response.status_code == 200
            assert response.get_json()["status"] == status
            expected_keys = {
                "taranis_frontend:user:alice:model:osint_source:detail:other-source",
                f"taranis_frontend:user:alice:model:task:detail:{task_id}",
                "taranis_frontend:user:alice:model:job:list:default",
                "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
                "taranis_frontend:user:alice:model:active_job:list:default",
                "taranis_frontend:user:alice:model:failed_job:list:default",
                "taranis_frontend:user:alice:model:queue_status:list:default",
                "taranis_frontend:user:alice:model:worker_stats:detail:singleton",
                "taranis_frontend:user:alice:model:story:list:default",
            }
            assert set(redis_client.scan_iter(match="*")) == expected_keys
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_collector_success_result_restores_full_cache_invalidation(self, client, api_header, app, monkeypatch):
        import fakeredis

        from core.model.task import Task
        from core.service import cache_invalidation as cache_invalidation_module

        source_id = f"source-{uuid.uuid4().hex}"
        task_id = f"collect_rss_collector_{source_id}"
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        cached_keys = {
            "taranis_frontend:user:alice:model:osint_source:list:default",
            f"taranis_frontend:user:alice:model:osint_source:detail:{source_id}",
            "taranis_frontend:user:alice:model:osint_source:detail:other-source",
            f"taranis_frontend:user:alice:model:task:detail:{task_id}",
            "taranis_frontend:user:alice:model:job:list:default",
            "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
            "taranis_frontend:user:alice:model:active_job:list:default",
            "taranis_frontend:user:alice:model:failed_job:list:default",
            "taranis_frontend:user:alice:model:queue_status:list:default",
            "taranis_frontend:user:alice:model:worker_stats:detail:singleton",
            "taranis_frontend:user:alice:model:story:list:default",
        }
        redis_client.mset(dict.fromkeys(cached_keys, "1"))

        service = cache_invalidation_module.FrontendCacheInvalidationService()
        service._client = redis_client
        monkeypatch.setattr(cache_invalidation_module, "cache_invalidation_service", service)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_ENABLED", True)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_KEY_PREFIX", "taranis_frontend")

        payload = {
            "id": task_id,
            "task": "collector_task",
            "worker_id": source_id,
            "worker_type": "rss_collector",
            "result": {
                "message": "Collected 3 new items",
                "retryable": False,
                "data": {"source_id": source_id},
            },
            "status": "SUCCESS",
        }

        try:
            response = client.post(self.base_uri, json=payload, headers=api_header)

            assert response.status_code == 200
            assert response.get_json()["status"] == "SUCCESS"
            assert set(redis_client.scan_iter(match="*")) == set()
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_collector_not_modified_updates_last_success_and_task_statistics(self, client, api_header, app, fake_source):
        from core.model.osint_source import CollectorHTTPState
        from core.model.task import Task

        source_id = fake_source
        task_id = f"collect_rss_collector_{source_id}"
        validators = {
            "url": "https://example.com/feed",
            "etag": 'W/"opaque-etag"',
            "last_modified": "Tue, 11 Aug 2026 09:07:03 GMT",
        }
        payload = {
            "id": task_id,
            "task": "collector_task",
            "worker_id": source_id,
            "worker_type": "rss_collector",
            "result": {
                "message": "No changes: feed was not modified",
                "reason": "collector_not_modified",
                "retryable": False,
                "data": {"source_id": source_id, "http_validators": validators},
            },
            "status": "NOT_MODIFIED",
        }

        try:
            response = client.post(self.base_uri.replace("/worker", "/tasks"), json=payload, headers=api_header)
            assert response.status_code == 200

            with app.app_context():
                stored = Task.get(task_id)
                assert stored is not None
                assert stored.status == "NOT_MODIFIED"
                assert stored.last_run is not None
                assert stored.last_success is not None
                state = CollectorHTTPState.query.get(source_id)
                assert state is not None
                assert state.to_worker_dict() == validators

            source_response = client.get(f"/api/worker/osint-sources/{source_id}", headers=api_header)
            assert source_response.status_code == 200
            assert source_response.get_json()["http_validators"] == validators

            history_response = client.get("/api/tasks", headers=api_header)
            assert history_response.status_code == 200

            history = history_response.get_json()
            collector_stats = history["task_stats"]["rss_collector"]
            assert collector_stats["successes"] >= 1
            assert collector_stats["total"] >= collector_stats["successes"]
            assert history["totals"]["successes"] >= 1
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)

    def test_synthetic_cron_collector_failure_updates_source_status_last_run(self, client, api_header, app):
        from core.model.osint_source import OSINTSource
        from core.model.task import Task

        source_id = f"cron-failure-{uuid.uuid4().hex}"
        source = {
            "id": source_id,
            "name": f"Cron Failure Source {source_id}",
            "description": "Cron failure source",
            "parameters": {"FEED_URL": "https://example.invalid/cron-failure.xml"},
            "type": "rss_collector",
        }
        with app.app_context():
            OSINTSource.add(source)
            persisted_source = OSINTSource.get(source_id)
            assert persisted_source is not None
            cron_task_id = f"cron_osint_source_{persisted_source.id}_1777459628"
        payload = {
            "id": cron_task_id,
            "task": "collector_task",
            "worker_id": source_id,
            "worker_type": "collector_task",
            "result": {
                "message": "Collector worker was killed",
                "reason": "work_horse_killed",
                "retryable": True,
                "data": {"source_id": source_id, "retpid": 456, "ret_val": 9},
            },
            "status": "FAILURE",
        }

        try:
            response = client.post(self.base_uri.replace("/worker", "/tasks"), json=payload, headers=api_header)
            assert response.status_code == 200

            with app.app_context():
                stored = Task.get(cron_task_id)
                assert stored is not None
                assert stored.status == "FAILURE"
                assert stored.last_run is not None
                assert stored.last_success is None

                refreshed_source = OSINTSource.get(source_id)
                assert refreshed_source is not None
                assert refreshed_source.status is not None
                assert refreshed_source.status["job_id"] == cron_task_id
                assert refreshed_source.status["status"] == "FAILURE"
                assert refreshed_source.status["last_run"] is not None
        finally:
            with app.app_context():
                if Task.get(cron_task_id):
                    Task.delete(cron_task_id)
                if OSINTSource.get(source_id):
                    OSINTSource.delete(source_id)

    def test_collector_not_modified_clears_admin_badges_cache_after_failure(self, client, api_header, app, monkeypatch):
        import fakeredis

        from core.model.task import Task
        from core.service import cache_invalidation as cache_invalidation_module

        source_id = f"source-{uuid.uuid4().hex}"
        task_id = f"collect_rss_collector_{source_id}"
        previous_failure_id = f"{task_id}-failed"
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        cached_keys = {
            "taranis_frontend:user:alice:model:admin_menu_badges:detail:singleton",
            f"taranis_frontend:user:alice:model:osint_source:detail:{source_id}",
            "taranis_frontend:user:alice:model:osint_source:detail:other-source",
        }
        redis_client.mset(dict.fromkeys(cached_keys, "1"))

        service = cache_invalidation_module.FrontendCacheInvalidationService()
        service._client = redis_client
        monkeypatch.setattr(cache_invalidation_module, "cache_invalidation_service", service)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_ENABLED", True)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_KEY_PREFIX", "taranis_frontend")

        try:
            with app.app_context():
                Task.add(
                    {
                        "id": previous_failure_id,
                        "task": "collector_task",
                        "worker_id": source_id,
                        "worker_type": "rss_collector",
                        "status": "FAILURE",
                        "result": {"message": "boom", "reason": "collection_failed", "retryable": False, "data": {"source_id": source_id}},
                    }
                )

            response = client.post(
                self.base_uri,
                json={
                    "id": task_id,
                    "task": "collector_task",
                    "worker_id": source_id,
                    "worker_type": "rss_collector",
                    "result": {
                        "message": "No changes: feed was not modified",
                        "reason": "collector_not_modified",
                        "retryable": False,
                        "data": {"source_id": source_id},
                    },
                    "status": "NOT_MODIFIED",
                },
                headers=api_header,
            )

            assert response.status_code == 200
            assert "taranis_frontend:user:alice:model:admin_menu_badges:detail:singleton" not in set(redis_client.scan_iter(match="*"))
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)
                if Task.get(previous_failure_id):
                    Task.delete(previous_failure_id)

    def test_tasks_get_allows_jwt_auth(self, client, auth_header):
        response = client.get(self.base_uri, headers=auth_header)
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        assert "items" in payload
        assert "task_stats" in payload
        assert "totals" in payload

    def test_tasks_get_allows_api_key_auth(self, client, api_header):
        response = client.get(self.base_uri, headers=api_header)
        assert response.status_code == 200

    def test_tasks_delete_allows_jwt_auth_and_invalidates_worker_status_caches(self, client, auth_header, app, monkeypatch):
        import fakeredis

        from core.model.task import Task
        from core.service import cache_invalidation as cache_invalidation_module

        task_id = f"delete-task-{uuid.uuid4().hex}"
        source_id = f"source-{uuid.uuid4().hex}"
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        cached_keys = {
            "taranis_frontend:user:alice:model:admin_menu_badges:detail:singleton",
            "taranis_frontend:user:alice:model:bot:list:default",
            "taranis_frontend:user:alice:model:osint_source:list:default",
            f"taranis_frontend:user:alice:model:osint_source:detail:{source_id}",
            "taranis_frontend:user:alice:model:osint_source:detail:other-source",
        }
        redis_client.mset(dict.fromkeys(cached_keys, "1"))

        service = cache_invalidation_module.FrontendCacheInvalidationService()
        service._client = redis_client
        monkeypatch.setattr(cache_invalidation_module, "cache_invalidation_service", service)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_ENABLED", True)
        monkeypatch.setattr(cache_invalidation_module.Config, "CACHE_KEY_PREFIX", "taranis_frontend")

        try:
            with app.app_context():
                Task.add(
                    {
                        "id": task_id,
                        "task": "collector_task",
                        "worker_id": source_id,
                        "worker_type": "rss_collector",
                        "result": {"message": "failed", "retryable": False, "data": {"source_id": source_id}},
                        "status": "FAILURE",
                    }
                )

            response = client.delete(f"{self.base_uri}/{task_id}", headers=auth_header)

            assert response.status_code == 200
            with app.app_context():
                assert Task.get(task_id) is None
            assert set(redis_client.scan_iter(match="*")) == {
                "taranis_frontend:user:alice:model:bot:list:default",
                "taranis_frontend:user:alice:model:osint_source:detail:other-source",
            }
        finally:
            with app.app_context():
                if Task.get(task_id):
                    Task.delete(task_id)


class TestConnector:
    base_uri = "/api/worker"

    def test_connector(self, client, stories, api_header):
        import types

        class _StubLogger:
            def warning(self, *_, **__):
                return None

            def debug(self, *_, **__):
                return None

        class _StubBaseMispObject:
            def __init__(self, *_, **__):
                return None

        class _StubMISPEvent:
            def __init__(self, *_, **__):
                return None

        pymisp = types.ModuleType("pymisp")
        pymisp.MISPEvent = _StubMISPEvent

        worker_module = types.ModuleType("worker")
        worker_connectors = types.ModuleType("worker.connectors")
        worker_connectors_definitions = types.ModuleType("worker.connectors.definitions")
        worker_connectors_misp_objects = types.ModuleType("worker.connectors.definitions.misp_objects")
        worker_log = types.ModuleType("worker.log")

        worker_log.logger = _StubLogger()
        worker_connectors_misp_objects.BaseMispObject = _StubBaseMispObject

        sys.modules["pymisp"] = pymisp
        sys.modules["worker"] = worker_module
        sys.modules["worker.connectors"] = worker_connectors
        sys.modules["worker.connectors.definitions"] = worker_connectors_definitions
        sys.modules["worker.connectors.definitions.misp_objects"] = worker_connectors_misp_objects
        sys.modules["worker.log"] = worker_log

        file_path = Path(__file__).resolve().parents[4] / "worker" / "worker" / "connectors" / "base_misp_builder.py"

        spec = importlib.util.spec_from_file_location("base_misp_builder", file_path)
        assert spec is not None and spec.loader is not None

        base_misp_builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(base_misp_builder)

        response = client.get(f"{self.base_uri}/stories", headers=api_header)
        story = response.get_json()[0]
        story_id = story.get("id")

        story["attributes"] = {
            "TLP": {"key": "TLP", "value": "clear"},
            "test": {"key": "test", "value": "test"},
        }
        news_item_id = story["news_items"][0]["id"]
        story.pop("tags", None)
        for news_item in story.get("news_items", []):
            news_item.pop("tags", None)

        client.post(f"{self.base_uri}/stories", json=story, headers=api_header)
        tag_response = client.put(
            f"{self.base_uri}/tags", json={news_item_id: [{"name": "test_tag", "tag_type": "misc"}]}, headers=api_header
        )
        assert tag_response.status_code == 200

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": story_id})
        updated_story = response.get_json()[0]

        attribute_list = base_misp_builder.add_attributes_from_story(updated_story)
        object_data = base_misp_builder.get_story_object_dict(updated_story)
        tag_list = object_data.get("tags", [])

        assert attribute_list == [
            '{"key": "TLP", "value": "clear"}',
            '{"key": "test", "value": "test"}',
            f'{{"key": "misp_event_uuid", "value": "{story_id}"}}',
        ], f"Expected attributes {updated_story['attributes']}, but got {attribute_list}"

        assert tag_list == ['{"name": "test_tag", "tag_type": "misc"}'], f"Expected tags {updated_story['tags']}, but got {tag_list}"


class TestOSINTSourceScheduling:
    base_uri = "/api/worker"

    PER_SOURCE = "per-source"
    DEFAULT = "default"
    NONE = "none"

    @pytest.mark.parametrize(
        "row, per_source_proxy_set, default_proxy_set, use_global, expected",
        [
            # Row, per-source, default, use_global, expected result
            (1, False, False, False, NONE),
            (2, True, False, False, PER_SOURCE),
            (3, False, True, False, NONE),
            (4, True, True, False, PER_SOURCE),
            (5, False, False, True, NONE),
            (6, True, False, True, NONE),
            (7, False, True, True, DEFAULT),
            (8, True, True, True, DEFAULT),
        ],
        ids=[f"row-{i}" for i in range(1, 9)],
    )
    def test_proxy_selection_matrix(
        self, app, client, auth_header, api_header, row, per_source_proxy_set, default_proxy_set, use_global, expected
    ):
        """
        Verifies that PROXY_SERVER in the worker payload follows the 2x2x2 matrix:

        - use_global = true  -> PROXY_SERVER should be the default proxy (or empty if not set)
        - use_global = false -> PROXY_SERVER should be the per-source proxy if set; otherwise absent/empty
        """
        per_proxy = "http://per-source:1234"
        default_proxy = "http://default-proxy:9999"
        settings_payload = {
            "settings": {
                "default_collector_proxy": default_proxy if default_proxy_set else "",
                "default_collector_interval": "5 5 * * *",
                "default_tlp_level": "clear",
            }
        }

        response = client.put("/api/settings/settings", json=settings_payload, headers=auth_header)
        assert response.status_code == 200, f"Failed to set settings for row {row}: {response}"

        source_id = "test_id"
        with app.app_context():
            from core.model.osint_source import OSINTSource

            params = {
                "FEED_URL": "https://example.org/feed.xml",
                "USE_GLOBAL_PROXY": "true" if use_global else "false",
            }
            if per_source_proxy_set:
                params["PROXY_SERVER"] = per_proxy

            source_data = {
                "id": source_id,
                "description": f"Matrix test row {row}",
                "name": f"Matrix Test {row}",
                "parameters": params,
                "type": "rss_collector",
            }

            if OSINTSource.get(source_id):
                OSINTSource.delete(source_id)
            OSINTSource.add(source_data)

        try:
            response = client.get(f"{self.base_uri}/osint-sources/{source_id}", headers=api_header)
            assert response.status_code == 200, f"Worker GET failed for row {row}: {response}"
            payload = response.get_json()
            params = payload.get("parameters", {})

            effective_proxy = params.get("PROXY_SERVER", None)

            if expected == self.PER_SOURCE:
                assert effective_proxy == per_proxy, f"Row {row}: expected per-source proxy, got {effective_proxy!r}"
            elif expected == self.DEFAULT:
                assert effective_proxy == default_proxy, f"Row {row}: expected default proxy, got {effective_proxy!r}"
            else:
                assert not effective_proxy, f"Row {row}: expected no proxy, got {effective_proxy!r}"

        finally:
            with app.app_context():
                from core.model.osint_source import OSINTSource

                OSINTSource.delete(source_id)
