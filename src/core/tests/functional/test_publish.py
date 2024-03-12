from tests.functional.helpers import BaseTest


class TestPublishApi(BaseTest):
    base_uri = "/api/publish"

    def test_get_Products(self, client, auth_header):
        """
        This test queries the /api/publish/products endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "products", auth_header)
        assert response.get_json()["total_count"] == 0
        assert response.get_json()["items"] == []
