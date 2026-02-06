import importlib.util
import os
import sys

import pytest


class TestWorkerApi:
    base_uri = "/api/worker"

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
        update_data["news_items"] = [cleanup_news_item]
        update_data["attributes"].append({"key": "status", "value": "updated"})
        update_data["tags"] = ["tag1", "tag2"]

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
        assert len(updated_story.get("tags")) == 2

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
        original_news_items.append(cleanup_news_item_2)

        update_data = cleanup_story_update_data.copy()
        update_data["id"] = story_1_id
        update_data["news_items"] = original_news_items

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
        assert len(response.get_json()[0].get("news_items", [])) == len(original_news_items)
        assert len(response.get_json()[0].get("tags")) == 2

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
        assert len(story.get("tags", [])) == len(full_story[0].get("tags", []))
        assert len(story.get("attributes", {})) == len(full_story[0].get("attributes", [])) + 1  # TLP is automatically added

    def test_worker_post_to_misp_endpoint(self, client, full_story: list[dict], api_header):
        """Test if MISP endpoint handles updates without conflicts correctly"""
        story_id = full_story[0].get("id")

        response = client.post(
            f"{self.base_uri}/stories/misp",
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
        assert len(story.get("tags", [])) == len(full_story[0].get("tags", []))
        assert len(story.get("attributes", {})) == len(full_story[0].get("attributes", [])) + 1

    def test_worker_put_tags(self, client, stories, api_header):
        story_1_id = stories[0]
        tags = ["tag3", "tag4"]

        response = client.put(f"{self.base_uri}/tags", json={story_1_id: tags}, headers=api_header)

        assert response.status_code == 200
        assert response.get_json().get("message") == "Tags updated"

    def test_worker_put_tags_invalid_cases(self, client, stories, api_header):
        story_1_id = stories[0]

        # Empty list
        response = client.put(f"{self.base_uri}/tags", json={story_1_id: []}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # Tags not a list
        response = client.put(f"{self.base_uri}/tags", json={story_1_id: "notalist"}, headers=api_header)
        assert response.status_code == 207
        assert "message" in response.get_json()

        # Missing story id
        response = client.put(f"{self.base_uri}/tags", json={"not_a_story_id": ["tag1"]}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # Tags list contains non-string elements
        response = client.put(f"{self.base_uri}/tags", json={story_1_id: [123, None]}, headers=api_header)
        assert response.status_code == 207
        assert "errors" in response.get_json()

        # Story ID is not a string
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

    def test_worker_get_tags(self, client, api_header):
        response = client.get(f"{self.base_uri}/tags", headers=api_header)

        assert response.status_code == 200
        assert isinstance(response.get_json(), dict)
        assert len(response.get_json()) == 5


class TestConnector:
    base_uri = "/api/worker"

    def test_connector(self, client, stories, api_header):
        from unittest.mock import MagicMock

        sys.modules["pymisp"] = MagicMock()
        sys.modules["worker"] = MagicMock()
        sys.modules["worker.log"] = MagicMock()
        sys.modules["worker.core_api"] = MagicMock()
        sys.modules["worker.connectors"] = MagicMock()
        sys.modules["worker.connectors.definitions"] = MagicMock()
        sys.modules["worker.connectors.base_misp_builder"] = MagicMock()
        sys.modules["worker.connectors.definitions.misp_objects"] = MagicMock()

        file_path = os.path.abspath(os.path.join(__file__, "../../../../worker/worker/connectors/base_misp_builder.py"))

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
        story["tags"] = {"test_tag": {"name": "test_tag", "tag_type": "misc"}}

        client.post(f"{self.base_uri}/stories", json=story, headers=api_header)

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

        response = client.put("/api/admin/settings", json=settings_payload, headers=auth_header)
        assert response.status_code == 200, f"Failed to set settings for row {row}: {response}"

        source_id = "test_id"
        with app.app_context():
            from core.model.osint_source import OSINTSource

            params = [
                {"FEED_URL": "https://example.org/feed.xml"},
                {"USE_GLOBAL_PROXY": "true" if use_global else "false"},
            ]
            if per_source_proxy_set:
                params.append({"PROXY_SERVER": per_proxy})

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
