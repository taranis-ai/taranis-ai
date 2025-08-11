import pytest


class TestWorkerApi:
    base_uri = "/api/worker"

    def test_worker_story_update(self, client, stories, cleanup_story_update_data, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """

        update_story_data = cleanup_story_update_data
        update_story_data["id"] = stories[0]

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_story_data,
            headers=api_header,
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Story updated successfully"
        assert result.get("id") == stories[0]

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": stories[0]})

        assert response.status_code == 200
        assert response.get_json()[0].get("title") == update_story_data["title"]
        assert response.get_json()[0].get("id") == stories[0]

    def test_worker_story_update_with_new_news_item(self, client, stories, cleanup_story_update_data, cleanup_news_item, api_header):
        """
        This test updates the same story as before (using the story_id from the previous test)
        by including new news items and adding an extra attribute.
        It verifies that the total number of news_items in the story increases as expected.
        """
        # Get the current state of the story to know the original number of news items.
        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": stories[0]},
        )
        assert response.status_code == 200
        original_story = response.get_json()[0]
        original_news_items = original_story.get("news_items", [])
        original_news_items_count = len(original_news_items)

        print(f"{original_news_items=}")
        print(f"{original_news_items_count=}")

        update_data = cleanup_story_update_data.copy()
        update_data["id"] = stories[0]  # reuse the story id from the previous test
        update_data["news_items"] = [original_story.get("news_items", [])[0], cleanup_news_item]
        update_data["attributes"].append({"key": "status", "value": "updated"})

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_data,
            headers=api_header,
        )
        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Story updated successfully"
        assert result.get("id") == stories[0]

        response = client.get(
            f"{self.base_uri}/stories",
            headers=api_header,
            query_string={"story_id": stories[0]},
        )
        assert response.status_code == 200
        updated_story = response.get_json()[0]
        print(f"{updated_story=}")
        assert updated_story.get("title") == update_data["title"]
        assert updated_story.get("id") == stories[0]

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

    def test_worker_create_full_story(self, client, full_story: list[dict], api_header):
        response = client.post(
            f"{self.base_uri}/stories",
            json=full_story[0],
            headers=api_header,
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Story added successfully"
        assert result.get("news_item_ids")[0] == full_story[0].get("news_items", [])[0].get("id", "<news_item_id>")
        assert result.get("story_id", "t<story_id>") == full_story[0].get("id")


class TestWorkerStoryApi:
    base_uri = "/api/worker"

    def test_news_items_to_story(self, client, news_items, api_header):
        story = {
            "title": "Test title",
            "attributes": [{"key": "hey", "value": "hou"}],
            "news_items": news_items,
        }

        response = client.post(f"{self.base_uri}/stories", json=story, headers=api_header)

        assert response.status_code == 200
        assert response.get_json().get("message") == "Story added successfully"


class TestOSINTSourceScheduling:
    base_uri = "/api/worker"

    @pytest.mark.parametrize(
        "row, per_source_proxy_set, default_proxy_set, use_global, expected",
        [
            # Row, per-source, default, use_global, expected result
            (1, False, False, False, "none"),
            (2, True, False, False, "per"),
            (3, False, True, False, "none"),
            (4, True, True, False, "per"),
            (5, False, False, True, "none"),
            (6, True, False, True, "none"),
            (7, False, True, True, "default"),
            (8, True, True, True, "default"),
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

            if expected == "per":
                assert effective_proxy == per_proxy, f"Row {row}: expected per-source proxy, got {effective_proxy!r}"
            elif expected == "default":
                assert effective_proxy == default_proxy, f"Row {row}: expected default proxy, got {effective_proxy!r}"
            else:
                assert not effective_proxy, f"Row {row}: expected no proxy, got {effective_proxy!r}"

        finally:
            with app.app_context():
                from core.model.osint_source import OSINTSource

                OSINTSource.delete(source_id)
