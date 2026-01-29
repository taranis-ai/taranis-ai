import copy
from collections import defaultdict

from flask import json


class TestStoryAssessWorkerUpdates:
    base_uri_assess = "/api/assess"
    base_uri_worker = "/api/worker"
    base_uri_connectors = "/api/connectors"

    def test_prevent_item_deletion_on_grouping(
        self, client, misp_story_from_news_items_id, full_story_with_multiple_items_id, story_conflict_resolution_1, api_header, auth_header
    ):
        misp_story_id, _ = misp_story_from_news_items_id
        full_story_id, _ = full_story_with_multiple_items_id
        # assert worker story
        response = client.get(f"{self.base_uri_assess}/story/{misp_story_id}", headers=auth_header)
        assert response.status_code == 200, "Worker story should be fetched successfully"
        story_data = response.get_json()
        assert story_data.get("id") == misp_story_id, "The fetched worker story should match"
        assert len(story_data.get("news_items")) == 3, "Worker story should have 3 news items"
        news_items = story_data.get("news_items")
        news_item_story_ids = {item.get("story_id") for item in news_items}
        assert len(news_item_story_ids) == 1, "Worker story should have one story_id across all news items"

        response = client.get(f"{self.base_uri_assess}/story/{full_story_id}", headers=auth_header)
        assert response.status_code == 200
        full_story_news_items_ids = [item.get("id") for item in response.get_json().get("news_items")]

        # 3. Ungroup the specified news item from the full story
        ungroup_item_id = "04129597-592d-45cb-9a80-3218108b29a1"  # News item ID to ungroup
        ungroup_resp = client.put(f"{self.base_uri_assess}/news-items/ungroup", json=[ungroup_item_id], headers=auth_header)
        assert ungroup_resp.status_code == 200
        new_story_id = ungroup_resp.get_json().get("new_stories_ids")[0]
        assert new_story_id, "Ungrouping should create a new story"

        # 4. Now group the worker story with the full story
        group_payload = [misp_story_id, full_story_id]
        group_resp = client.put(f"{self.base_uri_assess}/stories/group", json=group_payload, headers=auth_header)
        assert group_resp.status_code == 200
        clustered_id = group_resp.get_json()["id"]
        assert clustered_id == misp_story_id, "The grouped story should have the same ID as the worker story"

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
        story_data["id"] = misp_story_id
        update_resp = client.post(f"{self.base_uri_worker}/stories/misp", json=[story_data], headers=api_header)
        assert update_resp.status_code == 409
        assert isinstance(update_resp.get_json().get("details"), dict)
        assert update_resp.get_json().get("details").get("errors")[0].get("conflict", {}).get("local", {}).get("id") == misp_story_id

        # Check if story stayed intact
        response = client.get(f"{self.base_uri_assess}/story/{misp_story_id}", headers=auth_header)
        assert response.status_code == 200
        assert response.get_json().get("id") == misp_story_id, "The worker story should remain unchanged after grouping"
        assert len(response.get_json().get("news_items")) == len(expected_ids), "The worker story should have the same number of news items"
        assert response.get_json().get("news_items")[0].get("story_id") == misp_story_id, "The worker story should have the correct story_id"
        assert response.get_json().get("news_items")[1].get("story_id") == misp_story_id, "The worker story should have the correct story_id"
        assert response.get_json().get("news_items")[2].get("story_id") == misp_story_id, "The worker story should have the correct story_id"
        assert response.get_json().get("news_items")[3].get("story_id") == misp_story_id, "The worker story should have the correct story_id"

        # Resolve the conflict successfully
        response = client.put(
            f"{self.base_uri_connectors}/conflicts/stories/{misp_story_id}", json=story_conflict_resolution_1, headers=auth_header
        )
        assert response.status_code == 200, "Conflict resolution should succeed"

        # Check if story is resolved correctly
        response = client.get(f"{self.base_uri_assess}/story/{misp_story_id}", headers=auth_header)
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data.get("id") == misp_story_id, "The worker story should remain unchanged after grouping"
        assert len(response_data.get("news_items")) == 3, "The worker story should have the same number of news items"
        assert response_data.get("title") == story_conflict_resolution_1.get("resolution").get("title"), (
            "The worker story title should be updated correctly"
        )
        assert response_data.get("description") == story_conflict_resolution_1.get("resolution").get("description"), (
            "The worker story description should be updated correctly"
        )
        assert response_data.get("comments") == story_conflict_resolution_1.get("resolution").get("comments"), (
            "The worker story comments should be updated correctly"
        )
        assert response_data.get("summary") == story_conflict_resolution_1.get("resolution").get("summary"), (
            "The worker story summary should be updated correctly"
        )
        assert len(response_data.get("attributes")) == len(story_conflict_resolution_1.get("resolution").get("attributes")) + 1, (
            "The worker story attributes should be updated correctly + TLP attribute"
        )
        assert response_data.get("news_items")[0].get("content") in ["TEST CONTENT ZZZZ", "TEST CONTENT YYYY", "CVE-2020-1234 - Test Story 1"]
        assert response_data.get("news_items")[1].get("content") in ["TEST CONTENT ZZZZ", "TEST CONTENT YYYY", "CVE-2020-1234 - Test Story 1"]
        assert response_data.get("news_items")[2].get("content") in ["TEST CONTENT ZZZZ", "TEST CONTENT YYYY", "CVE-2020-1234 - Test Story 1"]


class TestStoryConflictStoreUpdates:
    base_uri_assess = "/api/assess"
    base_uri_worker = "/api/worker"
    base_uri_connectors = "/api/connectors"

    def test_story_conflict_store_update(
        self, client, misp_story_from_news_items_id, full_story_with_multiple_items_id, story_conflict_resolution_1, api_header, auth_header
    ):
        misp_story_id, misp_story_data = misp_story_from_news_items_id
        full_story_id, full_story_data = full_story_with_multiple_items_id
        # Make an internal change to the misp story (simulate pressing submit with the same data)
        response = client.put(
            f"{self.base_uri_assess}/story/{misp_story_id}",
            json=misp_story_data,
            headers=auth_header,
        )
        assert response.status_code == 200, "MISP story should be updated successfully"
        # make internal change to story with multiple items (simulate pressing submit with the same data)
        response = client.put(
            f"{self.base_uri_assess}/story/{full_story_id}",
            json=full_story_data,
            headers=auth_header,
        )

        assert response.status_code == 200, "Full story should be updated successfully"
        # try to update stories -> create conflicts for story conflict data class
        misp_story_data["title"] = "Updated MISP Story Title"
        full_story_data["title"] = "Updated Full Story Title"
        response = client.post(
            f"{self.base_uri_worker}/stories/misp",
            json=[misp_story_data, full_story_data],
            headers=api_header,
        )

        assert response.status_code == 409, "Conflict should be created when trying to update stories"
        response = client.get(f"{self.base_uri_connectors}/conflicts/stories", headers=auth_header)
        assert response.status_code == 200
        assert len(response.get_json().get("conflicts")) == 2, "There should be 2 conflicts in the store"
        assert response.get_json().get("conflicts")[0].get("storyId") == misp_story_id
        assert response.get_json().get("conflicts")[1].get("storyId") == full_story_id
        misp_story_1_original_data = json.loads(response.get_json().get("conflicts")[0].get("original"))
        misp_story_1_updated_data = json.loads(response.get_json().get("conflicts")[0].get("updated"))
        full_story_2_original_data = json.loads(response.get_json().get("conflicts")[1].get("original"))
        full_story_2_updated_data = json.loads(response.get_json().get("conflicts")[1].get("updated"))

        assert misp_story_1_original_data.get("title") == "Test title"
        assert misp_story_1_updated_data.get("title") == "Updated MISP Story Title"
        assert full_story_2_original_data.get("title") == "Test Story: Two News Items"
        assert full_story_2_updated_data.get("title") == "Updated Full Story Title"

        # Simulate worker sending updates to the two stories
        # Story conflict data class should update the conflict store
        misp_story_data["title"] = "Second update to MISP Story Title"
        full_story_data["title"] = "Second update to Full Story Title"
        response = client.post(
            f"{self.base_uri_worker}/stories/misp",
            json=[misp_story_data, full_story_data],
            headers=api_header,
        )
        assert response.status_code == 409, "Conflict should be created when trying to update stories again"
        response = client.get(f"{self.base_uri_connectors}/conflicts/stories", headers=auth_header)
        assert response.status_code == 200
        assert len(response.get_json().get("conflicts")) == 2, "There should be 2 conflicts in the store"
        assert response.get_json().get("conflicts")[0].get("storyId") == misp_story_id
        assert response.get_json().get("conflicts")[1].get("storyId") == full_story_id
        misp_story_1_original_data = json.loads(response.get_json().get("conflicts")[0].get("original"))
        misp_story_1_updated_data = json.loads(response.get_json().get("conflicts")[0].get("updated"))
        full_story_2_original_data = json.loads(response.get_json().get("conflicts")[1].get("original"))
        full_story_2_updated_data = json.loads(response.get_json().get("conflicts")[1].get("updated"))

        assert misp_story_1_original_data.get("title") == "Test title"
        assert misp_story_1_updated_data.get("title") == "Second update to MISP Story Title"
        assert full_story_2_original_data.get("title") == "Test Story: Two News Items"
        assert full_story_2_updated_data.get("title") == "Second update to Full Story Title"


class TestNewsItemConflictStoreUpdates:
    base_uri_assess = "/api/assess"
    base_uri_worker = "/api/worker"
    base_uri_connectors = "/api/connectors"

    def test_news_item_conflict_store_update(
        self,
        client,
        misp_story_from_news_items_id,
        full_story_with_multiple_items_id,
        story_conflict_resolution_1,
        api_header,
        auth_header,
    ):
        self._flush_conflict_stores()

        misp_story_id, misp_story_data_original = misp_story_from_news_items_id
        full_story_id, full_story_data_original = full_story_with_multiple_items_id

        context = {
            "misp_story_id": misp_story_id,
            "full_story_id": full_story_id,
            "misp_story_data": copy.deepcopy(misp_story_data_original),
            "full_story_data": copy.deepcopy(full_story_data_original),
            "misp_conflict_ids": set(),
            "full_conflict_ids": set(),
            "pairs_first": set(),
            "pairs_second": set(),
            "removed_news_item_id": None,
        }

        self._step_01_ungroup_and_assert_five_items(client, auth_header, context)
        self._step_02_first_update_creates_conflicts(client, api_header, auth_header, context)
        self._step_03_second_update_refreshes_snapshots_without_new_pairs(client, api_header, auth_header, context)
        self._step_04_remove_one_conflicting_item_and_verify_counts(client, api_header, auth_header, context)

    # ---------- helpers (no test_ prefix) ----------

    def _flush_conflict_stores(self) -> None:
        from core.model.news_item_conflict import NewsItemConflict
        from core.model.story_conflict import StoryConflict

        NewsItemConflict.flush_store()
        StoryConflict.flush_store()

    def _step_01_ungroup_and_assert_five_items(self, client, auth_header, context: dict) -> None:
        misp_story_id = context["misp_story_id"]
        full_story_id = context["full_story_id"]

        response = client.put(
            f"{self.base_uri_assess}/stories/ungroup",
            json=[misp_story_id, full_story_id],
            headers=auth_header,
        )
        assert response.status_code == 200, "Ungrouping stories should succeed"

        response = client.get(f"{self.base_uri_assess}/stories", headers=auth_header)
        assert response.status_code == 200
        payload = response.get_json()
        assert payload.get("counts", {}).get("total_count") == 5
        assert len(payload.get("items", [])) == 5

    def _step_02_first_update_creates_conflicts(self, client, api_header, auth_header, context: dict) -> None:
        context["misp_story_data"]["title"] = "Second update to MISP Story Title"
        context["full_story_data"]["title"] = "Second update to Full Story Title"

        response = client.post(
            f"{self.base_uri_worker}/stories/misp",
            json=[context["misp_story_data"], context["full_story_data"]],
            headers=api_header,
        )
        assert response.status_code == 409, "Posting updates should create conflicts"

        conflicts = self._fetch_news_item_conflicts(client, auth_header)
        assert isinstance(conflicts, list)
        assert len(conflicts) == 5

        conflicts_by_story = self._group_conflicts_by_story(conflicts)
        assert set(conflicts_by_story.keys()) == {context["misp_story_id"], context["full_story_id"]}

        misp_count = len(conflicts_by_story[context["misp_story_id"]])
        full_count = len(conflicts_by_story[context["full_story_id"]])
        assert misp_count >= 1 and full_count >= 1 and misp_count + full_count == 5

        assert conflicts_by_story[context["misp_story_id"]][0]["incoming_story"]["title"] == "Second update to MISP Story Title"
        assert conflicts_by_story[context["full_story_id"]][0]["incoming_story"]["title"] == "Second update to Full Story Title"

        context["pairs_first"] = {(conflict["incoming_story_id"], conflict["news_item_id"]) for conflict in conflicts}

    def _step_03_second_update_refreshes_snapshots_without_new_pairs(self, client, api_header, auth_header, context: dict) -> None:
        context["misp_story_data"]["title"] = "Third update to MISP Story Title"
        context["full_story_data"]["title"] = "Third update to Full Story Title"

        response = client.post(
            f"{self.base_uri_worker}/stories/misp",
            json=[context["misp_story_data"], context["full_story_data"]],
            headers=api_header,
        )
        assert response.status_code == 409

        conflicts_second = self._fetch_news_item_conflicts(client, auth_header)
        assert len(conflicts_second) == 5

        context["pairs_second"] = {(conflict["incoming_story_id"], conflict["news_item_id"]) for conflict in conflicts_second}
        assert context["pairs_second"] == context["pairs_first"], "Second update must not add new conflict pairs"

        conflicts_by_story = self._group_conflicts_by_story(conflicts_second)
        assert conflicts_by_story[context["misp_story_id"]][0]["incoming_story"]["title"] == "Third update to MISP Story Title"
        assert conflicts_by_story[context["full_story_id"]][0]["incoming_story"]["title"] == "Third update to Full Story Title"

        context["misp_conflict_ids"] = {conflict["news_item_id"] for conflict in conflicts_by_story[context["misp_story_id"]]}
        context["full_conflict_ids"] = {conflict["news_item_id"] for conflict in conflicts_by_story[context["full_story_id"]]}

    def _step_04_remove_one_conflicting_item_and_verify_counts(self, client, api_header, auth_header, context: dict) -> None:
        # choose one conflicting item from MISP story and remove it from payload
        news_item_id_to_remove = next(iter(context["misp_conflict_ids"]))
        context["removed_news_item_id"] = news_item_id_to_remove

        original_length = len(context["misp_story_data"]["news_items"])
        context["misp_story_data"]["news_items"] = [
            item for item in context["misp_story_data"]["news_items"] if item.get("id") != news_item_id_to_remove
        ]
        assert len(context["misp_story_data"]["news_items"]) == original_length - 1, "Specific item should be removed"

        # bump title again and post
        context["misp_story_data"]["title"] = "Fourth update to MISP Story Title"
        response = client.post(
            f"{self.base_uri_worker}/stories/misp",
            json=[context["misp_story_data"], context["full_story_data"]],
            headers=api_header,
        )
        assert response.status_code in (200, 409)

        conflicts_after = self._fetch_news_item_conflicts(client, auth_header)
        conflict_pairs_after = {(conflict["incoming_story_id"], conflict["news_item_id"]) for conflict in conflicts_after}
        assert (context["misp_story_id"], news_item_id_to_remove) not in conflict_pairs_after
        assert len(conflict_pairs_after) == len(context["pairs_second"]) - 1

        conflicts_by_story_after = self._group_conflicts_by_story(conflicts_after)
        assert {c["news_item_id"] for c in conflicts_by_story_after.get(context["full_story_id"], [])} == context["full_conflict_ids"]

        if conflicts_by_story_after.get(context["misp_story_id"]):
            assert conflicts_by_story_after[context["misp_story_id"]][0]["incoming_story"]["title"] == "Fourth update to MISP Story Title"
        if conflicts_by_story_after.get(context["full_story_id"]):
            assert conflicts_by_story_after[context["full_story_id"]][0]["incoming_story"]["title"] == "Third update to Full Story Title"

    # ---------- tiny utilities ----------

    def _fetch_news_item_conflicts(self, client, auth_header) -> list[dict]:
        response = client.get(f"{self.base_uri_connectors}/conflicts/news-items", headers=auth_header)
        assert response.status_code == 200
        return response.get_json().get("conflicts", [])

    def _group_conflicts_by_story(self, conflicts: list[dict]) -> dict[str, list[dict]]:
        conflicts_by_story = defaultdict(list)
        for conflict in conflicts:
            conflicts_by_story[conflict["incoming_story_id"]].append(conflict)
        return conflicts_by_story
