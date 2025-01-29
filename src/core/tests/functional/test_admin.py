from tests.functional.helpers import BaseTest


class TestAdminApi(BaseTest):
    base_uri = "/api/admin"

    def test_delete_all_stories(self, client, stories, auth_header):
        response = self.assert_post_ok(client, "delete-stories", {}, auth_header)
        assert response.get_json()["message"] == "All Story deleted"
        response = client.get("/api/assess/stories", headers=auth_header)
        assert response.get_json()["counts"]["total_count"] == 0
