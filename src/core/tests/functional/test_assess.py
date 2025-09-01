from tests.functional.helpers import BaseTest
import uuid


class TestAssessApi(BaseTest):
    base_uri = "/api/assess"

    def test_get_OSINTSourceGroupsAssess(self, client, fake_source, auth_header):
        """
        This test queries the OSINTSourceGroupsAssess authenticated.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "osint-source-group-list", auth_header)
        assert response.get_json()["items"][0]["id"] == "default"

    def test_get_OSINTSourcesList(self, client, fake_source, auth_header):
        """
        This test queries the OSINTSourcesList authenticated.
        It expects 1 OSINTSource ("manual") returned
        """
        response = self.assert_get_ok(client, "osint-sources-list", auth_header)
        items = response.get_json()["items"]
        assert len(items) >= 1
        item_ids = [item["id"] for item in items]
        assert "manual" in item_ids

    def test_worker_story_creation_and_persistence(self, client, misp_story_from_news_items_id, auth_header):
        story_id, input_data = misp_story_from_news_items_id

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        assert response.status_code == 200
        story = response.get_json()

        expected_attributes = sorted(input_data["attributes"] + [{"key": "TLP", "value": "clear"}], key=lambda d: d["key"])
        actual_attributes = sorted(story["attributes"], key=lambda d: d["key"])

        assert story["title"] == input_data["title"]
        assert actual_attributes == expected_attributes
        assert len(story["news_items"]) == len(input_data["news_items"])


class TestAssessNewsItems(BaseTest):
    base_uri = "/api/assess"

    def test_post_AddNewsItem(self, client, cleanup_news_item, auth_header):
        response = self.assert_get_ok(client, "news-items", auth_header)
        assert len(response.get_json()["items"]) == 0, f"No news items should exist, found {response.get_json()['items']}"

        response = self.assert_post_ok(client, "news-items", cleanup_news_item, auth_header)
        assert uuid.UUID(response.get_json()["story_id"], version=4)

    def test_get_NewsItems(self, client, cleanup_news_item, auth_header):
        response = self.assert_get_ok(client, "news-items", auth_header)
        assert len(response.get_json()["items"]) == 1
        assert response.get_json()["items"][0]["id"] == cleanup_news_item["id"]

    def test_get_NewsItem(self, client, cleanup_news_item, auth_header):
        response = self.assert_get_ok(client, f"news-items/{cleanup_news_item['id']}", auth_header)
        assert response.get_json()["id"] == cleanup_news_item["id"]

    def test_delete_NewsItem(self, client, cleanup_news_item, auth_header):
        response = self.assert_delete_ok(client, f"news-items/{cleanup_news_item['id']}", auth_header)
        assert response.get_json()["id"] == cleanup_news_item["id"]
        assert response.get_json()["message"] == "News Item deleted"


class TestAssessStories(BaseTest):
    base_uri = "/api/assess"

    def test_story_creation(self, client, stories, auth_header):
        """
        This test queries the stories authenticated.
        It expects all the fields from the stories fixture to be mapped correctly
        """
        response = self.assert_get_ok(client, f"story/{stories[0]}", auth_header)
        first_story = response.get_json()
        assert first_story["id"] == stories[0]
        assert first_story["title"] == "Mobile World Congress 2023"
        assert first_story["attributes"] == [{"key": "TLP", "value": "clear"}]
        assert first_story["last_change"] == "external"

    def test_get_stories(self, client, stories, auth_header):
        """
        This test queries the stories authenticated.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "stories", auth_header)
        assert response.get_json()["counts"]["total_count"] == 3
        assert response.get_json()["items"][0]["id"] in stories

        response = client.get("/api/assess/stories?search=notexistent", headers=auth_header)
        assert response.status_code == 200
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/stories?notexistent=notexist", headers=auth_header)
        assert response.get_json()["counts"]["total_count"] > 0

        response = client.get("/api/assess/stories?read=true", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/stories?relevant=true", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/stories?in_report=true", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/stories?range=DAY", headers=auth_header)
        assert response.status_code == 200

        response = client.get("/api/assess/stories?sort=DATE_DESC", headers=auth_header)
        assert response.get_json()["counts"]["total_count"] > 0

        response = client.get("/api/assess/stories?offset=1", headers=auth_header)
        assert len(response.get_json()["items"]) == 2

        response = client.get("/api/assess/stories?limit=1", headers=auth_header)
        assert len(response.get_json()["items"]) == 1

    def test_get_story_tags(self, client, stories, auth_header):
        from core.model.story import Story

        nia1 = Story.get(stories[0])
        nia2 = Story.get(stories[1])
        assert nia1
        assert nia2

        response = nia1.set_tags(["foo", "bar", "baz"])
        assert response[1] == 200
        response = nia2.set_tags({"foo": {"tag_type": "misc"}, "bar": {"tag_type": "misc"}})
        assert response[1] == 200
        response = nia2.set_tags({"new": {"tag_type": "misc"}, "falling_back": ["this_is_malformed_format_and_should_be_rejected"]})
        assert response[1] == 500

        response = client.get("/api/assess/tags", headers=auth_header)
        assert len(response.get_json()) == 0
        assert response.content_type == "application/json"
        assert response.status_code == 200
        response = client.get("/api/assess/tags?min_size=1", headers=auth_header)
        assert len(response.get_json()) == 3
        response = client.get("/api/assess/tags?search=fo&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 1
        response = client.get("/api/assess/tags?limit=1&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 1
        response = client.get("/api/assess/tags?offset=1&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 2

    def test_delete_story(self, client, stories, auth_header):
        response = self.assert_delete_ok(client, f"story/{stories[0]}", auth_header)

        response = client.get("/api/assess/stories", headers=auth_header)
        total_count = response.get_json()["counts"]["total_count"]
        assert total_count == 2


class TestAssessStoriesGrouping(BaseTest):
    base_uri = "/api/assess"

    def test_group_stories(self, client, stories, auth_header):
        """
        This test groups the stories authenticated.
        """
        # Check initial state
        response = self.assert_get_ok(client, f"/story/{stories[0]}", auth_header)
        response_json = response.get_json()
        assert response_json["id"] == stories[0]
        assert response_json["last_change"] == "external"

        # Check main action
        response = self.assert_put_ok(client, "/stories/group", [stories[0], stories[1]], auth_header)
        assert response.get_json()["message"] == "Clustering Stories successful"
        assert response.get_json()["id"] == stories[0]

        # Check action result
        response = self.assert_get_ok(client, f"/story/{stories[0]}", auth_header)
        response_json = response.get_json()
        assert response_json["id"] == stories[0]
        assert len(response_json["news_items"]) == 2
        assert response_json["last_change"] == "internal"

        # Check the manual story that is supposed to stay unchanged
        response = self.assert_get_ok(client, f"/story/{stories[2]}", auth_header)
        response_json = response.get_json()
        assert response_json["news_items"][0]["id"] == "04129597-592d-45cb-9a80-3218108b29a1"
        assert response_json["news_items"][0]["osint_source_id"] == "manual"
        assert response_json["last_change"] == "internal"
        assert response_json["news_items"][0]["last_change"] == "internal", "manual news item's last_change should be internal"

        response = self.assert_get_ok(client, "stories", auth_header)
        assert response.get_json()["counts"]["total_count"] == 2

    def test_ungroup_stories(self, client, stories, auth_header):
        """
        This test ungroups the stories authenticated.
        """

        self.assert_put_ok(client, "/stories/ungroup", [stories[0]], auth_header)
        response = self.assert_get_ok(client, "stories", auth_header)
        assert response.get_json()["counts"]["total_count"] == 3

        assert response.get_json()["items"][0]["last_change"] == "internal"
        assert response.get_json()["items"][0]["news_items"][0]["last_change"] == "external"
        assert response.get_json()["items"][1]["last_change"] == "internal"
        assert response.get_json()["items"][1]["news_items"][0]["last_change"] == "external"

        # Check last_change for a manual news item
        assert response.get_json()["items"][2]["news_items"][0]["id"] == "04129597-592d-45cb-9a80-3218108b29a1"
        assert response.get_json()["items"][2]["news_items"][0]["osint_source_id"] == "manual"
        assert response.get_json()["items"][2]["last_change"] == "internal"
        assert response.get_json()["items"][2]["news_items"][0]["last_change"] == "internal", (
            "manual news item's last_change should be internal"
        )


class TestAssessUngroupNewsItem(BaseTest):
    base_uri = "/api/assess"

    def test_ungroup_single_news_item(self, client, stories, auth_header):
        """
        This test ungroups (removes) a single news item from a story with a only 1 item.
        The existing story ID should be removed and the news item should get a new story ID.
        """

        response = self.assert_put_ok(client, "/news-items/ungroup", ["0a129597-592d-45cb-9a80-3218108b29a0"], auth_header)
        assert response.get_json()["message"] == "success"
        assert response.get_json()["new_stories_ids"] not in stories

        response = client.get(f"/api/assess/story/{stories[1]}", headers=auth_header)
        assert response.status_code == 404


class TestAssessUngroupBigStory(BaseTest):
    base_uri = "/api/assess"

    def test_creation_of_full_story_with_multiple_items(self, client, full_story_with_multiple_items_id, auth_header):
        """
        This test creates a full story with multiple news items.
        It expects the story to be created with the correct ID and last_change set to internal.
        """
        full_story_id, _ = full_story_with_multiple_items_id

        response = self.assert_get_ok(client, f"/story/{full_story_id}", auth_header)
        assert response.get_json()["id"] == full_story_id
        assert len(response.get_json()["news_items"]) == 2
        assert response.get_json()["last_change"] == "external"
        assert response.get_json()["news_items"][0]["id"] == "90f0d9ec-70e7-45cf-8919-6ae2c02a4d88"
        assert response.get_json()["news_items"][0]["last_change"] == "external"
        assert response.get_json()["news_items"][1]["id"] == "c2a1c55c-6e7e-41de-8ad1-bda321f2f56b"
        assert response.get_json()["news_items"][1]["last_change"] == "external"
        assert len(response.get_json()["attributes"]) == 4
        assert len(response.get_json()["tags"]) == 3

    def test_ungroup_story_with_multiple_news_items(self, client, full_story_with_multiple_items_id, auth_header):
        from core.managers.db_manager import db

        """
        This test ungroups (removes) a single news item from a story with multiple items.
        The existing story ID should be kept with the first item and the other news item should get a new story ID.
        """
        full_story_id, _ = full_story_with_multiple_items_id

        response = self.assert_put_ok(client, "/news-items/ungroup", ["c2a1c55c-6e7e-41de-8ad1-bda321f2f56b"], auth_header)
        new_story_id = response.get_json()["new_stories_ids"][0]
        assert response.get_json()["message"] == "success"
        assert new_story_id != full_story_id

        # db.session.expunge_all() made visible a wrong db.session.commit() order - where the commit came too early - before all changes were made.
        # Without this, this problem was not visible and only occured in the real deployment.
        db.session.expunge_all()

        # Original story should still exist and change last_change property to internal
        response = self.assert_get_ok(client, f"/story/{full_story_id}", auth_header)
        assert response.get_json()["id"] == full_story_id
        assert response.get_json()["last_change"] == "internal", "after an item was removed, property should be internal"
        assert len(response.get_json()["news_items"]) == 1
        assert response.get_json()["news_items"][0]["id"] == "90f0d9ec-70e7-45cf-8919-6ae2c02a4d88"
        assert response.get_json()["news_items"][0]["last_change"] == "external"

        # New story should be created with the news item and have last_change set to internal
        response = self.assert_get_ok(client, f"/story/{new_story_id}", auth_header)
        assert response.get_json()["last_change"] == "internal"
        assert len(response.get_json()["news_items"]) == 1
        assert response.get_json()["news_items"][0]["id"] == "c2a1c55c-6e7e-41de-8ad1-bda321f2f56b"
        assert response.get_json()["news_items"][0]["last_change"] == "external"


class TestStoryNewsItemStatus(BaseTest):
    base_uri = "/api/assess"

    def test_story_news_item_status(self, client, stories, auth_header):
        response = self.assert_get_ok(client, "stories", auth_header)
        assert response.get_json()["counts"]["total_count"] == 3

        assert response.get_json()["items"][0]["last_change"] == "external"
        assert response.get_json()["items"][0]["news_items"][0]["last_change"] == "external"
        assert response.get_json()["items"][1]["last_change"] == "external"
        assert response.get_json()["items"][1]["news_items"][0]["last_change"] == "external"

        assert response.get_json()["items"][2]["last_change"] == "internal", "manual should be internal"
        assert response.get_json()["items"][2]["news_items"][0]["id"] == "04129597-592d-45cb-9a80-3218108b29a1"
        assert response.get_json()["items"][2]["news_items"][0]["osint_source_id"] == "manual"
        assert response.get_json()["items"][2]["news_items"][0]["last_change"] == "internal", (
            "manual news item's last_change should be internal"
        )
