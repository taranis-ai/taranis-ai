import json
import uuid
from datetime import datetime, timedelta, timezone

from tests.application.support.api_test_base import BaseTest


class TestAdminApi(BaseTest):
    base_uri = "/api/settings"

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
                "default_story_conflict_retention": "150",
                "default_news_item_conflict_retention": "150",
                "default_timezone": "Europe/Vienna",
            }
        }

        response = self.assert_put_ok(client, "settings", test_settings, auth_header)
        response_settings = response.get_json()

        assert response_settings["message"] == "Successfully updated settings"
        for key, value in test_settings["settings"].items():
            assert response_settings["settings"][key] == value

    def test_settings_patch_updates_single_field(self, client, auth_header):
        initial_settings = {
            "settings": {
                "default_collector_proxy": "http://initial-proxy.test:1111",
                "default_collector_interval": "5 5 * * *",
                "default_tlp_level": "clear",
                "default_story_conflict_retention": "150",
                "default_news_item_conflict_retention": "150",
            }
        }
        self.assert_put_ok(client, "settings", initial_settings, auth_header)

        response = self.assert_patch_ok(
            client,
            "settings",
            {"settings": {"default_collector_proxy": "http://patched-proxy.test:2222"}},
            auth_header,
        )

        response_settings = response.get_json()["settings"]
        assert response_settings["default_collector_proxy"] == "http://patched-proxy.test:2222"
        assert response_settings["default_collector_interval"] == initial_settings["settings"]["default_collector_interval"]

    def test_settings_rejects_invalid_default_timezone(self, client, auth_header):
        response = client.put(
            self.concat_url("settings"),
            json={"settings": {"default_timezone": "Not/A_Timezone"}},
            headers=auth_header,
        )

        assert response.status_code == 400
        assert "Invalid timezone" in response.get_json()["error"]

    def test_settings_rejects_non_string_default_timezone(self, client, auth_header):
        response = client.put(
            self.concat_url("settings"),
            json={"settings": {"default_timezone": 123}},
            headers=auth_header,
        )

        assert response.status_code == 400
        assert "Invalid timezone" in response.get_json()["error"]

    def test_settings_clears_default_timezone(self, client, auth_header):
        response = self.assert_put_ok(
            client,
            "settings",
            {"settings": {"default_timezone": ""}},
            auth_header,
        )

        assert response.get_json()["settings"]["default_timezone"] is None


def test_export_stories_and_metadata(client, full_story, api_header, auth_header):
    full_story[0]["attributes"] = [{"key": "status", "value": "updated"}]
    r = client.post("/api/worker/stories", json=full_story[0], headers=api_header)
    assert r.status_code == 200

    story_id = full_story[0]["id"]
    news_item_ids = {ni["id"] for ni in full_story[0].get("news_items", [])}

    # Export without metadata
    r = client.get("/api/settings/export-stories", headers=auth_header)
    assert r.status_code == 200
    assert r.mimetype.startswith("application/json")
    r.direct_passthrough = False  # send_file response
    data = json.loads(r.get_data(as_text=True))

    assert isinstance(data, list)
    assert isinstance(data[0], dict)
    assert "id" in data[0]
    assert "created" in data[0]
    assert "news_items" in data[0]
    assert data[0]["id"] == story_id
    assert data[0]["news_items"][0].get("author") is None

    expected_created = datetime.fromisoformat(full_story[0]["created"]).isoformat()
    assert data[0]["created"] == expected_created

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
    assert "updated" not in data[0]

    # Export with metadata
    r = client.get("/api/settings/export-stories?metadata=true", headers=auth_header)
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


def test_import_stories_ignores_export_only_fields(client, auth_header):
    story_id = str(uuid.uuid4())
    news_item_id = str(uuid.uuid4())
    payload = [
        {
            "id": story_id,
            "title": "Imported Story",
            "relevance_override": 7,
            "links": ["https://example.com/story/export-only"],
            "news_items": [
                {
                    "id": news_item_id,
                    "title": "Imported Story News 1",
                    "content": "content",
                    "source": "https://example.com/source",
                    "link": "https://example.com/news",
                    "osint_source_id": "manual",
                    "links": ["https://example.com/news/export-only"],
                }
            ],
        }
    ]

    response = client.post("/api/assess/import", json=payload, headers=auth_header)

    assert response.status_code == 200
    imported_story = response.get_json()["imported_stories"][0]
    assert imported_story["id"] == story_id
    assert imported_story["relevance_override"] == 7
    assert imported_story["links"] == ["https://example.com/news"]
    assert imported_story["news_items"][0]["id"] == news_item_id
    assert imported_story["news_items"][0]["link"] == "https://example.com/news"


def test_export_stories_rejects_invalid_datetime_filters(client, auth_header):
    r = client.get("/api/settings/export-stories?timefrom=invalid", headers=auth_header)

    assert r.status_code == 400
    assert r.get_json()["error"][0]["loc"] == ["timefrom"]


def test_export_stories_rejects_future_datetime_filters(client, auth_header):
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    r = client.get(f"/api/settings/export-stories?timeto={future_time}", headers=auth_header)

    assert r.status_code == 400
    assert r.get_json()["error"][0]["loc"] == ["timeto"]


def test_export_stories_allows_empty_datetime_filters(client, auth_header):
    r = client.get("/api/settings/export-stories?timefrom=&timeto=", headers=auth_header)

    assert r.status_code == 200


def test_cache_invalidate_all_endpoint(client, auth_header, monkeypatch):
    from core.service import cache_invalidation as cache_invalidation_module

    monkeypatch.setattr(cache_invalidation_module.cache_invalidation_service, "invalidate_all", lambda: 5)

    response = client.post("/api/admin/cache/invalidate", json={"mode": "all"}, headers=auth_header)

    assert response.status_code == 200
    assert response.get_json() == {"message": "Frontend cache invalidated", "deleted": 5, "mode": "all"}


def test_cache_invalidate_model_endpoint_requires_model(client, auth_header):
    response = client.post("/api/admin/cache/invalidate", json={"mode": "model"}, headers=auth_header)

    assert response.status_code == 400
    assert response.get_json()["error"] == "model is required for mode=model"


def test_cache_invalidate_scope_endpoint_rejects_unknown_scope(client, auth_header):
    response = client.post("/api/admin/cache/invalidate", json={"mode": "scope", "scope": "unknown"}, headers=auth_header)

    assert response.status_code == 400
    assert response.get_json()["error"] == "Unknown scope"
