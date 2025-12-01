from tests.functional.helpers import BaseTest


class TestPublishApi(BaseTest):
    base_uri = "/api/publish"

    def test_post_Product(self, client, auth_header, cleanup_product):
        """
        This test queries the /api/publish/products endpoint with a POST request.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "products", auth_header=auth_header, json_data=cleanup_product)
        assert response.get_json()["id"] == cleanup_product["id"]

    def test_get_Products(self, client, auth_header, cleanup_product):
        """
        This test queries the /api/publish/products endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "products", auth_header)
        assert response.get_json()["total_count"] == 1
        assert response.get_json()["items"][0]["title"] == cleanup_product["title"]
