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
    # Ingest one story via worker (API key auth)
    r = client.post("/api/worker/stories", json=full_story[0], headers=api_header)
    assert r.status_code == 200

    story_id = full_story[0]["id"]
    news_item_ids = {ni["id"] for ni in full_story[0].get("news_items", [])}

    # --- Export without metadata ---
    r = client.get("/api/admin/export-stories", headers=auth_header)
    assert r.status_code == 200
    assert r.mimetype.startswith("application/json")
    r.direct_passthrough = False  # send_file response
    data = json.loads(r.get_data(as_text=True))

    assert isinstance(data, list)
    assert all(isinstance(st, dict) for st in data)
    assert all("id" in st and "news_items" in st for st in data)

    # Story present
    by_id = {st["id"]: st for st in data}
    assert story_id in by_id, f"Story {story_id} missing in export without metadata"

    # News items present
    exported_news_ids = {ni["id"] for ni in by_id[story_id].get("news_items", [])}
    assert news_item_ids.issubset(exported_news_ids), f"Expected news items {news_item_ids}, got {exported_news_ids}"

    # --- Export with metadata ---
    r = client.get("/api/admin/export-stories?metadata=true", headers=auth_header)
    assert r.status_code == 200
    assert r.mimetype.startswith("application/json")
    r.direct_passthrough = False
    data = json.loads(r.get_data(as_text=True))

    assert isinstance(data, list)
    assert all(isinstance(st, dict) for st in data)

    st = next((s for s in data if s["id"] == story_id), None)
    assert st is not None, f"Story {story_id} missing in export with metadata"

    for key in ("id", "title", "tags", "attributes", "news_items"):
        assert key in st, f"Missing key {key} in story payload"

    exported_news_ids = {ni["id"] for ni in st.get("news_items", [])}
    assert news_item_ids.issubset(exported_news_ids), f"Expected news items {news_item_ids}, got {exported_news_ids}"
