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
