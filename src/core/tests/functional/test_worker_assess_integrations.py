class TestStoryAssessWorkerUpdates:
    base_uri_assess = "/api/assess"
    base_uri_worker = "/api/worker"

    def test_prevent_item_deletion_on_grouping(self, client, worker_story, full_story_with_multiple_items, api_header, auth_header):
        story_id, story_data = worker_story

        # 3. Ungroup the specified news item from the full story
        ungroup_item_id = "04129597-592d-45cb-9a80-3218108b29a1"
        ungroup_resp = client.put(f"{self.base_uri_assess}/news-items/ungroup", json=[ungroup_item_id], headers=auth_header)
        assert ungroup_resp.status_code == 200
        new_story_id = ungroup_resp.get_json().get("new_stories_ids")[0]
        assert new_story_id, "Ungrouping should create a new story"

        # 4. Now group the worker story with the full story
        group_payload = [story_id, full_story_with_multiple_items]
        group_resp = client.put("/api/assess/stories/group", json=group_payload, headers=auth_header)
        assert group_resp.status_code == 200
        clustered_id = group_resp.get_json()["id"]

        # 5. Fetch the grouped story and assert no added news items have been deleted
        grouped_resp = client.get(f"/api/assess/story/{clustered_id}", headers=auth_header)
        assert grouped_resp.status_code == 200
        items = grouped_resp.get_json()["news_items"]

        # Get the IDs of the news items you expect to exist after grouping
        expected_ids = set(
            [item["id"] for item in story_data["news_items"]]
            + [
                item["id"]
                for item in client.get(f"/api/assess/story/{full_story_with_multiple_items}", headers=auth_header).get_json()["news_items"]
            ]
        )

        result_ids = set(item["id"] for item in items)
        missing = expected_ids - result_ids

        assert not missing, f"Some news items got deleted in grouping: {missing}"
