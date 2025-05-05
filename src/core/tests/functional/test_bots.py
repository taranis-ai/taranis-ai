from tests.functional.helpers import BaseTest


class TestBotsApi(BaseTest):
    base_uri = "/api/bots"

    def test_story_update(self, client, stories, cleanup_story_update_data, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.put(f"{self.base_uri}/story/{stories[0]}", json=cleanup_story_update_data, headers=api_header)
        story_id = response.get_json().get("id")

        assert response.status_code == 200
        assert story_id == stories[0], "Response ID should match request ID"

    def test_attribute_update(self, client, stories, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.patch(
            f"{self.base_uri}/story/{stories[0]}/attributes", json=[{"key": "tech", "value": "in_progress"}], headers=api_header
        )
        assert response.status_code == 200

    def test_check_updated_story(self, client, stories, cleanup_story_update_data, auth_header):
        """Check if the update was successful"""
        response = client.get(f"api/assess/story/{stories[0]}", headers=auth_header)

        assert response.status_code == 200
        assert response.get_json().get("important") == cleanup_story_update_data["important"]
        assert response.get_json().get("read") == cleanup_story_update_data["read"]
        assert response.get_json().get("title") == cleanup_story_update_data["title"]
        assert response.get_json().get("description") == cleanup_story_update_data["description"]
        assert response.get_json().get("comments") == cleanup_story_update_data["comments"]
        assert response.get_json().get("summary") == cleanup_story_update_data["summary"]

        assert len(response.get_json().get("links")) == len(cleanup_story_update_data["links"])
        assert all(link in cleanup_story_update_data["links"] for link in response.get_json().get("links"))

        attributes = sorted(response.get_json()["attributes"], key=lambda d: d["key"])
        expected_attributes = sorted(
            cleanup_story_update_data["attributes"] + [{"key": "tech", "value": "in_progress"}], key=lambda d: d["key"]
        )

        assert attributes == expected_attributes
