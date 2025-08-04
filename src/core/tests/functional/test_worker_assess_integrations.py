class TestStoryAssessWorkerUpdates:
    base_uri_assess = "/api/assess"
    base_uri_worker = "/api/worker"
    base_uri_connectors = "/api/connectors"

    def test_prevent_item_deletion_on_grouping(
        self, client, worker_story, full_story_with_multiple_items_id, worker_story_update_payload_1, api_header, auth_header
    ):
        story_id = worker_story
        # assert worker story
        response = client.get(f"{self.base_uri_assess}/story/{story_id}", headers=auth_header)
        assert response.status_code == 200, "Worker story should be fetched successfully"
        story_data = response.get_json()
        assert story_data.get("id") == story_id, "The fetched worker story should match"
        assert len(story_data.get("news_items")) == 3, "Worker story should have 3 news items"
        news_items = story_data.get("news_items")
        news_item_story_ids = {item.get("story_id") for item in news_items}
        assert len(news_item_story_ids) == 1, "Worker story should have one story_id across all news items"

        response = client.get(f"{self.base_uri_assess}/story/{full_story_with_multiple_items_id}", headers=auth_header)
        assert response.status_code == 200
        full_story_news_items_ids = [item.get("id") for item in response.get_json().get("news_items")]

        # 3. Ungroup the specified news item from the full story
        ungroup_item_id = "04129597-592d-45cb-9a80-3218108b29a1"  # News item ID to ungroup
        ungroup_resp = client.put(f"{self.base_uri_assess}/news-items/ungroup", json=[ungroup_item_id], headers=auth_header)
        assert ungroup_resp.status_code == 200
        new_story_id = ungroup_resp.get_json().get("new_stories_ids")[0]
        assert new_story_id, "Ungrouping should create a new story"

        # 4. Now group the worker story with the full story
        group_payload = [story_id, full_story_with_multiple_items_id]
        group_resp = client.put(f"{self.base_uri_assess}/stories/group", json=group_payload, headers=auth_header)
        assert group_resp.status_code == 200
        clustered_id = group_resp.get_json()["id"]
        assert clustered_id == story_id, "The grouped story should have the same ID as the worker story"

        # 5. Fetch the grouped story
        grouped_resp = client.get(f"{self.base_uri_assess}/story/{clustered_id}", headers=auth_header)
        assert grouped_resp.status_code == 200
        items = grouped_resp.get_json()["news_items"]
        expected_ids = list(
            set([news_item.get("id") for news_item in story_data["news_items"]] + full_story_news_items_ids) - {ungroup_item_id}
        )
        actual_ids = [news_item.get("id") for news_item in items]

        assert len(actual_ids) == 4
        assert sorted(expected_ids) == sorted(actual_ids), "Grouped story should contain all news items except the ungrouped one"

        # Update worker_story with the original worker story_data
        story_data["id"] = story_id
        update_resp = client.post(f"{self.base_uri_worker}/stories/misp", json=[story_data], headers=api_header)
        assert update_resp.status_code == 409
        assert isinstance(update_resp.get_json().get("details"), list)
        assert update_resp.get_json().get("details")[0].get("conflict", {}).get("local", {}).get("id") == story_id

        # Check if story stayed intact
        response = client.get(f"{self.base_uri_assess}/story/{story_id}", headers=auth_header)
        assert response.status_code == 200
        assert response.get_json().get("id") == story_id, "The worker story should remain unchanged after grouping"
        assert len(response.get_json().get("news_items")) == len(expected_ids), "The worker story should have the same number of news items"
        assert response.get_json().get("news_items")[0].get("story_id") == story_id, "The worker story should have the correct story_id"
        assert response.get_json().get("news_items")[1].get("story_id") == story_id, "The worker story should have the correct story_id"
        assert response.get_json().get("news_items")[2].get("story_id") == story_id, "The worker story should have the correct story_id"
        assert response.get_json().get("news_items")[3].get("story_id") == story_id, "The worker story should have the correct story_id"

        # Resolve the conflict successfully
        response = client.put(
            f"{self.base_uri_connectors}/conflicts/stories/{story_id}", json=worker_story_update_payload_1, headers=auth_header
        )
        assert response.status_code == 200, "Conflict resolution should succeed"

        # Check if story is resolved correctly
        response = client.get(f"{self.base_uri_assess}/story/{story_id}", headers=auth_header)
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data.get("id") == story_id, "The worker story should remain unchanged after grouping"
        assert len(response_data.get("news_items")) == 3, "The worker story should have the same number of news items"
        assert response_data.get("title") == worker_story_update_payload_1.get("resolution").get("title"), (
            "The worker story title should be updated correctly"
        )
        assert response_data.get("description") == worker_story_update_payload_1.get("resolution").get("description"), (
            "The worker story description should be updated correctly"
        )
        assert response_data.get("comments") == worker_story_update_payload_1.get("resolution").get("comments"), (
            "The worker story comments should be updated correctly"
        )
        assert response_data.get("summary") == worker_story_update_payload_1.get("resolution").get("summary"), (
            "The worker story summary should be updated correctly"
        )
        assert len(response_data.get("attributes")) == len(worker_story_update_payload_1.get("resolution").get("attributes")) + 1, (
            "The worker story attributes should be updated correctly + TLP attribute"
        )
        assert response_data.get("links") == worker_story_update_payload_1.get("resolution").get("links"), (
            "The worker story links should be updated correctly"
        )
        assert response_data.get("news_items")[0].get("content") in ["TEST CONTENT ZZZZ", "TEST CONTENT YYYY", "CVE-2020-1234 - Test Story 1"]
        assert response_data.get("news_items")[1].get("content") in ["TEST CONTENT ZZZZ", "TEST CONTENT YYYY", "CVE-2020-1234 - Test Story 1"]
        assert response_data.get("news_items")[2].get("content") in ["TEST CONTENT ZZZZ", "TEST CONTENT YYYY", "CVE-2020-1234 - Test Story 1"]
