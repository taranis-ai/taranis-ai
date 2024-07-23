from tests.functional.helpers import BaseTest
import uuid


class TestAssessApi(BaseTest):
    base_uri = "/api/assess"

    def test_get_OSINTSourceGroupsAssess_auth(self, client, auth_header):
        """
        This test queries the OSINTSourceGroupsAssess authenticated.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "osint-source-group-list", auth_header)
        assert response.get_json()["items"][0]["id"] == "default"

    def test_get_OSINTSourcesList_auth(self, client, auth_header):
        """
        This test queries the OSINTSourcesList authenticated.
        It expects 1 OSINTSource ("manual") retured
        """
        response = self.assert_get_ok(client, "osint-sources-list", auth_header)
        items = response.get_json()["items"]
        assert len(items) >= 1
        item_ids = [item["id"] for item in items]
        assert "manual" in item_ids

    def test_post_AddNewsItem_auth(self, client, cleanup_news_item, auth_header):
        """
        This test queries the AddNewsItem authenticated.
        It expects a valid data and a valid status-code
        """

        response = client.post("/api/assess/news-items", json=cleanup_news_item, headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200
        assert uuid.UUID(response.get_json()["id"], version=4)

    def test_get_stories_auth(self, client, stories, auth_header):
        """
        This test queries the stories authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get("/api/assess/stories", headers=auth_header)
        assert response
        assert response.data
        assert response.get_json()["counts"]["total_count"] == 3
        assert response.content_type == "application/json"
        assert response.status_code == 200

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

    def test_get_NewsItem_auth(self, client, stories, auth_header):
        """
        This test queries the NewsItems Authenticated.
        It expects valid NewsItems
        """
        response = client.get("/api/assess/news-items", headers=auth_header)
        assert response.content_type == "application/json"
        assert response.status_code == 200
        assert len(response.get_json()["items"]) == 3

    def test_get_story_tags(self, client, stories, auth_header):
        """
        This test queries the tags Authentictaed.
        It expects a list of tags
        """
        from core.model.story import Story

        nia1 = Story.get(stories[0])
        nia2 = Story.get(stories[1])
        assert nia1
        assert nia2

        response = nia1.update_tags(nia1.id, ["foo", "bar", "baz"])
        assert response[1] == 200
        response = nia2.update_tags(nia2.id, {"foo": {"tag_type": "misc"}, "bar": {"tag_type": "misc"}})
        assert response[1] == 200

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
