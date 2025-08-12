import json
from tests.functional.helpers import BaseTest


class TestAdminApi(BaseTest):
    base_uri = "/api/admin"

    def test_delete_all_stories(self, client, stories, auth_header):
        response = self.assert_post_ok(client, "delete-stories", {}, auth_header)
        assert response.get_json()["message"] == "All Story deleted"
        response = client.get("/api/assess/stories", headers=auth_header)
        assert response.get_json()["counts"]["total_count"] == 0

    def test_settings_update(self, client, auth_header):
        """
        Test updating settings
        """
        test_settings = {
            "settings": {
                "default_collector_proxy": "http://test_server:1111",
                "default_collector_interval": "5 5 * * *",
                "default_tlp_level": "clear",
            }
        }

        response = self.assert_put_ok(client, "settings", test_settings, auth_header)
        response_settings = response.get_json()

        assert response_settings["message"] == "Successfully updated settings"
        assert response_settings["settings"] == test_settings["settings"]


def test_export_stories_and_metadata(client, full_story, api_header, auth_header):
    full_story[0]["attributes"] = [{"key": "status", "value": "updated"}]
    r = client.post("/api/worker/stories", json=full_story[0], headers=api_header)
    assert r.status_code == 200

    story_id = full_story[0]["id"]
    news_item_ids = {ni["id"] for ni in full_story[0].get("news_items", [])}

    # Export without metadata
    r = client.get("/api/admin/export-stories", headers=auth_header)
    assert r.status_code == 200
    assert r.mimetype.startswith("application/json")
    r.direct_passthrough = False  # send_file response
    data = json.loads(r.get_data(as_text=True))

    assert isinstance(data, list)
    assert isinstance(data[0], dict)
    assert "id" in data[0]
    assert "news_items" in data[0]
    assert data[0]["id"] == story_id
    assert data[0]["news_items"][0].get("author") is None

    exported_news_item_ids = {ni["id"] for ni in data[0].get("news_items", [])}
    assert len(exported_news_item_ids) == len(news_item_ids)
    assert news_item_ids.issubset(exported_news_item_ids)

    # Should not include metadata fields
    assert "attributes" not in data[0]
    assert "tags" not in data[0]
    assert "likes" not in data[0]
    assert "dislikes" not in data[0]
    assert "description" not in data[0]
    assert "read" not in data[0]
    assert "relevance" not in data[0]
    assert "comments" not in data[0]
    assert "summary" not in data[0]
    assert "created" not in data[0]
    assert "updated" not in data[0]

    # Export with metadata
    r = client.get("/api/admin/export-stories?metadata=true", headers=auth_header)
    assert r.status_code == 200
    assert r.mimetype.startswith("application/json")
    r.direct_passthrough = False
    data = json.loads(r.get_data(as_text=True))

    assert isinstance(data, list)
    assert isinstance(data[0], dict)
    assert "id" in data[0]
    assert data[0]["id"] == story_id
    assert data[0]["news_items"][0].get("author") == full_story[0]["news_items"][0].get("author")

    # Must include metadata fields now
    assert "title" in data[0]
    assert "tags" in data[0]
    # assert "attributes" in data[0]
    assert "news_items" in data[0]
    assert "likes" in data[0]
    assert "dislikes" in data[0]
    assert "description" in data[0]
    assert "read" in data[0]
    assert "relevance" in data[0]
    assert "comments" in data[0]
    assert "summary" in data[0]
    assert "created" in data[0]
    assert "updated" in data[0]

    exported_news_item_ids = {ni["id"] for ni in data[0].get("news_items", [])}
    assert len(exported_news_item_ids) == len(news_item_ids)
    assert news_item_ids.issubset(exported_news_item_ids)

    # Attribute we set should be present
    # attrs = {a.get("key"): a.get("value") for a in data[0].get("attributes", [])}
    # assert attrs.get("status") == "updated"
