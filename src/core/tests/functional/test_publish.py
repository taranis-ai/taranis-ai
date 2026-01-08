import base64
import mimetypes
import uuid
from datetime import date

from core.model.product import Product
from core.model.product_type import ProductType
from models.types import PRESENTER_TYPES
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

    def test_rendered_product_download_returns_attachment(self, app, client, auth_header):
        product_id = str(uuid.uuid4())
        file_bytes = b"example product content"

        with app.app_context():
            presenter = ProductType.get_by_type(PRESENTER_TYPES.TEXT_PRESENTER)
            assert presenter, "Expected default text presenter to exist"

            product = Product.add(
                {
                    "id": product_id,
                    "title": "Download Product",
                    "description": "Functional download test",
                    "product_type_id": presenter.id,
                }
            )
            product.update_render(base64.b64encode(file_bytes).decode())
            expected_mime = presenter.get_mimetype()
            extension = mimetypes.guess_extension(expected_mime, strict=False) or ""
            expected_filename = f"Download_Product_{date.today().isoformat()}{extension}"

        try:
            response = client.get(self.concat_url(f"products/{product_id}/render"), headers=auth_header)
            assert response.status_code == 200
            assert response.data == file_bytes
            assert response.mimetype == expected_mime
            assert response.headers.get("Content-Disposition") == f'attachment; filename="{expected_filename}"'
        finally:
            with app.app_context():
                Product.delete(product_id)
