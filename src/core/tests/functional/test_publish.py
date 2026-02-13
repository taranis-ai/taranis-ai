import base64
from datetime import datetime

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

    def test_rendered_product_download_returns_attachment(self, app, client, auth_header, pdf_product):
        file_bytes = b"This is a pdf"
        pdf_product.update_render(base64.b64encode(file_bytes).decode())
        expected_filename = f"Test Product_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.pdf"

        response = client.get(self.concat_url(f"products/{pdf_product.id}/render"), headers=auth_header)
        assert response.status_code == 200
        assert response.data == file_bytes
        assert response.mimetype == "application/pdf"
        assert response.headers.get("Content-Disposition") == f'attachment; filename="{expected_filename}"'
